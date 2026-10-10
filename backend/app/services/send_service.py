import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.reply_draft import ReplyDraft
from app.models.email import Email
from app.models.gmail_account import GmailAccount
from app.models.user_settings import UserSettings, VIPSender
from app.models.classification import Classification
from app.models.audit_event import AuditEvent
from app.core.security import compute_content_hash, decrypt_token
from app.services.gmail_service import GmailService, GmailAPIError, get_gmail_service
from app.services.policy_engine import evaluate_policy, Policy, EmailContext
from app.schemas.classification import EmailClassification

logger = logging.getLogger("gmail_assistant.send")


class SendServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SendService:
    """
    Dedicated and ONLY authorized service for sending emails via Gmail.
    Guarantees strict human-in-the-loop authorization, content hash matching,
    and idempotency protections.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_draft(self, draft_id: str, user_id: str) -> ReplyDraft:
        # 1. Fetch draft, email, and gmail account with full join ensuring user ownership
        stmt = (
            select(ReplyDraft, Email, GmailAccount)
            .join(Email, ReplyDraft.email_id == Email.id)
            .outerjoin(GmailAccount, Email.gmail_account_id == GmailAccount.id)
            .where(and_(ReplyDraft.id == draft_id, Email.user_id == user_id))
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            raise SendServiceError("Draft not found or access denied", status_code=status.HTTP_404_NOT_FOUND)

        draft, email, gmail_account = row

        # 2. Strict Invariant: Draft must be explicitly APPROVED
        if draft.status != "APPROVED":
            raise SendServiceError(
                f"Unauthorized send attempt: Draft status is '{draft.status}'. Only drafts in 'APPROVED' status can be sent.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 3. Content hash verification: Current draft hash must equal approved hash
        current_hash = compute_content_hash(draft.body)
        if not draft.approved_content_hash or draft.approved_content_hash != current_hash:
            raise SendServiceError(
                "Integrity check failed: Draft content was modified after approval. Approval is invalidated.",
                status_code=status.HTTP_409_CONFLICT,
            )

        # 4. Re-check current policy to ensure settings haven't changed to invalidate approval
        await self._verify_policy_compliance(draft, email, user_id)

        # 5. Atomic state update to SENDING before invoking external Gmail API
        draft.status = "SENDING"
        draft.updated_at = datetime.now(timezone.utc)
        send_started_event = AuditEvent(
            draft_id=draft.id,
            user_id=user_id,
            event_type="send_started",
            draft_version=draft.version,
            content_hash=current_hash,
            metadata_json={"recipient": email.sender, "subject": email.subject},
        )
        self.db.add(send_started_event)
        await self.db.commit()

        # 6. Execute send through GmailService
        gmail_service = get_gmail_service(gmail_account)
        access_token = ""

        from app.services.gmail_service import refresh_google_access_token, GmailAPIError

        if gmail_account and gmail_account.access_token_encrypted:
            # Check if token is expired or expiring soon (within 2 minutes)
            is_expired = False
            if gmail_account.token_expiry:
                expiry = gmail_account.token_expiry
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                is_expired = (expiry - datetime.now(timezone.utc)).total_seconds() < 120

            if is_expired and gmail_account.refresh_token_encrypted:
                try:
                    access_token = await refresh_google_access_token(self.db, gmail_account)
                except Exception as ref_err:
                    logger.warning("Token refresh failed before send: %s", ref_err)
                    access_token = decrypt_token(gmail_account.access_token_encrypted)
            else:
                access_token = decrypt_token(gmail_account.access_token_encrypted)

        if not access_token and not gmail_service.use_mock:
            raise SendServiceError(
                "Cannot send real email: No connected Gmail account with active credentials found. Please click 'Connect Gmail' to connect your Google account.",
                status_code=400,
            )

        try:
            try:
                send_result = await gmail_service.send_approved_reply(
                    access_token=access_token,
                    thread_id=email.gmail_thread_id,
                    message_id=email.gmail_message_id,
                    recipient=email.sender,
                    subject=email.subject or "Re:",
                    body=draft.body,
                )
            except GmailAPIError as g_err:
                # If access token expired just now, try one refresh and retry
                if "expired" in str(g_err).lower() and gmail_account and gmail_account.refresh_token_encrypted:
                    logger.info("Access token expired during send. Refreshing and retrying...")
                    access_token = await refresh_google_access_token(self.db, gmail_account)
                    send_result = await gmail_service.send_approved_reply(
                        access_token=access_token,
                        thread_id=email.gmail_thread_id,
                        message_id=email.gmail_message_id,
                        recipient=email.sender,
                        subject=email.subject or "Re:",
                        body=draft.body,
                    )
                else:
                    raise

            # 7. Record SENT state and audit trail
            draft.status = "SENT"
            draft.gmail_sent_message_id = send_result.get("id")
            draft.sent_at = datetime.now(timezone.utc)
            draft.updated_at = datetime.now(timezone.utc)

            sent_event = AuditEvent(
                draft_id=draft.id,
                user_id=user_id,
                event_type="sent",
                draft_version=draft.version,
                content_hash=current_hash,
                metadata_json={"gmail_sent_id": draft.gmail_sent_message_id},
            )
            self.db.add(sent_event)
            await self.db.commit()
            await self.db.refresh(draft)
            return draft

        except Exception as exc:
            logger.error("Gmail send failed for draft %s: %s", draft_id, str(exc))
            # On network timeout or uncertain error, fail safe to SEND_UNKNOWN to prevent duplicate sends
            is_timeout = "timeout" in str(exc).lower()
            resulting_status = "SEND_UNKNOWN" if is_timeout else "SEND_FAILED"
            event_type = "send_unknown" if is_timeout else "send_failed"

            draft.status = resulting_status
            draft.updated_at = datetime.now(timezone.utc)

            fail_event = AuditEvent(
                draft_id=draft.id,
                user_id=user_id,
                event_type=event_type,
                draft_version=draft.version,
                content_hash=current_hash,
                metadata_json={"error": str(exc), "reconcile_required": is_timeout},
            )
            self.db.add(fail_event)
            await self.db.commit()
            await self.db.refresh(draft)
            raise SendServiceError(f"Sending failed: {str(exc)}", status_code=500)

    async def _verify_policy_compliance(self, draft: ReplyDraft, email: Email, user_id: str):
        """Re-evaluates user policy immediately prior to sending."""
        vip_res = await self.db.execute(
            select(VIPSender).where(and_(VIPSender.user_id == user_id, VIPSender.email_address == email.sender))
        )
        is_vip = vip_res.scalar_one_or_none() is not None

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

        class_res = await self.db.execute(select(Classification).where(Classification.email_id == email.id))
        class_row = class_res.scalar_one_or_none()
        classification = None
        if class_row:
            classification = EmailClassification(
                category=class_row.category,
                risk_level=class_row.risk_level,
                confidence=class_row.confidence,
                rationale=class_row.rationale,
                requires_caution=True,
            )

        decision = evaluate_policy(email_context, classification, policy)
        # Invariant: If policy requires approval, draft must have been explicitly approved
        if decision.requires_approval and not draft.approved_at:
            raise SendServiceError("Policy re-check failed: Message requires human approval", status_code=403)
