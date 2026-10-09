import os
import base64
from typing import Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "dev_secret_key_change_in_production_min32chars!"
    
    # SQLite async fallback for quick testing / dev, Postgres for prod
    DATABASE_URL: str = "sqlite+aiosqlite:///./gmail_assistant.db"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    
    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "mock", "anthropic", "groq"
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Encryption key for OAuth tokens (Fernet urlsafe base64 32 bytes)
    OAUTH_TOKEN_ENCRYPTION_KEY: str = "dGhpcy1pcy1hLTMyLWJ5dGUtc2VjcmV0LWtleS1mb3ItZGV2IQ=="
    
    # Logging
    LOG_LEVEL: str = "INFO"

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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
