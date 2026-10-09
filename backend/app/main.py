from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging, logger
from app.api.v1.router import api_v1_router
from app.api.auth import router as auth_router

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("AI Gmail Assistant initialized successfully.")
    yield
    logger.info("Shutting down AI Gmail Assistant...")


app = FastAPI(
    title="AI Gmail Assistant — Human-in-the-Loop Email Automation",
    description="Safety-first email assistant with classification, draft generation, and deterministic approval policy enforcement.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router)
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
