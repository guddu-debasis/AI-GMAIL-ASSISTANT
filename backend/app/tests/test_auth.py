import base64
import time
import types

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import clerk_auth
from app.core.clerk_auth import frontend_api_host, get_issuer, get_jwks_url
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_token
from app.main import app
from app.models.user import User
from app.services import user_service

ISSUER = "https://test-app.clerk.accounts.dev"
ORIGIN = "http://localhost:5173"

PROTECTED_PATHS = [
    "/api/v1/emails",
    "/api/v1/approvals",
    "/api/v1/settings",
    "/api/v1/audit-events",
    "/auth/me",
]


# ---------------------------------------------------------------------------
# Helpers: a fake Clerk. We sign tokens with our own RSA key and tell the
# backend to trust that key instead of downloading Clerk's real ones.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def other_private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _StubJWKClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return types.SimpleNamespace(key=self._public_key)


@pytest.fixture
def clerk_config(monkeypatch, private_key):
    monkeypatch.setattr(settings, "CLERK_ISSUER", ISSUER)
    monkeypatch.setattr(settings, "CLERK_JWKS_URL", f"{ISSUER}/.well-known/jwks.json")
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", "")
    monkeypatch.setattr(settings, "CLERK_SECRET_KEY", "")
    monkeypatch.setattr(settings, "CLERK_AUTHORIZED_PARTIES", ORIGIN)
    stub = _StubJWKClient(private_key.public_key())
    monkeypatch.setattr(clerk_auth, "_jwk_client", lambda url: stub)


def make_token(key, sub="user_test_1", **overrides):
    now = int(time.time())
    claims = {
        "sub": sub,
        "iss": ISSUER,
        "iat": now,
        "nbf": now - 5,
        "exp": now + 300,
        "azp": ORIGIN,
        "sid": "sess_test",
        "v": 2,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(test_db, clerk_config):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def test_issuer_and_jwks_are_derived_from_publishable_key(monkeypatch):
    key = "pk_test_" + base64.b64encode(b"my-app.clerk.accounts.dev$").decode().rstrip("=")
    monkeypatch.setattr(settings, "CLERK_ISSUER", "")
    monkeypatch.setattr(settings, "CLERK_JWKS_URL", "")
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", key)

    assert frontend_api_host(key) == "my-app.clerk.accounts.dev"
    assert get_issuer() == "https://my-app.clerk.accounts.dev"
    assert get_jwks_url() == "https://my-app.clerk.accounts.dev/.well-known/jwks.json"


@pytest.mark.parametrize("bad_key", ["", "nonsense", "pk_test_", "pk_test_!!!"])
def test_malformed_publishable_key_gives_no_host(bad_key):
    assert frontend_api_host(bad_key) == ""


# ---------------------------------------------------------------------------
# Gmail connect "state" tokens (still signed by this app, not by Clerk)
# ---------------------------------------------------------------------------
def test_state_token_roundtrip_and_purpose():
    state = create_access_token("user-123", purpose="oauth_state", expires_minutes=10)
    assert decode_token(state, purpose="oauth_state") == "user-123"
    assert decode_token(state, purpose="access") is None


def test_expired_state_token_is_rejected():
    state = create_access_token("user-123", purpose="oauth_state", expires_minutes=-1)
    assert decode_token(state, purpose="oauth_state") is None


def test_garbage_state_token_is_rejected():
    assert decode_token("") is None
    assert decode_token("not.a.jwt") is None


# ---------------------------------------------------------------------------
# Clerk tokens against the real endpoints
# ---------------------------------------------------------------------------
async def test_valid_token_creates_local_user_and_seeds_default_settings(client, private_key):
    token = make_token(private_key, email="Alice@Example.com")

    me = await client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    settings_res = await client.get("/api/v1/settings", headers=_auth(token))
    assert settings_res.status_code == 200
    data = settings_res.json()
    assert set(data["approval_categories"]) == {"job_recruitment", "financial", "legal_contractual"}
    assert data["allow_auto_send"] is False


async def test_same_clerk_user_always_maps_to_same_local_user(client, private_key):
    token = make_token(private_key)
    first = await client.get("/auth/me", headers=_auth(token))
    second = await client.get("/auth/me", headers=_auth(make_token(private_key)))
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


async def test_email_falls_back_to_placeholder_when_clerk_gives_none(client, private_key):
    me = await client.get("/auth/me", headers=_auth(make_token(private_key, sub="user_NoEmail")))
    assert me.status_code == 200
    assert me.json()["email"] == "user_noemail@clerk.invalid"


async def test_email_can_come_from_clerk_backend_api(client, private_key, monkeypatch):
    async def fake_resolve(claims):
        return "from-api@example.com"

    monkeypatch.setattr(user_service, "resolve_user_email", fake_resolve)
    me = await client.get("/auth/me", headers=_auth(make_token(private_key, sub="user_api")))
    assert me.json()["email"] == "from-api@example.com"


async def test_old_local_account_with_same_email_is_never_taken_over(client, private_key, test_db):
    test_db.add(User(email="taken@example.com"))
    await test_db.commit()

    token = make_token(private_key, sub="user_newcomer", email="taken@example.com")
    me = await client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "user_newcomer@clerk.invalid"


async def test_users_only_see_their_own_data(client, private_key):
    token_a = make_token(private_key, sub="user_a")
    token_b = make_token(private_key, sub="user_b")

    added = await client.post(
        "/api/v1/settings/vip-senders",
        json={"email_address": "boss@corp.com"},
        headers=_auth(token_a),
    )
    assert added.status_code == 200

    vip_a = await client.get("/api/v1/settings/vip-senders", headers=_auth(token_a))
    vip_b = await client.get("/api/v1/settings/vip-senders", headers=_auth(token_b))
    assert len(vip_a.json()) == 1
    assert vip_b.json() == []


async def test_missing_or_garbage_token_is_rejected(client):
    for path in PROTECTED_PATHS:
        assert (await client.get(path)).status_code == 401
    garbage = await client.get("/api/v1/emails", headers=_auth("garbage"))
    assert garbage.status_code == 401


async def test_x_user_email_header_does_not_grant_access(client):
    res = await client.get("/api/v1/emails", headers={"X-User-Email": "demo.user@example.com"})
    assert res.status_code == 401


async def test_expired_token_is_rejected(client, private_key):
    token = make_token(private_key, exp=int(time.time()) - 600, nbf=int(time.time()) - 900)
    assert (await client.get("/auth/me", headers=_auth(token))).status_code == 401


async def test_token_from_another_issuer_is_rejected(client, private_key):
    token = make_token(private_key, iss="https://someone-else.clerk.accounts.dev")
    assert (await client.get("/auth/me", headers=_auth(token))).status_code == 401


async def test_token_for_another_website_is_rejected(client, private_key):
    token = make_token(private_key, azp="https://evil.example")
    assert (await client.get("/auth/me", headers=_auth(token))).status_code == 401


async def test_token_without_azp_is_accepted(client, private_key):
    # Clerk may leave azp out. The docs say to skip the check in that case.
    token = make_token(private_key, azp=None)
    assert (await client.get("/auth/me", headers=_auth(token))).status_code == 200


async def test_token_signed_with_a_different_key_is_rejected(client, other_private_key):
    token = make_token(other_private_key)
    assert (await client.get("/auth/me", headers=_auth(token))).status_code == 401


async def test_pending_session_is_rejected(client, private_key):
    token = make_token(private_key, sts="pending")
    assert (await client.get("/auth/me", headers=_auth(token))).status_code == 401


async def test_app_state_token_cannot_be_used_to_log_in(client):
    state = create_access_token("user-123", purpose="oauth_state", expires_minutes=10)
    assert (await client.get("/auth/me", headers=_auth(state))).status_code == 401


async def test_server_without_clerk_settings_answers_503(client, private_key, monkeypatch):
    monkeypatch.setattr(settings, "CLERK_ISSUER", "")
    monkeypatch.setattr(settings, "CLERK_JWKS_URL", "")
    monkeypatch.setattr(settings, "CLERK_PUBLISHABLE_KEY", "")

    res = await client.get("/auth/me", headers=_auth(make_token(private_key)))
    assert res.status_code == 503
    assert "CLERK_PUBLISHABLE_KEY" in res.json()["detail"]


async def test_google_connect_requires_login_and_callback_checks_state(client, private_key):
    assert (await client.get("/auth/google/start")).status_code == 401

    started = await client.get("/auth/google/start", headers=_auth(make_token(private_key)))
    assert started.status_code == 200

    forged = await client.get("/auth/google/callback", params={"code": "abc", "state": "forged"})
    assert forged.status_code == 400
