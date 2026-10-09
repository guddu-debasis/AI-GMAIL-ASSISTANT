import pytest
from datetime import datetime, timezone
from app.models.email import Email
from app.models.reply_draft import ReplyDraft
from app.models.classification import Classification
from app.services.send_service import SendService, SendServiceError
from app.core.security import compute_content_hash

pytestmark = pytest.mark.asyncio


async def setup_draft_for_send(test_db, test_user, status="PENDING_APPROVAL", is_approved=False):
    email = Email(
        user_id=test_user.id,
        gmail_account_id="acc_send_1",
        gmail_message_id="msg_send_1",
        gmail_thread_id="th_send_1",
        sender="client@corp.com",
        subject="Meeting confirmation",
        body_text="Looking forward to meeting tomorrow.",
        received_at=datetime.now(timezone.utc),
        is_starred=False,
    )
    test_db.add(email)
    await test_db.flush()

    body = "Thank you for confirming. See you tomorrow at 10 AM."
    chash = compute_content_hash(body)

    draft = ReplyDraft(
        email_id=email.id,
        body=body,
        status=status,
        version=1,
        content_hash=chash,
        policy_version=1,
        approved_by=test_user.id if is_approved else None,
        approved_at=datetime.now(timezone.utc) if is_approved else None,
        approved_content_hash=chash if is_approved else None,
    )
    test_db.add(draft)
    await test_db.commit()
    await test_db.refresh(draft)
    return draft, email


async def test_unapproved_draft_cannot_be_sent(test_db, test_user):
    """Any attempt to send an unapproved draft must be blocked with HTTP 403."""
    draft, _ = await setup_draft_for_send(test_db, test_user, status="PENDING_APPROVAL", is_approved=False)
    send_svc = SendService(test_db)

    with pytest.raises(SendServiceError) as exc_info:
        await send_svc.send_draft(draft_id=draft.id, user_id=test_user.id)
    assert exc_info.value.status_code == 403
    assert "Only drafts in 'APPROVED' status can be sent" in exc_info.value.message


async def test_rejected_draft_cannot_be_sent(test_db, test_user):
    """Rejected draft cannot be sent."""
    draft, _ = await setup_draft_for_send(test_db, test_user, status="REJECTED", is_approved=False)
    send_svc = SendService(test_db)

    with pytest.raises(SendServiceError) as exc_info:
        await send_svc.send_draft(draft_id=draft.id, user_id=test_user.id)
    assert exc_info.value.status_code == 403


async def test_tampered_or_unmatched_hash_cannot_be_sent(test_db, test_user):
    """If draft body is altered directly without re-approval, send must fail with conflict error."""
    draft, _ = await setup_draft_for_send(test_db, test_user, status="APPROVED", is_approved=True)
    # Tamper body behind the scenes
    draft.body = "Malicious or altered content inserted without re-approval"
    test_db.add(draft)
    await test_db.commit()

    send_svc = SendService(test_db)
    with pytest.raises(SendServiceError) as exc_info:
        await send_svc.send_draft(draft_id=draft.id, user_id=test_user.id)
    assert exc_info.value.status_code == 409
    assert "Draft content was modified after approval" in exc_info.value.message


async def test_authorized_draft_sends_successfully(test_db, test_user):
    """Properly approved draft transitions to SENT with sent_at timestamp."""
    draft, _ = await setup_draft_for_send(test_db, test_user, status="APPROVED", is_approved=True)
    send_svc = SendService(test_db)

    sent = await send_svc.send_draft(draft_id=draft.id, user_id=test_user.id)
    assert sent.status == "SENT"
    assert sent.sent_at is not None
    assert sent.gmail_sent_message_id is not None


async def test_cannot_send_twice(test_db, test_user):
    """A draft that is already SENT cannot be re-sent."""
    draft, _ = await setup_draft_for_send(test_db, test_user, status="SENT", is_approved=True)
    send_svc = SendService(test_db)

    with pytest.raises(SendServiceError) as exc_info:
        await send_svc.send_draft(draft_id=draft.id, user_id=test_user.id)
    assert exc_info.value.status_code == 403
