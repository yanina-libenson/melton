"""Tests for the per-user persistent memory store: MemoryService + memory tools.

Covers CRUD, fuzzy/normalized matching, upsert, and — critically — that the
store is isolated per (operator, agent): one user/agent never reads another's.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as app_database
import app.models  # noqa: F401 — register all mappers before create_all
from app.database import Base
from app.services.memory_service import MemoryService
from app.tools.memory_tools import build_memory_tools

USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
ORG = uuid.uuid4()
AGENT_1 = uuid.uuid4()
AGENT_2 = uuid.uuid4()


@pytest.fixture
async def mem_maker(monkeypatch):
    """In-memory sqlite session maker, also patched in as the global
    async_session_maker so MemoryTool.execute() (which opens its own session)
    hits this DB."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(app_database, "async_session_maker", maker)
    yield maker
    await engine.dispose()


# --- MemoryService -----------------------------------------------------------


@pytest.mark.asyncio
async def test_remember_and_recall(mem_maker):
    async with mem_maker() as session:
        svc = MemoryService(session)
        await svc.remember(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", label="yani mp", data={"alias": "yani.mp", "cuit": "27323575954"},
        )
        await session.commit()
        found = await svc.recall(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", query="yani",
        )
        assert len(found) == 1
        assert found[0].data["alias"] == "yani.mp"


@pytest.mark.asyncio
async def test_remember_upsert_normalized(mem_maker):
    """Re-saving the same label (different case/spacing) updates, not duplicates."""
    async with mem_maker() as session:
        svc = MemoryService(session)
        await svc.remember(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", label="Yani  MP", data={"alias": "old"},
        )
        await svc.remember(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", label="yani mp", data={"alias": "new"},
        )
        await session.commit()
        rows = await svc.list_all(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1, collection="contactos",
        )
        assert len(rows) == 1
        assert rows[0].data["alias"] == "new"


@pytest.mark.asyncio
async def test_forget(mem_maker):
    async with mem_maker() as session:
        svc = MemoryService(session)
        await svc.remember(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", label="graciela", data={"alias": "graciela.h"},
        )
        await session.commit()
        removed = await svc.forget(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", label="GRACIELA",
        )
        await session.commit()
        assert removed is True
        rows = await svc.list_all(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1, collection="contactos",
        )
        assert rows == []


@pytest.mark.asyncio
async def test_scope_isolated_by_user(mem_maker):
    async with mem_maker() as session:
        svc = MemoryService(session)
        await svc.remember(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", label="yani mp", data={"alias": "yani.mp"},
        )
        await session.commit()
        # USER_B uses the same agent — must NOT see USER_A's data.
        other = await svc.recall(
            user_id=USER_B, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", query="yani",
        )
        assert other == []


@pytest.mark.asyncio
async def test_scope_isolated_by_agent(mem_maker):
    async with mem_maker() as session:
        svc = MemoryService(session)
        await svc.remember(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_1,
            collection="contactos", label="yani mp", data={"alias": "yani.mp"},
        )
        await session.commit()
        # Same user, different agent — separate store.
        other = await svc.recall(
            user_id=USER_A, organization_id=ORG, agent_id=AGENT_2,
            collection="contactos", query="yani",
        )
        assert other == []


# --- Memory tools (end-to-end via their own session) -------------------------


def _tools(user_id=USER_A, agent_id=AGENT_1):
    tools = {t.name: t for t in build_memory_tools(user_id, ORG, agent_id)}
    return tools


@pytest.mark.asyncio
async def test_remember_tool_then_recall_tool(mem_maker):
    tools = _tools()
    saved = await tools["remember"].execute(
        {"collection": "contactos", "label": "yani mp", "data": {"alias": "yani.mp", "cuit": "27323575954"}}
    )
    assert saved["success"] is True
    assert saved["record"]["data"]["alias"] == "yani.mp"

    recalled = await tools["recall"].execute({"collection": "contactos", "query": "yani"})
    assert recalled["success"] is True
    assert recalled["count"] == 1
    assert recalled["results"][0]["data"]["cuit"] == "27323575954"


@pytest.mark.asyncio
async def test_recall_tool_no_match(mem_maker):
    tools = _tools()
    res = await tools["recall"].execute({"collection": "contactos", "query": "nadie"})
    assert res["success"] is True
    assert res["count"] == 0


@pytest.mark.asyncio
async def test_remember_tool_requires_label(mem_maker):
    tools = _tools()
    res = await tools["remember"].execute({"collection": "contactos", "label": "", "data": {}})
    assert res["success"] is False
    assert "label" in res["error"].lower()


@pytest.mark.asyncio
async def test_forget_tool(mem_maker):
    tools = _tools()
    await tools["remember"].execute(
        {"collection": "contactos", "label": "graciela", "data": {"alias": "g"}}
    )
    gone = await tools["forget"].execute({"collection": "contactos", "label": "graciela"})
    assert gone["success"] is True
    listed = await tools["list_memory"].execute({"collection": "contactos"})
    assert listed["count"] == 0


@pytest.mark.asyncio
async def test_tool_scope_isolated_by_user(mem_maker):
    """The remember tool for USER_A must not be visible to USER_B's recall tool."""
    await _tools(user_id=USER_A)["remember"].execute(
        {"collection": "contactos", "label": "yani mp", "data": {"alias": "yani.mp"}}
    )
    res = await _tools(user_id=USER_B)["recall"].execute({"collection": "contactos", "query": "yani"})
    assert res["count"] == 0
