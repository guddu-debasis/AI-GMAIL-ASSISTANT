from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.reply_draft import ReplyDraft
from app.models.email import Email
from app.schemas.approval import ApproveRequest, RejectRequest, ApprovalQueueItem
from app.schemas.draft import DraftResponse
from app.services.approval_service import ApprovalService, ApprovalError
from app.services.send_service import SendService, SendServiceError

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=List[ApprovalQueueItem])
async def list_pending_approvals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List pending drafts requiring review or approval."""
    stmt = (
        select(ReplyDraft, Email)
        .join(Email, ReplyDraft.email_id == Email.id)
        .options(selectinload(Email.classification))
        .where(
            and_(
                Email.user_id == user.id,
                ReplyDraft.status.in_(["PENDING_APPROVAL", "DRAFT_READY"]),
            )
        )
        .order_by(desc(ReplyDraft.updated_at))
    )
    res = await db.execute(stmt)
    items = []
    for draft, email in res.all():
        classification = email.classification
        items.append(
            ApprovalQueueItem(
                draft_id=draft.id,
                email_id=email.id,
                email_subject=email.subject,
                email_sender=email.sender,
                email_received_at=email.received_at,
                email_body=email.body_text,
                is_starred=email.is_starred,
                category=classification.category if classification else "general",
                risk_level=classification.risk_level if classification else "low",
                confidence=classification.confidence if classification else 1.0,
                reasons=classification.reasons if classification else [],
                draft_body=draft.body,
                draft_version=draft.version,
                draft_status=draft.status,
                content_hash=draft.content_hash,
                created_at=draft.created_at,
            )
        )
    return items


@router.post("/{draft_id}/approve", response_model=DraftResponse)
async def approve_and_send(
    draft_id: str,
    payload: ApproveRequest = ApproveRequest(),
    auto_send: bool = Query(True, description="Immediately send once approved"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approves draft for sending.
    If auto_send is True, immediately passes through the dedicated SendService.
    """
    approval_svc = ApprovalService(db)
    send_svc = SendService(db)

    try:
        # Step 1: Validate and record approval
        approved_draft = await approval_svc.approve_draft(
            draft_id=draft_id,
            user_id=user.id,
            comment=payload.comment,
        )

        if not auto_send:
            return approved_draft

        # Step 2: Send through authorized SendService
        sent_draft = await send_svc.send_draft(draft_id=draft_id, user_id=user.id)
        return sent_draft

    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except SendServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/{draft_id}/reject", response_model=DraftResponse)
async def reject_draft(
    draft_id: str,
    payload: RejectRequest = RejectRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rejects reply draft."""
    approval_svc = ApprovalService(db)
    try:
        rejected_draft = await approval_svc.reject_draft(
            draft_id=draft_id,
            user_id=user.id,
            reason=payload.reason or "Rejected by user",
        )
        return rejected_draft
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
