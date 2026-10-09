from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.draft import DraftUpdate, DraftResponse
from app.services.approval_service import ApprovalService, ApprovalError
from app.services.send_service import SendService, SendServiceError

router = APIRouter(prefix="/drafts", tags=["Drafts"])


@router.patch("/{draft_id}", response_model=DraftResponse)
async def update_draft_content(
    draft_id: str,
    payload: DraftUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Edits draft text.
    Strict Invariant: Invalidate any previous approval, bumps draft version,
    recalculates content hash, and returns to review state.
    """
    approval_svc = ApprovalService(db)
    try:
        updated = await approval_svc.edit_draft(
            draft_id=draft_id,
            user_id=user.id,
            new_body=payload.body,
        )
        return updated
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/{draft_id}/send", response_model=DraftResponse)
async def send_draft(
    draft_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dedicated Send endpoint.
    Sends only if draft is currently in APPROVED state and content hash matches.
    """
    send_svc = SendService(db)
    try:
        sent = await send_svc.send_draft(draft_id=draft_id, user_id=user.id)
        return sent
    except SendServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
