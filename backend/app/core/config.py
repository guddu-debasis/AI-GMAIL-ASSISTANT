import os
import base64
from typing import List, Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "dev_secret_key_change_in_production_min32chars!"
    
    # SQLite async fallback for quick testing / dev, Postgres for prod
    DATABASE_URL: str = "sqlite+aiosqlite:///./gmail_assistant.db"
    
    # Google OAuth 2.0 Credentials (loaded from .env)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    
    # LLM Settings
    LLM_PROVIDER: str = "groq"  # "groq" (free, default), "anthropic", or "mock"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-20b"  # fast, responsive model on Groq free tier
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Encryption key for OAuth tokens (Fernet urlsafe base64 32 bytes)
    OAUTH_TOKEN_ENCRYPTION_KEY: str = "dGhpcy1pcy1hLTMyLWJ5dGUtc2VjcmV0LWtleS1mb3ItZGV2IQ=="
    
    # Logging
    LOG_LEVEL: str = "INFO"

    # Clerk (app login). The frontend signs users in, the backend only verifies
    # the session token Clerk gives them.
    # Easiest setup: paste the same publishable key the frontend uses. The backend
    # derives the issuer and the JWKS URL from it.
    CLERK_PUBLISHABLE_KEY: str = ""
    # Optional overrides, normally left empty
    CLERK_ISSUER: str = ""      # example: https://your-app.clerk.accounts.dev
    CLERK_JWKS_URL: str = ""    # example: https://your-app.clerk.accounts.dev/.well-known/jwks.json
    # Optional. Lets the backend look up the user's email on first sign in.
    # Never put this key in the frontend.
    CLERK_SECRET_KEY: str = ""
    # Origins allowed to have generated the token (the "azp" claim).
    # Empty means: reuse CORS_ORIGINS.
    CLERK_AUTHORIZED_PARTIES: str = ""

    # Short lived tokens signed with APP_SECRET_KEY (used for the Gmail connect "state")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Frontend and CORS (comma separated list of allowed origins)
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Default approval policy values
    DEFAULT_APPROVAL_CATEGORIES: Set[str] = {
        "job_recruitment",
        "financial",
        "legal_contractual",
    }
    DEFAULT_APPROVE_WHEN_UNCERTAIN: bool = True
    DEFAULT_APPROVE_STARRED: bool = True
    DEFAULT_ALLOW_AUTO_SEND: bool = False
    DEFAULT_MIN_CONFIDENCE: float = 0.80

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def clerk_authorized_parties_list(self) -> List[str]:
        raw = self.CLERK_AUTHORIZED_PARTIES.strip()
        if not raw:
            return self.cors_origins_list
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
