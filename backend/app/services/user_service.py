from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clerk_auth import resolve_user_email
from app.core.config import settings
from app.models.user import User
from app.models.user_settings import UserSettings


def placeholder_email(clerk_user_id: str) -> str:
    """Used when Clerk did not tell us the email. The .invalid domain can never be a real address."""
    return f"{clerk_user_id.lower()}@clerk.invalid"


async def create_user_with_defaults(
    db: AsyncSession,
    email: str,
    clerk_user_id: Optional[str] = None,
) -> User:
    """
    Creates a user and seeds the required default approval settings
    (README Section 2). Commits the transaction.
    """
    user = User(email=email, clerk_user_id=clerk_user_id)
    db.add(user)
    await db.flush()

    db.add(
        UserSettings(
            user_id=user.id,
            approval_categories=list(settings.DEFAULT_APPROVAL_CATEGORIES),
            approve_when_uncertain=settings.DEFAULT_APPROVE_WHEN_UNCERTAIN,
            approve_starred=settings.DEFAULT_APPROVE_STARRED,
            allow_auto_send=settings.DEFAULT_ALLOW_AUTO_SEND,
            min_confidence=settings.DEFAULT_MIN_CONFIDENCE,
            policy_version=1,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user


async def _find_by_clerk_id(db: AsyncSession, clerk_user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    return result.scalar_one_or_none()


async def get_or_create_clerk_user(db: AsyncSession, claims: Dict[str, Any]) -> User:
    """
    Maps a verified Clerk token to our own users table.
    The first time a Clerk user calls the API, a local row (plus default settings) is created.
    """
    clerk_user_id = claims["sub"]

    user = await _find_by_clerk_id(db, clerk_user_id)
    if user:
        return user

    email = await resolve_user_email(claims) or placeholder_email(clerk_user_id)

    try:
        return await create_user_with_defaults(db, email=email, clerk_user_id=clerk_user_id)
    except IntegrityError:
        await db.rollback()

    # Either another request created this user at the same moment (fine, use that row),
    # or an older local account already uses this email.
    user = await _find_by_clerk_id(db, clerk_user_id)
    if user:
        return user

    # Never merge into an old account just because the email matches.
    return await create_user_with_defaults(
        db,
        email=placeholder_email(clerk_user_id),
        clerk_user_id=clerk_user_id,
    )
