from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    """
    Returns the signed in user. The frontend calls this right after sign in,
    which also creates the local user row the first time.
    """
    return user
