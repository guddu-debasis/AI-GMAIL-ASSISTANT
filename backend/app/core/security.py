import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.OAUTH_TOKEN_ENCRYPTION_KEY
    if key:
        if isinstance(key, str):
            key = key.encode("utf-8")
        try:
            return Fernet(key)
        except Exception:
            pass
    # Deterministic fallback derived stably from APP_SECRET_KEY
    derived_32 = hashlib.sha256(settings.APP_SECRET_KEY.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(derived_32)
    return Fernet(fernet_key)


def encrypt_token(plain_token: str) -> str:
    """Encrypt OAuth token before storing in database."""
    if not plain_token:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt stored OAuth token. Returns empty string if token is invalid or corrupted."""
    if not encrypted_token:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def normalize_content(text: str) -> str:
    """
    Normalizes email / draft body text before computing cryptographic hash.
    Standardizes line breaks and trims trailing whitespace.
    """
    if text is None:
        return ""
    # Normalize Windows and Mac line endings to standard \n
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip leading/trailing whitespaces per line
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def compute_content_hash(text: str) -> str:
    """
    Computes deterministic SHA-256 hash of normalized draft text.
    Used for verifying that the exact reviewed draft version is what is being sent.
    """
    normalized = normalize_content(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Short lived app tokens (HS256, signed with APP_SECRET_KEY).
# These are NOT login tokens. Login is handled by Clerk (see core/clerk_auth.py).
# They are used for the Gmail connect "state" value, and "purpose" makes sure
# a token made for one job can never be used for another.
# ---------------------------------------------------------------------------
def create_access_token(
    user_id: str,
    purpose: str = "access",
    expires_minutes: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES if expires_minutes is None else expires_minutes
    payload = {
        "sub": user_id,
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, purpose: str = "access") -> Optional[str]:
    """Returns the user id if the token is valid, not expired, and has the right purpose."""
    try:
        payload = jwt.decode(
            token,
            settings.APP_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) and subject else None
