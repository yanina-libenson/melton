"""Agent database model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Agent(Base):
    """Agent model - represents an AI agent configuration."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    model_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Public agent fields
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    access_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="private")
    public_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    public_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Sharing fields
    is_shareable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_code: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="agents")
    integrations: Mapped[list["Integration"]] = relationship(
        "Integration", back_populates="agent", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="agent", cascade="all, delete-orphan"
    )
    deployments: Mapped[list["Deployment"]] = relationship(
        "Deployment", back_populates="agent", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["AgentPermission"]] = relationship(
        "AgentPermission", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"
