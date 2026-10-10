from typing import Dict, Any, List
from datetime import datetime, timezone
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.gmail_account import GmailAccount
from app.models.email import Email
from app.models.classification import Classification
from app.models.reply_draft import ReplyDraft
from app.models.user_settings import UserSettings, VIPSender
from app.models.audit_event import AuditEvent
from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token, compute_content_hash
from app.services.gmail_service import GmailService, get_gmail_service
from app.services.llm_provider import get_llm_provider
from app.services.reply_generator import ReplyGenerator
from app.services.policy_engine import evaluate_policy, Policy, EmailContext
from app.schemas.email import EmailSyncResponse

router = APIRouter(prefix="/gmail", tags=["Gmail"])


@router.get("/status")
async def get_gmail_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(GmailAccount).where(GmailAccount.user_id == user.id)
    res = await db.execute(stmt)
    account = res.scalar_one_or_none()

    if not account:
        return {
            "connected": False,
            "status": "disconnected",
            "gmail_address": None,
            "message": "No Gmail account connected. Using demo sandbox or connect Google OAuth.",
        }

    return {
        "connected": account.status == "connected",
        "status": account.status,
        "gmail_address": account.gmail_address,
        "connected_at": account.created_at,
    }


@router.post("/sync", response_model=EmailSyncResponse)
async def sync_emails(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronizes emails from Gmail:
    - Normalizes message and thread context
    - Deduplicates by (gmail_account_id, gmail_message_id)
    - Classifies email with LLM
    - Evaluates deterministic user policy
    - Generates reply draft
    - Persists Email, Classification, Draft, and Audit event
    - Leaves draft in PENDING_APPROVAL or DRAFT_READY (never automatically sent)
    """
    # Find or create a demo/connected account for the user
    stmt = select(GmailAccount).where(GmailAccount.user_id == user.id)
    res = await db.execute(stmt)
    account = res.scalar_one_or_none()

    if not account:
        account = GmailAccount(
            user_id=user.id,
            google_subject="sub_mock_12345",
            gmail_address=f"{user.email.split('@')[0]}@gmail.com",
            status="connected",
        )
        db.add(account)
        await db.flush()

    # Load user policy and VIP senders
    settings_res = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    user_settings = settings_res.scalar_one_or_none()

    vip_res = await db.execute(select(VIPSender).where(VIPSender.user_id == user.id))
    vip_senders = {vip.email_address.lower() for vip in vip_res.scalars().all()}

    policy = Policy(
        approval_categories=set(user_settings.approval_categories if user_settings else ["job_recruitment", "financial", "legal_contractual"]),
        approve_when_uncertain=user_settings.approve_when_uncertain if user_settings else True,
        approve_starred=user_settings.approve_starred if user_settings else True,
        allow_auto_send=user_settings.allow_auto_send if user_settings else False,
        min_confidence=user_settings.min_confidence if user_settings else 0.80,
    )

    gmail_service = get_gmail_service(account)
    llm_provider = get_llm_provider()
    reply_gen = ReplyGenerator(llm_provider)

    from app.services.gmail_service import refresh_google_access_token, GmailAPIError

    access_token = ""
    if account and account.access_token_encrypted:
        # Check expiry safely (handling both naive SQLite and aware datetimes)
        is_expired = False
        if account.token_expiry:
            expiry = account.token_expiry
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            is_expired = (expiry - datetime.now(timezone.utc)).total_seconds() < 120

        if is_expired and account.refresh_token_encrypted:
            try:
                access_token = await refresh_google_access_token(db, account)
            except Exception as ref_err:
                logger.warning("Token refresh failed during sync: %s", ref_err)
                access_token = decrypt_token(account.access_token_encrypted)
        else:
            access_token = decrypt_token(account.access_token_encrypted)

    if account and account.access_token_encrypted and not access_token and not gmail_service.use_mock:
        raise HTTPException(
            status_code=400,
            detail="Google token encryption key changed. Please click 'Reconnect / Switch Google Account' to re-authorize once.",
        )

    try:
        messages_meta = await gmail_service.list_messages(access_token, max_results=5)
    except GmailAPIError as g_err:
        if "expired" in str(g_err).lower() and account and account.refresh_token_encrypted:
            access_token = await refresh_google_access_token(db, account)
            messages_meta = await gmail_service.list_messages(access_token, max_results=5)
        else:
            raise HTTPException(status_code=400, detail=str(g_err))

    synced_count = 0
    drafted_count = 0

    for item in messages_meta:
        msg_id = item["id"]

        # Deduplication check: unique constraint on (gmail_account_id, gmail_message_id)
        existing_res = await db.execute(
            select(Email).where(
                and_(
                    Email.gmail_account_id == account.id,
                    Email.gmail_message_id == msg_id,
                )
            )
        )
        if existing_res.scalar_one_or_none():
            continue  # Already ingested

        raw_msg = await gmail_service.fetch_message(access_token, msg_id)
        headers = raw_msg.get("headers", {})
        sender = headers.get("from", "unknown@example.com")
        subject = headers.get("subject", "(No Subject)")
        body = raw_msg.get("body", raw_msg.get("snippet", ""))
        is_starred = raw_msg.get("is_starred", "STARRED" in raw_msg.get("labelIds", []))

        # 1. Create Email record
        email_record = Email(
            user_id=user.id,
            gmail_account_id=account.id,
            gmail_message_id=msg_id,
            gmail_thread_id=raw_msg.get("threadId", msg_id),
            sender=sender,
            subject=subject,
            body_text=body,
            received_at=datetime.now(timezone.utc),
            is_starred=is_starred,
            processing_status="PROCESSED",
        )
        db.add(email_record)
        await db.flush()

        # 2. Classify email with LLM
        classification_context = f"Sender: {sender}\nSubject: {subject}\nBody: {body}"
        classification = await llm_provider.classify_email(classification_context)

        # 3. Evaluate deterministic policy
        sender_clean = sender.split("<")[-1].replace(">", "").strip().lower()
        is_vip = sender_clean in vip_senders
        email_context = EmailContext(
            is_starred=is_starred,
            sender_is_vip=is_vip,
            sender=sender,
            subject=subject,
        )
        decision = evaluate_policy(email_context, classification, policy)

        # 4. Save Classification record
        classification_record = Classification(
            email_id=email_record.id,
            category=classification.category,
            risk_level=classification.risk_level,
            confidence=classification.confidence,
            rationale=classification.rationale,
            reasons=decision.reasons,
            requires_approval=decision.requires_approval,
            policy_version=user_settings.policy_version if user_settings else 1,
        )
        db.add(classification_record)

        # 5. Generate contextual reply proposal
        draft_reply = await reply_gen.generate(sender=sender, subject=subject, body=body)
        content_hash = compute_content_hash(draft_reply)

        draft_status = "PENDING_APPROVAL" if decision.requires_approval else "DRAFT_READY"

        draft_record = ReplyDraft(
            email_id=email_record.id,
            body=draft_reply,
            status=draft_status,
            version=1,
            content_hash=content_hash,
            policy_version=user_settings.policy_version if user_settings else 1,
        )
        db.add(draft_record)
        await db.flush()

        # 6. Audit Event
        audit_event = AuditEvent(
            draft_id=draft_record.id,
            user_id=user.id,
            event_type="created",
            draft_version=1,
            content_hash=content_hash,
            metadata_json={"reasons": decision.reasons, "initial_status": draft_status},
        )
        db.add(audit_event)

        synced_count += 1
        drafted_count += 1

    await db.commit()

    return EmailSyncResponse(
        message=f"Sync completed successfully. {synced_count} new messages processed.",
        synced_count=synced_count,
        drafted_count=drafted_count,
    )
