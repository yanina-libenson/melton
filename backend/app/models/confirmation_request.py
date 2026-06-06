"""ConfirmationRequest model - a paused, awaiting-confirmation tool call.

When the execution loop hits a tool flagged requires_confirmation, it does NOT
execute the tool. Instead it persists this row (the suspended frame) so the
conversation can be resumed from a later, socket-less request (e.g. a voice
POST) on any worker. The reference_id is the idempotency key handed to the
tool on execution, so a retry never double-acts.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConfirmationRequest(Base):
    """A pending/approved/rejected/expired confirmation for one tool call."""

    __tablename__ = "confirmation_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The assistant message holding the tool_use block (for resume). Nullable so
    # an in-flight request isn't lost if the message row isn't persisted yet.
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )

    # Enough to faithfully rebuild the tool_use / tool_result pair on resume.
    tool_use_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_args: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # pending -> approved | rejected | expired
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    # Idempotency key passed to the tool on execution; unique across all requests.
    reference_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Human-facing summary for the confirmation card (amount, destination, ...).
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ConfirmationRequest(id={self.id}, tool={self.tool_name}, "
            f"status={self.status})>"
        )
