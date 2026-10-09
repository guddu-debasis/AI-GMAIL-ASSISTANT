from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class ReplyDraft(Base):
    __tablename__ = "reply_drafts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email_id = Column(String(36), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    body = Column(Text, nullable=False)
    # Statuses: PROCESSING, PENDING_APPROVAL, DRAFT_READY, APPROVED, REJECTED, SENDING, SENT, SEND_FAILED, SEND_UNKNOWN, EXPIRED
    status = Column(String(50), default="PROCESSING", nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    content_hash = Column(String(64), nullable=False)
    policy_version = Column(Integer, default=1, nullable=False)
    approved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_content_hash = Column(String(64), nullable=True)
    gmail_draft_id = Column(String(255), nullable=True)
    gmail_sent_message_id = Column(String(255), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    email = relationship("Email", back_populates="reply_draft")
    approver = relationship("User", foreign_keys=[approved_by])
    audit_events = relationship("AuditEvent", back_populates="reply_draft", cascade="all, delete-orphan")
