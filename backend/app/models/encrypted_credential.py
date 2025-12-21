"""Encrypted Credential database model."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EncryptedCredential(Base):
    """EncryptedCredential model - stores encrypted API credentials."""

    __tablename__ = "encrypted_credentials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credential_type: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)

    # OAuth-specific fields
    token_expiry: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_token_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    integration: Mapped["Integration"] = relationship("Integration", back_populates="credentials")

    def __repr__(self) -> str:
        return f"<EncryptedCredential(id={self.id}, type={self.credential_type})>"
