from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ApproveRequest(BaseModel):
    comment: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = "Rejected by user"


class AuditEventResponse(BaseModel):
    id: str
    draft_id: str
    user_id: str
    event_type: str
    draft_version: int
    content_hash: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalQueueItem(BaseModel):
    draft_id: str
    email_id: str
    email_subject: Optional[str]
    email_sender: str
    email_received_at: Optional[datetime]
    email_body: Optional[str]
    is_starred: bool
    category: str
    risk_level: str
    confidence: float
    reasons: list[str]
    draft_body: str
    draft_version: int
    draft_status: str
    content_hash: str
    created_at: datetime
