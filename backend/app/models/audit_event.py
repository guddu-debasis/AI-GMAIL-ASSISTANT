from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class AuditEvent(Base):
    __tablename__ = "approval_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    draft_id = Column(String(36), ForeignKey("reply_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Event types: created, requested, edited, approved, rejected, approval_invalidated, send_started, sent, send_failed, send_unknown, policy_rechecked
    event_type = Column(String(50), nullable=False, index=True)
    draft_version = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    reply_draft = relationship("ReplyDraft", back_populates="audit_events")
    user = relationship("User", back_populates="audit_events")
