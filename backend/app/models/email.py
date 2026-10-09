from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class Email(Base):
    __tablename__ = "emails"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gmail_account_id = Column(String(36), ForeignKey("gmail_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    gmail_message_id = Column(String(255), nullable=False)
    gmail_thread_id = Column(String(255), nullable=False, index=True)
    sender = Column(String(255), nullable=False, index=True)
    subject = Column(String(512), nullable=True)
    body_text = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    is_starred = Column(Boolean, default=False, nullable=False)
    processing_status = Column(String(50), default="PROCESSED", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("gmail_account_id", "gmail_message_id", name="uq_gmail_account_message"),
    )

    user = relationship("User", back_populates="emails")
    gmail_account = relationship("GmailAccount", back_populates="emails")
    classification = relationship("Classification", back_populates="email", uselist=False, cascade="all, delete-orphan")
    reply_draft = relationship("ReplyDraft", back_populates="email", uselist=False, cascade="all, delete-orphan")
