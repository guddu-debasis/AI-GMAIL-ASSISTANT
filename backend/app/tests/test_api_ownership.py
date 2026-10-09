import pytest
from datetime import datetime, timezone
from app.models.user import User
from app.models.email import Email
from app.models.reply_draft import ReplyDraft
from app.services.approval_service import ApprovalService, ApprovalError
from app.services.send_service import SendService, SendServiceError
from app.core.security import compute_content_hash

pytestmark = pytest.mark.asyncio


async def test_cross_user_isolation(test_db, test_user):
    # Create another distinct user B
    user_b = User(email="user_b@example.com")
    test_db.add(user_b)
    await test_db.flush()

    # Create email and draft belonging to User A
    email_a = Email(
        user_id=test_user.id,
        gmail_account_id="acc_user_a",
        gmail_message_id="msg_user_a",
        gmail_thread_id="th_user_a",
        sender="partner@firm.com",
        subject="Confidential Strategy",
        body_text="Confidential details",
        received_at=datetime.now(timezone.utc),
    )
    test_db.add(email_a)
    await test_db.flush()

    draft_a = ReplyDraft(
        email_id=email_a.id,
        body="Draft reply for A",
        status="PENDING_APPROVAL",
        version=1,
        content_hash=compute_content_hash("Draft reply for A"),
        policy_version=1,
    )
    test_db.add(draft_a)
    await test_db.commit()

    approval_svc = ApprovalService(test_db)
    send_svc = SendService(test_db)

    # 1. User B cannot approve User A's draft
    with pytest.raises(ApprovalError) as exc_info:
        await approval_svc.approve_draft(draft_id=draft_a.id, user_id=user_b.id)
    assert exc_info.value.status_code == 404

    # 2. User B cannot edit User A's draft
    with pytest.raises(ApprovalError) as exc_info:
        await approval_svc.edit_draft(draft_id=draft_a.id, user_id=user_b.id, new_body="Hacked content")
    assert exc_info.value.status_code == 404

    # 3. User B cannot send User A's draft
    with pytest.raises(SendServiceError) as exc_info:
        await send_svc.send_draft(draft_id=draft_a.id, user_id=user_b.id)
    assert exc_info.value.status_code == 404
