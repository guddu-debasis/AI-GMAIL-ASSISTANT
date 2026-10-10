import email.mime.text
import base64
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from app.core.security import decrypt_token

from app.services.email_parser import extract_plain_text_from_mime, parse_email_headers

logger = logging.getLogger("gmail_assistant.gmail")


class GmailAPIError(Exception):
    pass


class GmailService:
    """Gmail API integration supporting live Google REST API and mock test data."""

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock

    async def list_messages(self, access_token: str, query: str = "label:INBOX", max_results: int = 20) -> List[Dict[str, Any]]:
        if self.use_mock and not access_token:
            return self._get_mock_message_list()

        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params = {"q": query, "maxResults": max_results}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 401:
                raise GmailAPIError("Gmail token expired or revoked. Please re-authenticate.")
            resp.raise_for_status()
            data = resp.json()
            return data.get("messages", [])

    async def fetch_message(self, access_token: str, message_id: str) -> Dict[str, Any]:
        if self.use_mock and not access_token:
            mock_item = self._get_mock_message_by_id(message_id)
            if mock_item:
                return mock_item
            raise GmailAPIError(f"Message {message_id} not found in mock store")

        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
        params = {"format": "full"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 401:
                raise GmailAPIError("Gmail token expired or revoked. Please re-authenticate.")
            resp.raise_for_status()
            data = resp.json()

            # Normalize real Gmail API message format
            payload = data.get("payload", {})
            header_list = payload.get("headers", [])
            headers_dict = parse_email_headers(header_list)
            body_text = extract_plain_text_from_mime(payload)
            labels = data.get("labelIds", [])

            return {
                "id": data.get("id"),
                "threadId": data.get("threadId"),
                "labelIds": labels,
                "headers": headers_dict,
                "snippet": data.get("snippet", ""),
                "body": body_text or data.get("snippet", ""),
                "is_starred": "STARRED" in labels,
            }

    async def fetch_thread(self, access_token: str, thread_id: str) -> Dict[str, Any]:
        if self.use_mock and not access_token:
            return {"id": thread_id, "messages": [self._get_mock_message_by_id(thread_id) or {}]}

        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 401:
                raise GmailAPIError("Gmail token expired or revoked. Please re-authenticate.")
            resp.raise_for_status()
            return resp.json()

    async def create_reply_draft(
        self,
        access_token: str,
        thread_id: str,
        message_id: str,
        recipient: str,
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        """Creates a draft in Gmail. Never sends it."""
        if self.use_mock and not access_token:
            return {"id": f"mock_draft_{message_id}", "message": {"id": f"msg_draft_{message_id}", "threadId": thread_id}}

        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        raw_mime = self._construct_mime_message(
            recipient=recipient,
            subject=subject,
            body=body,
            in_reply_to=message_id,
        )
        payload = {
            "message": {
                "threadId": thread_id,
                "raw": base64.urlsafe_b64encode(raw_mime.as_bytes()).decode("utf-8"),
            }
        }
        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def send_approved_reply(
        self,
        access_token: str,
        thread_id: str,
        message_id: str,
        recipient: str,
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Sends reply message directly via Gmail API.
        Must only be called by dedicated SendService after final authorization!
        """
        if self.use_mock and not access_token:
            # Simulate send ONLY in mock test fixture mode
            return {
                "id": f"mock_sent_{datetime.now(timezone.utc).timestamp()}",
                "threadId": thread_id,
                "status": "SENT",
            }

        if not access_token:
            raise GmailAPIError("Cannot send email: No active Gmail OAuth access token found. Please connect your Gmail account.")

        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        raw_mime = self._construct_mime_message(
            recipient=recipient,
            subject=subject,
            body=body,
            in_reply_to=message_id,
        )
        payload = {
            "threadId": thread_id,
            "raw": base64.urlsafe_b64encode(raw_mime.as_bytes()).decode("utf-8"),
        }
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 401:
                raise GmailAPIError("Gmail access token has expired. Please re-authenticate.")
            if resp.status_code != 200:
                raise GmailAPIError(f"Gmail API send failed ({resp.status_code}): {resp.text}")
            return resp.json()

    def _construct_mime_message(
        self,
        recipient: str,
        subject: str,
        body: str,
        in_reply_to: Optional[str] = None,
    ) -> email.mime.text.MIMEText:
        msg = email.mime.text.MIMEText(body, "plain", "utf-8")
        msg["To"] = recipient
        msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to
        return msg

    def _get_mock_message_list(self) -> List[Dict[str, Any]]:
        return [
            {"id": "msg_recruitment_001", "threadId": "th_recruitment_001"},
            {"id": "msg_invoice_002", "threadId": "th_invoice_002"},
            {"id": "msg_contract_003", "threadId": "th_contract_003"},
            {"id": "msg_starred_vip_004", "threadId": "th_starred_vip_004"},
            {"id": "msg_routine_005", "threadId": "th_routine_005"},
        ]

    def _get_mock_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        mocks = {
            "msg_recruitment_001": {
                "id": "msg_recruitment_001",
                "threadId": "th_recruitment_001",
                "labelIds": ["INBOX"],
                "headers": {
                    "from": "sarah.connor@talent-tech.io",
                    "subject": "Senior AI Architect role - Next steps & Interview invitation",
                    "date": "2026-10-09T09:30:00Z",
                    "message-id": "<recruitment-001@talent-tech.io>",
                },
                "snippet": "Hi, We loved your background and would like to invite you for a 45-minute technical discussion next Tuesday.",
                "body": "Hi,\n\nWe loved your profile and track record in AI systems. The leadership team at TalentTech would like to invite you for a 45-minute technical discussion next Tuesday at 2 PM PST.\n\nPlease let us know if that time works or suggest alternative slots.\n\nBest,\nSarah Connor\nExecutive Recruiter",
                "is_starred": False,
            },
            "msg_invoice_002": {
                "id": "msg_invoice_002",
                "threadId": "th_invoice_002",
                "labelIds": ["INBOX"],
                "headers": {
                    "from": "billing@cloudinfra-solutions.com",
                    "subject": "Invoice #INV-2026-8812 - Due October 20th ($4,250.00)",
                    "date": "2026-10-09T10:15:00Z",
                    "message-id": "<billing-8812@cloudinfra-solutions.com>",
                },
                "snippet": "Attached is invoice #INV-2026-8812 for cloud cluster compute services totaling $4,250.00.",
                "body": "Hello,\n\nPlease find attached the billing statement and wire payment instructions for invoice #INV-2026-8812 totaling $4,250.00. Payment is due within 10 days.\n\nKindly confirm receipt.\n\nAccounts Receivable\nCloudInfra Solutions",
                "is_starred": False,
            },
            "msg_contract_003": {
                "id": "msg_contract_003",
                "threadId": "th_contract_003",
                "labelIds": ["INBOX"],
                "headers": {
                    "from": "legal@venturepartners.com",
                    "subject": "Mutual Non-Disclosure Agreement (NDA) for Execution",
                    "date": "2026-10-09T11:00:00Z",
                    "message-id": "<legal-nda-99@venturepartners.com>",
                },
                "snippet": "Please review and sign the attached mutual NDA prior to our strategic partnership briefing.",
                "body": "Dear Partner,\n\nPlease review the attached mutual NDA regarding our strategic technology briefing. We require signature by an authorized officer prior to sharing confidential system metrics.\n\nSincerely,\nLegal & Compliance Office\nVenture Partners",
                "is_starred": False,
            },
            "msg_starred_vip_004": {
                "id": "msg_starred_vip_004",
                "threadId": "th_starred_vip_004",
                "labelIds": ["INBOX", "STARRED"],
                "headers": {
                    "from": "ceo@ourcompany.com",
                    "subject": "URGENT: Q4 Board Deck Review & Strategy alignment",
                    "date": "2026-10-09T12:00:00Z",
                    "message-id": "<ceo-urgent-board-4@ourcompany.com>",
                },
                "snippet": "Can you check the product roadmap slide in the Q4 board deck before 5pm today?",
                "body": "Team,\n\nPlease review the product roadmap slides for the upcoming Q4 board meeting. Need any final comments or updates submitted before 5 PM today.\n\nThanks,\nChief Executive Officer",
                "is_starred": True,
            },
            "msg_routine_005": {
                "id": "msg_routine_005",
                "threadId": "th_routine_005",
                "labelIds": ["INBOX"],
                "headers": {
                    "from": "newsletter@techdigest.dev",
                    "subject": "Weekly Tech Digest: Issue 42 - What is new in Python & Web Standards",
                    "date": "2026-10-09T08:00:00Z",
                    "message-id": "<digest-42@techdigest.dev>",
                },
                "snippet": "Welcome to this week's highlights covering async web engines and API architectures.",
                "body": "Hello reader,\n\nHere are this week's top engineering articles and tutorials on web frameworks, database concurrency, and modern API standards.\n\nEnjoy reading!\nThe TechDigest Team",
                "is_starred": False,
            },
        }
        return mocks.get(message_id)


def get_gmail_service(account: Optional[Any] = None) -> GmailService:
    # If account has live token, use live service, else mock
    use_mock = True
    if account and getattr(account, "access_token_encrypted", None):
        decrypted = decrypt_token(account.access_token_encrypted)
        if decrypted:
            use_mock = False
    return GmailService(use_mock=use_mock)


async def refresh_google_access_token(db: Any, account: Any) -> str:
    """
    Refreshes an expired Google OAuth access token using stored refresh_token_encrypted.
    Updates the database with the new encrypted access token and new expiry timestamp.
    """
    if not account or not getattr(account, "refresh_token_encrypted", None):
        raise GmailAPIError("No refresh token stored. Re-authorization via Google OAuth required.")

    from datetime import timedelta
    from app.core.config import settings
    from app.core.security import encrypt_token

    refresh_token = decrypt_token(account.refresh_token_encrypted)
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data=data)
        if resp.status_code != 200:
            account.status = "needs_reauth"
            await db.commit()
            raise GmailAPIError(f"Google token refresh failed ({resp.status_code}). Please re-connect your Gmail account.")
        tokens = resp.json()

    new_access_token = tokens["access_token"]
    account.access_token_encrypted = encrypt_token(new_access_token)
    expires_in = tokens.get("expires_in", 3600)
    account.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    account.status = "connected"
    await db.commit()
    logger.info("Successfully refreshed Google access token for %s", account.gmail_address)
    return new_access_token
