"""Deployment database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Deployment(Base):
    """Deployment model - represents a channel deployment configuration."""

    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="deployments")

    def __repr__(self) -> str:
        return f"<Deployment(id={self.id}, channel={self.channel_type}, active={self.is_active})>"
