"""Confirmation service - the pause/resume state machine for tool calls.

A tool flagged requires_confirmation creates a pending ConfirmationRequest
instead of executing. A later turn approves or rejects it. Approval is
exactly-once: an atomic ``UPDATE ... WHERE status='pending'`` so a double-tap
(watch), a retried voice POST, or a replayed message can never execute twice.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.confirmation_request import ConfirmationRequest

DEFAULT_TTL_SECONDS = 120


class ConfirmationService:
    """Manages ConfirmationRequest lifecycle with exactly-once approval."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending(
        self,
        *,
        conversation_id: uuid.UUID,
        tool_use_id: str,
        tool_name: str,
        tool_args: dict,
        reference_id: str,
        summary: dict | None = None,
        message_id: uuid.UUID | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> ConfirmationRequest:
        """Create a pending confirmation for a suspended tool call."""
        request = ConfirmationRequest(
            conversation_id=conversation_id,
            message_id=message_id,
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_args=tool_args,
            reference_id=reference_id,
            summary=summary or {},
            status="pending",
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        )
        self.session.add(request)
        await self.session.flush()
        await self.session.refresh(request)
        return request

    async def get_pending(
        self, conversation_id: uuid.UUID
    ) -> ConfirmationRequest | None:
        """Return the latest still-pending request for a conversation.

        Lazily expires a request whose TTL has passed (returns None for it).
        """
        query = (
            select(ConfirmationRequest)
            .where(
                ConfirmationRequest.conversation_id == conversation_id,
                ConfirmationRequest.status == "pending",
            )
            .order_by(ConfirmationRequest.created_at.desc())
        )
        request = (await self.session.execute(query)).scalars().first()
        if request is None:
            return None

        if request.expires_at is not None and request.expires_at < datetime.utcnow():
            request.status = "expired"
            await self.session.flush()
            return None

        return request

    async def approve(self, confirmation_id: uuid.UUID) -> bool:
        """Atomically transition pending -> approved.

        Returns True only for the single caller that performed the transition;
        any subsequent (or expired) approval returns False. This is the
        exactly-once guard for irreversible actions.
        """
        now = datetime.utcnow()
        result = await self.session.execute(
            update(ConfirmationRequest)
            .where(
                ConfirmationRequest.id == confirmation_id,
                ConfirmationRequest.status == "pending",
                or_(
                    ConfirmationRequest.expires_at.is_(None),
                    ConfirmationRequest.expires_at > now,
                ),
            )
            .values(status="approved", updated_at=now)
        )
        await self.session.flush()
        return result.rowcount == 1

    async def reject(self, confirmation_id: uuid.UUID) -> bool:
        """Atomically transition pending -> rejected. Returns True if it did."""
        now = datetime.utcnow()
        result = await self.session.execute(
            update(ConfirmationRequest)
            .where(
                ConfirmationRequest.id == confirmation_id,
                ConfirmationRequest.status == "pending",
            )
            .values(status="rejected", updated_at=now)
        )
        await self.session.flush()
        return result.rowcount == 1
