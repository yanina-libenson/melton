"""Message database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    """Message model - represents a single message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    message_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    traces: Mapped[list["ExecutionTrace"]] = relationship(
        "ExecutionTrace", back_populates="message", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"
