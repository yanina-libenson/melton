"""Tool database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tool(Base):
    """Tool model - represents an individual tool within an integration."""

    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tool_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    integration: Mapped["Integration"] = relationship("Integration", back_populates="tools")

    def __repr__(self) -> str:
        return f"<Tool(id={self.id}, name={self.name}, enabled={self.is_enabled})>"
