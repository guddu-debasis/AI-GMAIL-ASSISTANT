import pytest
from datetime import datetime, timezone
from app.models.email import Email
from app.models.reply_draft import ReplyDraft
from app.models.classification import Classification
from app.services.approval_service import ApprovalService, ApprovalError
from app.core.security import compute_content_hash

pytestmark = pytest.mark.asyncio


async def setup_test_draft(test_db, test_user, body="Proposed reply text", status="PENDING_APPROVAL"):
    email = Email(
        user_id=test_user.id,
        gmail_account_id="acc_123",
        gmail_message_id="msg_test_100",
        gmail_thread_id="th_test_100",
        sender="partner@firm.com",
        subject="Discussion Topic",
        body_text="Can we discuss this?",
        received_at=datetime.now(timezone.utc),
        is_starred=False,
    )
    test_db.add(email)
    await test_db.flush()

    classification = Classification(
        email_id=email.id,
        category="general",
        risk_level="low",
        confidence=0.95,
        rationale="Routine",
        reasons=["pending_review"],
        requires_approval=True,
    )
    test_db.add(classification)

    hash_val = compute_content_hash(body)
    draft = ReplyDraft(
        email_id=email.id,
        body=body,
        status=status,
        version=1,
        content_hash=hash_val,
        policy_version=1,
    )
    test_db.add(draft)
    await test_db.commit()
    await test_db.refresh(draft)
    return draft, email


async def test_approve_draft_flow(test_db, test_user):
    draft, _ = await setup_test_draft(test_db, test_user)
    service = ApprovalService(test_db)

    approved = await service.approve_draft(
        draft_id=draft.id,
        user_id=test_user.id,
        expected_content_hash=draft.content_hash,
    )
    assert approved.status == "APPROVED"
    assert approved.approved_by == test_user.id
    assert approved.approved_at is not None
    assert approved.approved_content_hash == draft.content_hash


async def test_editing_invalidates_prior_approval(test_db, test_user):
    """Editing an approved draft must invalidate approval, bump version, and rehash content."""
    draft, _ = await setup_test_draft(test_db, test_user)
    service = ApprovalService(test_db)

    # First approve it
    await service.approve_draft(draft_id=draft.id, user_id=test_user.id)

    # Now edit the draft
    edited = await service.edit_draft(
        draft_id=draft.id,
        user_id=test_user.id,
        new_body="Updated and modified draft text.",
    )

    assert edited.version == 2
    assert edited.body == "Updated and modified draft text."
    assert edited.approved_by is None
    assert edited.approved_at is None
    assert edited.approved_content_hash is None
    # Must not remain in APPROVED state
    assert edited.status in ["PENDING_APPROVAL", "DRAFT_READY"]


async def test_reject_stale_content_hash(test_db, test_user):
    """Attempting to approve with a mismatched content hash must raise an error."""
    draft, _ = await setup_test_draft(test_db, test_user)
    service = ApprovalService(test_db)

    with pytest.raises(ApprovalError) as exc_info:
        await service.approve_draft(
            draft_id=draft.id,
            user_id=test_user.id,
            expected_content_hash="stale_or_wrong_hash_12345",
        )
    assert exc_info.value.status_code == 409


async def test_reject_draft_flow(test_db, test_user):
    """Rejecting draft moves it to REJECTED."""
    draft, _ = await setup_test_draft(test_db, test_user)
    service = ApprovalService(test_db)

    rejected = await service.reject_draft(
        draft_id=draft.id,
        user_id=test_user.id,
        reason="Not appropriate to respond",
    )
    assert rejected.status == "REJECTED"
