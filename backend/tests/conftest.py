"""Pytest configuration and fixtures."""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base

# Import the models package so ALL mappers are registered before create_all.
# (A string relationship like Agent -> "AgentPermission" only resolves if the
# target class has been imported.)
import app.models  # noqa: F401
from app.models.agent import Agent


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    # Use in-memory SQLite for testing. StaticPool keeps a SINGLE shared
    # connection so the in-memory DB (and its tables) persist across the
    # create_all connection and the session connection. With NullPool each
    # connection would get its own empty :memory: DB -> "no such table".
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def sample_agent(test_session: AsyncSession) -> Agent:
    """Create a sample agent for testing."""
    agent = Agent(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Test Agent",
        instructions="You are a helpful test agent",
        status="draft",
        model_config={
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
    )

    test_session.add(agent)
    await test_session.commit()
    await test_session.refresh(agent)

    return agent
