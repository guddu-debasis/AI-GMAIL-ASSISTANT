import pytest
from app.services.gmail_service import GmailService


def test_mime_threading_headers():
    svc = GmailService(use_mock=True)
    msg = svc._construct_mime_message(
        recipient="partner@corp.com",
        subject="Important project proposal",
        body="Yes, we accept the proposal.",
        in_reply_to="<original-message-id-999@corp.com>",
    )

    assert msg["To"] == "partner@corp.com"
    assert msg["Subject"] == "Re: Important project proposal"
    assert msg["In-Reply-To"] == "<original-message-id-999@corp.com>"
    assert msg["References"] == "<original-message-id-999@corp.com>"


def test_subject_re_prefix_not_duplicated():
    svc = GmailService(use_mock=True)
    msg = svc._construct_mime_message(
        recipient="partner@corp.com",
        subject="Re: Already has Re prefix",
        body="Understood.",
        in_reply_to="<msg-123>",
    )
    assert msg["Subject"] == "Re: Already has Re prefix"
