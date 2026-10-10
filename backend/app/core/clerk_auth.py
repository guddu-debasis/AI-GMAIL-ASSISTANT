"""
Verifies the session tokens that Clerk gives the frontend.

Clerk signs each token with RS256. We fetch Clerk's public keys (JWKS) and check
the signature, expiry, issuer and authorized party. The backend never sees a
password: sign in, sign up and the profile screens all live in Clerk.
"""
import base64
import logging
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi.concurrency import run_in_threadpool
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger("gmail_assistant.clerk")


class ClerkAuthError(Exception):
    """The token is expired, forged, or not meant for this app."""


class ClerkNotConfiguredError(Exception):
    """The server has no Clerk settings, so it cannot verify any token."""


def frontend_api_host(publishable_key: str) -> str:
    """
    A publishable key looks like pk_test_<base64 of "host$">.
    Returns the host, or an empty string if the key is malformed.
    """
    parts = publishable_key.strip().split("_", 2)
    if len(parts) != 3 or not parts[2]:
        return ""
    encoded = parts[2]
    try:
        decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""
    return decoded.rstrip("$").strip()


def get_issuer() -> str:
    if settings.CLERK_ISSUER.strip():
        return settings.CLERK_ISSUER.strip().rstrip("/")
    host = frontend_api_host(settings.CLERK_PUBLISHABLE_KEY) if settings.CLERK_PUBLISHABLE_KEY else ""
    return f"https://{host}" if host else ""


def get_jwks_url() -> str:
    if settings.CLERK_JWKS_URL.strip():
        return settings.CLERK_JWKS_URL.strip()
    issuer = get_issuer()
    return f"{issuer}/.well-known/jwks.json" if issuer else ""


@lru_cache(maxsize=4)
def _jwk_client(jwks_url: str) -> PyJWKClient:
    # PyJWKClient keeps the downloaded keys in memory, so Clerk is not called on every request
    return PyJWKClient(jwks_url, cache_keys=True)


async def verify_clerk_token(token: str) -> Dict[str, Any]:
    """Returns the verified claims, or raises ClerkAuthError / ClerkNotConfiguredError."""
    jwks_url = get_jwks_url()
    if not jwks_url:
        raise ClerkNotConfiguredError(
            "Clerk is not configured on the server. Set CLERK_PUBLISHABLE_KEY in the backend .env file."
        )
    issuer = get_issuer()

    try:
        # Fetching keys is a blocking network call, so keep it off the event loop
        signing_key = await run_in_threadpool(_jwk_client(jwks_url).get_signing_key_from_jwt, token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer or None,
            leeway=10,
            options={"require": ["exp", "sub"], "verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        logger.info("Rejected Clerk token: %s", exc)
        raise ClerkAuthError("Invalid or expired token") from exc

    # azp = the website that asked Clerk for this token. Protects against tokens minted for another site.
    allowed_parties = settings.clerk_authorized_parties_list
    azp = claims.get("azp")
    if allowed_parties and azp and azp not in allowed_parties:
        raise ClerkAuthError("Token was issued for a different origin")

    # "pending" means the user still has a step to finish (for example set up MFA)
    if claims.get("sts") == "pending":
        raise ClerkAuthError("Sign in is not finished yet")

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ClerkAuthError("Token has no user")

    return claims


async def resolve_user_email(claims: Dict[str, Any]) -> Optional[str]:
    """
    Session tokens do not carry the email by default. Order of attempts:
    1. an "email" claim (if you added one under Clerk's session token customization)
    2. Clerk Backend API, if CLERK_SECRET_KEY is set
    """
    claim_email = claims.get("email")
    if isinstance(claim_email, str) and claim_email.strip():
        return claim_email.strip().lower()

    if not settings.CLERK_SECRET_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.clerk.com/v1/users/{claims['sub']}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Could not fetch user email from Clerk: %s", exc)
        return None

    addresses = data.get("email_addresses") or []
    primary_id = data.get("primary_email_address_id")
    for item in addresses:
        if item.get("id") == primary_id and item.get("email_address"):
            return str(item["email_address"]).strip().lower()
    if addresses and addresses[0].get("email_address"):
        return str(addresses[0]["email_address"]).strip().lower()
    return None
