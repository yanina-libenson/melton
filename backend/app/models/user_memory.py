"""User persistent memory model.

A per-user, per-agent store the agent can read and write across conversations.
NOT payment-specific: it holds labeled JSON records grouped into named
collections (e.g. "contactos" for payees, but also preferences, notes, etc.).
Scoped to the OPERATOR (the logged-in user running the agent), so it survives
the conversation and belongs to the person, not the chat.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserMemory(Base):
    """A labeled JSON record in a user's persistent store, scoped to an agent.

    Unique on (user_id, agent_id, collection, label): saving the same label in
    the same collection updates the existing record (upsert).
    """

    __tablename__ = "user_memory"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # The OPERATOR — the user running the agent (not necessarily the agent owner).
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    # The agent this memory belongs to. Nullable reserves a future "global per
    # user" scope (agent_id NULL); v1 always sets it.
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Groups related records, e.g. "contactos", "preferencias", "notas".
    collection: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Human-readable key used for fuzzy lookup, e.g. "yani mp".
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    # Free-form payload, e.g. {"alias": "yani.mp", "cuit": "27..."}.
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "agent_id", "collection", "label",
            name="uq_user_memory_scope_label",
        ),
    )

    def __repr__(self) -> str:
        return f"<UserMemory(user_id={self.user_id}, collection={self.collection}, label={self.label!r})>"
