"""LLM model configuration model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMModel(Base):
    """LLM model configuration table."""

    __tablename__ = "llm_models"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    model_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    display_name: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
