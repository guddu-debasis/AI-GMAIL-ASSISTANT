from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class UserSettingsBase(BaseModel):
    approval_categories: List[str] = Field(
        default=["job_recruitment", "financial", "legal_contractual"]
    )
    approve_when_uncertain: bool = True
    approve_starred: bool = True
    allow_auto_send: bool = False
    min_confidence: float = Field(default=0.80, ge=0.0, le=1.0)


class UserSettingsUpdate(BaseModel):
    approval_categories: Optional[List[str]] = None
    approve_when_uncertain: Optional[bool] = None
    approve_starred: Optional[bool] = None
    allow_auto_send: Optional[bool] = None
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class UserSettingsResponse(UserSettingsBase):
    user_id: str
    policy_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VIPSenderCreate(BaseModel):
    email_address: str


class VIPSenderResponse(BaseModel):
    id: str
    user_id: str
    email_address: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
