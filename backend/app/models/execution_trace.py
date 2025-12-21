"""Execution Trace database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExecutionTrace(Base):
    """ExecutionTrace model - stores execution traces for observability."""

    __tablename__ = "execution_traces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)
    step_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="traces")

    def __repr__(self) -> str:
        return f"<ExecutionTrace(id={self.id}, step={self.step_type}, duration={self.duration_ms}ms)>"
