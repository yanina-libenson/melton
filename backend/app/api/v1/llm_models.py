"""LLM Models API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.dependencies import get_current_user
from app.schemas.llm_model import LLMModelResponse
from app.services.llm_model_service import LLMModelService

router = APIRouter()


@router.get("", response_model=list[LLMModelResponse])
async def list_llm_models(
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """Get all active LLM models."""
    service = LLMModelService(session)
    models = await service.get_all_models()
    return models
