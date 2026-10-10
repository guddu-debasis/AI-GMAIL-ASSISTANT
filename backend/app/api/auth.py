import urllib.parse
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.gmail_account import GmailAccount
from app.core.config import settings
from app.core.security import create_access_token, decode_token, encrypt_token

# This router connects a Gmail account to an already logged in app user.
# App login itself lives in app/api/auth_local.py.
router = APIRouter(prefix="/auth/google", tags=["Gmail Connection"])

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]


@router.get("/start")
async def google_oauth_start(user: User = Depends(get_current_user)):
    if not settings.GOOGLE_CLIENT_ID:
        return {
            "message": "Google Client ID not configured. Sandbox mock mode is active for testing.",
            "auth_url": None,
        }

    # The browser comes back from Google without our Authorization header.
    # A short-lived signed "state" tells the callback which user started this,
    # and also protects against forged callbacks (CSRF).
    state = create_access_token(user.id, purpose="oauth_state", expires_minutes=10)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": url}


@router.get("/callback")
async def google_oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if error or not code:
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {error}")

    user_id = decode_token(state or "", purpose="oauth_state")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state. Start the connection again.")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

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

    from datetime import datetime, timezone, timedelta
    expires_in = tokens.get("expires_in", 3600)
    token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if not account:
        account = GmailAccount(
            user_id=user.id,
            google_subject=google_sub,
            gmail_address=gmail_email,
            access_token_encrypted=encrypt_token(access_token),
            refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
            token_expiry=token_expiry,
            scopes=tokens.get("scope", "").split(),
            status="connected",
        )
        db.add(account)
    else:
        # If this was previously a mock demo account, purge mock emails so only real messages display
        if account.google_subject == "sub_mock_12345":
            from app.models.email import Email
            from sqlalchemy import delete
            await db.execute(delete(Email).where(Email.gmail_account_id == account.id))

        account.google_subject = google_sub
        account.gmail_address = gmail_email
        account.access_token_encrypted = encrypt_token(access_token)
        if refresh_token:
            account.refresh_token_encrypted = encrypt_token(refresh_token)
        account.token_expiry = token_expiry
        account.status = "connected"

    await db.commit()
    # Redirect to frontend dashboard
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/?oauth=success")
