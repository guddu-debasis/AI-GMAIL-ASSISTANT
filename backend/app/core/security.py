import hashlib
import re
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.OAUTH_TOKEN_ENCRYPTION_KEY
    if not key:
        # Generate safe fallback key if not provided (dev only)
        key = Fernet.generate_key().decode()
    # Fernet expects 32-byte urlsafe base64 encoded bytes
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plain_token: str) -> str:
    """Encrypt OAuth token before storing in database."""
    if not plain_token:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt stored OAuth token."""
    if not encrypted_token:
        return ""
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


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
