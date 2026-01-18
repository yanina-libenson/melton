"""Conversation database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    """Conversation model - represents a chat session."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    conversation_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_message_preview: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="conversations")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, agent_id={self.agent_id}, channel={self.channel_type})>"
