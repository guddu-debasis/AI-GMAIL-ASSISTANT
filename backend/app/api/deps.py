from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.clerk_auth import ClerkAuthError, ClerkNotConfiguredError, verify_clerk_token
from app.core.database import get_db
from app.models.user import User
from app.services.user_service import get_or_create_clerk_user

# auto_error=False so we can return a clean 401 with our own message
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the acting user from the "Authorization: Bearer <Clerk session token>" header.
    The token is signed by Clerk, so the caller cannot pick which user they are.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Not authenticated")

    try:
        claims = await verify_clerk_token(credentials.credentials)
    except ClerkNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except ClerkAuthError as exc:
        raise _unauthorized(str(exc))

    return await get_or_create_clerk_user(db, claims)
