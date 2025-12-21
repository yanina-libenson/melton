"""User API key model - stores encrypted user-provided LLM provider API keys."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserApiKey(Base):
    """User API keys for LLM providers (Anthropic, OpenAI, Google)."""

    __tablename__ = "user_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Provider: 'anthropic', 'openai', 'google'
    provider: Mapped[str] = mapped_column(String(50), nullable=False)

    # Encrypted API key (we'll use simple encryption for now, can upgrade to Fernet later)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserApiKey(id={self.id}, user_id={self.user_id}, provider={self.provider})>"
