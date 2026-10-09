from typing import Literal, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

Category = Literal[
    "job_recruitment",
    "financial",
    "legal_contractual",
    "complaint_sensitive",
    "general",
    "other",
]

RiskLevel = Literal["low", "medium", "high", "uncertain"]


class EmailClassification(BaseModel):
    category: Category
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    requires_caution: bool = True


class ClassificationResponse(BaseModel):
    id: str
    email_id: str
    category: Category
    risk_level: RiskLevel
    confidence: float
    rationale: str
    reasons: List[str]
    requires_approval: bool
    policy_version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
