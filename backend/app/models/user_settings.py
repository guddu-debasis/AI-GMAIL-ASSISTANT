from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Float, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    approval_categories = Column(
        JSON,
        nullable=False,
        default=["job_recruitment", "financial", "legal_contractual"],
    )
    approve_when_uncertain = Column(Boolean, default=True, nullable=False)
    approve_starred = Column(Boolean, default=True, nullable=False)
    allow_auto_send = Column(Boolean, default=False, nullable=False)
    min_confidence = Column(Float, default=0.80, nullable=False)
    policy_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="settings")


class VIPSender(Base):
    __tablename__ = "vip_senders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email_address = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "email_address", name="uq_user_vip_email"),
    )

    user = relationship("User", back_populates="vip_senders")
