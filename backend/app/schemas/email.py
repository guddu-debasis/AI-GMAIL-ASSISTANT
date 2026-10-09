from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.classification import ClassificationResponse
from app.schemas.draft import DraftResponse


class EmailListItem(BaseModel):
    id: str
    user_id: str
    gmail_account_id: str
    gmail_message_id: str
    gmail_thread_id: str
    sender: str
    subject: Optional[str] = None
    received_at: Optional[datetime] = None
    is_starred: bool
    processing_status: str
    created_at: datetime
    classification: Optional[ClassificationResponse] = None
    reply_draft: Optional[DraftResponse] = None

    model_config = ConfigDict(from_attributes=True)


class EmailDetailResponse(EmailListItem):
    body_text: Optional[str] = None


class EmailSyncResponse(BaseModel):
    message: str
    synced_count: int
    drafted_count: int
