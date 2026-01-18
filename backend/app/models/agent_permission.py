"""Agent permission model for sharing and collaboration."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgentPermission(Base):
    """
    Agent permission for sharing and collaboration.

    Permission types:
    - "use": Can chat with the agent, see own conversations
    - "admin": Full access - can edit, delete, manage permissions
    """

    __tablename__ = "agent_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    permission_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'use' or 'admin'
    granted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="permissions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="agent_permissions")
    granter: Mapped["User"] = relationship("User", foreign_keys=[granted_by])

    # Ensure one permission per user per agent
    __table_args__ = (
        UniqueConstraint("agent_id", "user_id", name="uq_agent_permissions_agent_user"),
    )

    def __repr__(self) -> str:
        return f"<AgentPermission agent_id={self.agent_id} user_id={self.user_id} type={self.permission_type}>"
