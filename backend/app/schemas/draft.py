from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DraftUpdate(BaseModel):
    body: str


class DraftResponse(BaseModel):
    id: str
    email_id: str
    body: str
    status: str
    version: int
    content_hash: str
    policy_version: int
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_content_hash: Optional[str] = None
    gmail_draft_id: Optional[str] = None
    gmail_sent_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
