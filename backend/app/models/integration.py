"""Integration database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Integration(Base):
    """Integration model - represents a platform or custom tool integration."""

    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    platform_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="integrations")
    tools: Mapped[list["Tool"]] = relationship(
        "Tool", back_populates="integration", cascade="all, delete-orphan"
    )
    credentials: Mapped[list["EncryptedCredential"]] = relationship(
        "EncryptedCredential", back_populates="integration", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, name={self.name}, type={self.type})>"
