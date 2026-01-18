"""User database model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """User model - represents an agent creator/owner."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    subdomain: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    agents: Mapped[list["Agent"]] = relationship(
        "Agent", back_populates="user", cascade="all, delete-orphan"
    )
    agent_permissions: Mapped[list["AgentPermission"]] = relationship(
        "AgentPermission",
        foreign_keys="AgentPermission.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", foreign_keys="Conversation.user_id"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, subdomain={self.subdomain})>"
