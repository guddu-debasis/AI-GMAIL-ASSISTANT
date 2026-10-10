import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base
from app.models.user import User
from app.models.user_settings import UserSettings
from app.core.config import settings

# Test DB url using async sqlite
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def force_mock_llm(monkeypatch):
    # Tests must never call the real Groq API, even if a key is in .env
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    user = User(email="tester@example.com")
    test_db.add(user)
    await test_db.flush()

    user_settings = UserSettings(
        user_id=user.id,
        approval_categories=["job_recruitment", "financial", "legal_contractual"],
        approve_when_uncertain=True,
        approve_starred=True,
        allow_auto_send=False,
        min_confidence=0.80,
        policy_version=1,
    )
    test_db.add(user_settings)
    await test_db.commit()
    await test_db.refresh(user)
    return user
