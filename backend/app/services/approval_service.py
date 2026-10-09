from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.reply_draft import ReplyDraft
from app.models.email import Email
from app.models.user_settings import UserSettings, VIPSender
from app.models.classification import Classification
from app.models.audit_event import AuditEvent
from app.core.security import compute_content_hash, normalize_content
from app.services.policy_engine import evaluate_policy, Policy, EmailContext
from app.schemas.classification import EmailClassification


class ApprovalError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_draft_with_ownership_check(self, draft_id: str, user_id: str) -> ReplyDraft:
        """Fetch draft and strictly verify user ownership through Email -> User relation."""
        stmt = (
            select(ReplyDraft)
            .join(Email, ReplyDraft.email_id == Email.id)
            .where(and_(ReplyDraft.id == draft_id, Email.user_id == user_id))
        )
        res = await self.db.execute(stmt)
        draft = res.scalar_one_or_none()
        if not draft:
            raise ApprovalError("Draft not found or access denied", status_code=status.HTTP_404_NOT_FOUND)
        return draft

    async def edit_draft(self, draft_id: str, user_id: str, new_body: str) -> ReplyDraft:
        """
        Edit draft body:
        - Recomputes content hash
        - Increments draft version
        - Invalidates any prior approval
        - Clears approved fields
        - Returns draft to review state (PENDING_APPROVAL or DRAFT_READY based on policy)
        - Logs audit event: 'edited' and 'approval_invalidated' if previously approved
        """
        draft = await self.get_draft_with_ownership_check(draft_id, user_id)

        # Cannot edit if currently sending or already sent
        if draft.status in ["SENDING", "SENT"]:
            raise ApprovalError(f"Cannot edit draft in '{draft.status}' state", status_code=400)

        prev_status = draft.status
        was_approved = prev_status == "APPROVED"
        new_normalized = normalize_content(new_body)
        new_hash = compute_content_hash(new_normalized)

        # Increment version and update content
        draft.version += 1
        draft.body = new_normalized
        draft.content_hash = new_hash
        draft.updated_at = datetime.now(timezone.utc)

        # Invalidate prior approval
        if was_approved or draft.approved_at is not None:
            draft.approved_by = None
            draft.approved_at = None
            draft.approved_content_hash = None

            # Audit event for invalidation
            inval_event = AuditEvent(
                draft_id=draft.id,
                user_id=user_id,
                event_type="approval_invalidated",
                draft_version=draft.version,
                content_hash=new_hash,
                metadata_json={"reason": "Draft edited after approval", "previous_status": prev_status},
            )
            self.db.add(inval_event)

        # Re-evaluate policy to determine review status
        review_status = await self._determine_draft_review_state(draft, user_id)
        draft.status = review_status

        # Audit event for edit
        edit_event = AuditEvent(
            draft_id=draft.id,
            user_id=user_id,
            event_type="edited",
            draft_version=draft.version,
            content_hash=new_hash,
            metadata_json={"new_status": draft.status},
        )
        self.db.add(edit_event)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def reject_draft(self, draft_id: str, user_id: str, reason: str = "Rejected by user") -> ReplyDraft:
        """Reject draft and log audit event."""
        draft = await self.get_draft_with_ownership_check(draft_id, user_id)

        if draft.status in ["SENDING", "SENT"]:
            raise ApprovalError(f"Cannot reject draft in '{draft.status}' state", status_code=400)

        draft.status = "REJECTED"
        draft.updated_at = datetime.now(timezone.utc)

        event = AuditEvent(
            draft_id=draft.id,
            user_id=user_id,
            event_type="rejected",
            draft_version=draft.version,
            content_hash=draft.content_hash,
            metadata_json={"reason": reason},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def approve_draft(
        self,
        draft_id: str,
        user_id: str,
        expected_content_hash: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> ReplyDraft:
        """
        Approves draft for sending:
        1. Checks ownership
        2. Validates current state allows approval (PENDING_APPROVAL, DRAFT_READY)
        3. Validates content hash against reviewed version to prevent race conditions
        4. Rechecks current policy and policy version
        5. Sets approved_by, approved_at, approved_content_hash, status="APPROVED"
        6. Logs audit event: 'approved'
        """
        draft = await self.get_draft_with_ownership_check(draft_id, user_id)

        # Invariant check: only reviewable states can be approved
        if draft.status not in ["PENDING_APPROVAL", "DRAFT_READY"]:
            raise ApprovalError(f"Cannot approve draft in status '{draft.status}'", status_code=400)

        current_hash = compute_content_hash(draft.body)
        if draft.content_hash != current_hash:
            raise ApprovalError("Draft content hash mismatch: draft has been modified", status_code=409)

        if expected_content_hash and expected_content_hash != current_hash:
            raise ApprovalError("Draft has been modified since it was loaded in UI", status_code=409)

        # Re-check policy version and policy
        settings_res = await self.db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        user_settings = settings_res.scalar_one_or_none()
        current_policy_version = user_settings.policy_version if user_settings else 1

        draft.status = "APPROVED"
        draft.approved_by = user_id
        draft.approved_at = datetime.now(timezone.utc)
        draft.approved_content_hash = current_hash
        draft.policy_version = current_policy_version
        draft.updated_at = datetime.now(timezone.utc)

        audit_event = AuditEvent(
            draft_id=draft.id,
            user_id=user_id,
            event_type="approved",
            draft_version=draft.version,
            content_hash=current_hash,
            metadata_json={"comment": comment, "policy_version": current_policy_version},
        )
        self.db.add(audit_event)

        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def _determine_draft_review_state(self, draft: ReplyDraft, user_id: str) -> str:
        """Re-evaluates policy to determine whether the draft is PENDING_APPROVAL or DRAFT_READY."""
        email_res = await self.db.execute(select(Email).where(Email.id == draft.email_id))
        email = email_res.scalar_one_or_none()
        if not email:
            return "PENDING_APPROVAL"

        # Check VIP status
        vip_res = await self.db.execute(
            select(VIPSender).where(and_(VIPSender.user_id == user_id, VIPSender.email_address == email.sender))
        )
        is_vip = vip_res.scalar_one_or_none() is not None

        # Fetch settings
        settings_res = await self.db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        user_settings = settings_res.scalar_one_or_none()

        policy = Policy(
            approval_categories=set(user_settings.approval_categories if user_settings else ["job_recruitment", "financial", "legal_contractual"]),
            approve_when_uncertain=user_settings.approve_when_uncertain if user_settings else True,
            approve_starred=user_settings.approve_starred if user_settings else True,
            allow_auto_send=user_settings.allow_auto_send if user_settings else False,
            min_confidence=user_settings.min_confidence if user_settings else 0.80,
        )

        email_context = EmailContext(
            is_starred=email.is_starred,
            sender_is_vip=is_vip,
            sender=email.sender,
            subject=email.subject,
        )

        # Fetch classification
        class_res = await self.db.execute(select(Classification).where(Classification.email_id == email.id))
        classification_row = class_res.scalar_one_or_none()

        if classification_row:
            classification = EmailClassification(
                category=classification_row.category,
                risk_level=classification_row.risk_level,
                confidence=classification_row.confidence,
                rationale=classification_row.rationale,
                requires_caution=True,
            )
        else:
            classification = None

        decision = evaluate_policy(email_context, classification, policy)
        return "PENDING_APPROVAL" if decision.requires_approval else "DRAFT_READY"
