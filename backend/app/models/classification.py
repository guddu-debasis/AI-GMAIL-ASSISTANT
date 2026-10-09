from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Float, Integer, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email_id = Column(String(36), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    category = Column(String(64), nullable=False)  # job_recruitment, financial, legal_contractual, complaint_sensitive, general, other
    risk_level = Column(String(32), nullable=False)  # low, medium, high, uncertain
    confidence = Column(Float, nullable=False)
    rationale = Column(Text, nullable=False)
    reasons = Column(JSON, nullable=False, default=list)
    requires_approval = Column(Boolean, nullable=False)
    policy_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    email = relationship("Email", back_populates="classification")
