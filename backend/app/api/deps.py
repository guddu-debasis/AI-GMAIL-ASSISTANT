from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.core.config import settings


async def get_current_user(
    x_user_email: Optional[str] = Header(default="demo.user@example.com"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to resolve the acting authenticated user.
    Supports multi-user isolation via X-User-Email header.
    Automatically seeds default user and initial user settings on first access.
    """
    email = (x_user_email or "demo.user@example.com").strip().lower()
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        user = User(email=email)
        db.add(user)
        await db.flush()

        # Seed initial user settings with required defaults (README Section 2)
        user_settings = UserSettings(
            user_id=user.id,
            approval_categories=list(settings.DEFAULT_APPROVAL_CATEGORIES),
            approve_when_uncertain=settings.DEFAULT_APPROVE_WHEN_UNCERTAIN,
            approve_starred=settings.DEFAULT_APPROVE_STARRED,
            allow_auto_send=settings.DEFAULT_ALLOW_AUTO_SEND,
            min_confidence=settings.DEFAULT_MIN_CONFIDENCE,
            policy_version=1,
        )
        db.add(user_settings)
        await db.commit()
        await db.refresh(user)

    return user
