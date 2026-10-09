import urllib.parse
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.gmail_account import GmailAccount
from app.core.config import settings
from app.core.security import encrypt_token

router = APIRouter(prefix="/auth/google", tags=["Authentication"])

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]


@router.get("/start")
async def google_oauth_start():
    if not settings.GOOGLE_CLIENT_ID:
        return {
            "message": "Google Client ID not configured. Sandbox mock mode is active for testing.",
            "auth_url": None,
        }

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": url}


@router.get("/callback")
async def google_oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if error or not code:
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {error}")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve token from Google")
        tokens = resp.json()

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    # Fetch user info from Google
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        userinfo_resp = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
        userinfo = userinfo_resp.json()

    google_sub = userinfo.get("sub", "unknown")
    gmail_email = userinfo.get("email", user.email)

    # Save or update GmailAccount with encrypted tokens
    stmt = select(GmailAccount).where(GmailAccount.user_id == user.id)
    res = await db.execute(stmt)
    account = res.scalar_one_or_none()

    if not account:
        account = GmailAccount(
            user_id=user.id,
            google_subject=google_sub,
            gmail_address=gmail_email,
            access_token_encrypted=encrypt_token(access_token),
            refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
            scopes=tokens.get("scope", "").split(),
            status="connected",
        )
        db.add(account)
    else:
        account.google_subject = google_sub
        account.gmail_address = gmail_email
        account.access_token_encrypted = encrypt_token(access_token)
        if refresh_token:
            account.refresh_token_encrypted = encrypt_token(refresh_token)
        account.status = "connected"

    await db.commit()
    # Redirect to frontend dashboard
    return RedirectResponse(url="/?oauth=success")
