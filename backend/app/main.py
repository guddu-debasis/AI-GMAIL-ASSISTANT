from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging, logger
from app.api.v1.router import api_v1_router
from app.api.auth import router as google_auth_router
from app.api.auth_session import router as auth_router

# Setup logging
setup_logging()


def _ensure_clerk_user_id_column(sync_conn) -> None:
    """
    create_all() creates missing tables but never adds columns to existing ones.
    Databases created before Clerk was added need users.clerk_user_id added once.
    """
    inspector = inspect(sync_conn)
    if "users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "clerk_user_id" not in columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN clerk_user_id VARCHAR(255)"))
        sync_conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_clerk_user_id ON users (clerk_user_id)"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_clerk_user_id_column)
    if not settings.CLERK_PUBLISHABLE_KEY and not settings.CLERK_ISSUER and not settings.CLERK_JWKS_URL:
        logger.warning("Clerk is not configured. Set CLERK_PUBLISHABLE_KEY or every API call will fail with 503.")
    if settings.APP_SECRET_KEY.startswith("dev_"):
        logger.warning("APP_SECRET_KEY is a development value. Set a long random secret before deploying.")
    logger.info("AI Gmail Assistant initialized successfully.")
    yield
    logger.info("Shutting down AI Gmail Assistant...")


app = FastAPI(
    title="AI Gmail Assistant: Human-in-the-Loop Email Automation",
    description="Safety-first email assistant with classification, draft generation, and deterministic approval policy enforcement.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: only the configured frontend origins. Auth uses a Bearer header,
# not cookies, so credentials are not needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include API routers
app.include_router(auth_router)
app.include_router(google_auth_router)
app.include_router(api_v1_router)


@app.get("/")
async def root():
    return {
        "service": "AI Gmail Assistant",
        "status": "operational",
        "docs": "/docs",
        "auto_send_policy": "DISABLED (Human approval strictly required by default)",
    }


@app.get("/healthz")
async def health():
    return {"status": "ok"}
