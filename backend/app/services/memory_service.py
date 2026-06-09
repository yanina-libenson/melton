"""Service for the user's persistent memory store (UserMemory).

All operations are scoped to (user_id, organization_id, agent_id, collection).
Matching on label is case- and whitespace-insensitive (mirrors the original
contactos.py `_norm`), so "Yani MP" and "yani  mp" resolve to the same record.
Collections are small per user/agent, so we filter/rank in Python rather than
pushing fuzzy matching into SQL.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_memory import UserMemory


def _norm(text: str) -> str:
    """Lowercase and collapse whitespace for lenient label matching."""
    return " ".join((text or "").lower().split())


class MemoryService:
    """CRUD for a user's persistent, per-agent labeled records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _collection_rows(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        collection: str,
    ) -> list[UserMemory]:
        query = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.organization_id == organization_id,
            UserMemory.agent_id == agent_id,
            UserMemory.collection == collection,
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def remember(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        collection: str,
        label: str,
        data: dict,
    ) -> UserMemory:
        """Insert or update a record (upsert by normalized label)."""
        rows = await self._collection_rows(user_id, organization_id, agent_id, collection)
        target_norm = _norm(label)
        for row in rows:
            if _norm(row.label) == target_norm:
                row.data = data
                await self.session.flush()
                await self.session.refresh(row)
                return row

        record = UserMemory(
            user_id=user_id,
            organization_id=organization_id,
            agent_id=agent_id,
            collection=collection,
            label=label,
            data=data,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def recall(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        collection: str,
        query: str,
    ) -> list[UserMemory]:
        """Fuzzy lookup by label. Exact (normalized) matches first, then
        substring matches. Empty query returns the whole collection."""
        rows = await self._collection_rows(user_id, organization_id, agent_id, collection)
        q = _norm(query)
        if not q:
            return rows
        exact = [r for r in rows if _norm(r.label) == q]
        partial = [r for r in rows if q in _norm(r.label) and r not in exact]
        return exact + partial

    async def list_all(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        collection: str,
    ) -> list[UserMemory]:
        """Return every record in a collection."""
        return await self._collection_rows(user_id, organization_id, agent_id, collection)

    async def forget(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        collection: str,
        label: str,
    ) -> bool:
        """Delete a record by normalized label. Returns True if one was removed."""
        rows = await self._collection_rows(user_id, organization_id, agent_id, collection)
        target_norm = _norm(label)
        for row in rows:
            if _norm(row.label) == target_norm:
                await self.session.delete(row)
                await self.session.flush()
                return True
        return False
