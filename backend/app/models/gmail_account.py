from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class GmailAccount(Base):
    __tablename__ = "gmail_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    google_subject = Column(String(255), nullable=False)
    gmail_address = Column(String(255), nullable=False)
    access_token_encrypted = Column(String(1024), nullable=True)
    refresh_token_encrypted = Column(String(1024), nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(JSON, nullable=True)
    status = Column(String(50), default="connected", nullable=False)  # connected, expired, revoked, needs_reauth
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "google_subject", name="uq_user_google_subject"),
    )

    user = relationship("User", back_populates="gmail_accounts")
    emails = relationship("Email", back_populates="gmail_account", cascade="all, delete-orphan")
