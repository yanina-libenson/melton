"""LLM model service for querying model configurations."""

from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_model import LLMModel


class LLMModelService:
    """Service for managing LLM model configurations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_provider_for_model(self, model_id: str) -> str:
        """
        Get provider for a given model ID.

        Args:
            model_id: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-5-20250929")

        Returns:
            Provider name ("anthropic", "openai", "google")

        Raises:
            ValueError: If model not found
        """
        # Query database
        query = select(LLMModel).where(
            LLMModel.model_id == model_id,
            LLMModel.is_active == True  # noqa: E712
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            # Fallback to heuristic for unknown models
            return self._fallback_provider_detection(model_id)

        return model.provider

    async def get_all_models(self) -> list[LLMModel]:
        """Get all active LLM models."""
        query = select(LLMModel).where(LLMModel.is_active == True).order_by(LLMModel.provider, LLMModel.display_name)  # noqa: E712
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_models_by_provider(self, provider: str) -> list[LLMModel]:
        """Get all active models for a specific provider."""
        query = select(LLMModel).where(
            LLMModel.provider == provider,
            LLMModel.is_active == True  # noqa: E712
        ).order_by(LLMModel.display_name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    @lru_cache(maxsize=128)
    def _fallback_provider_detection(model_id: str) -> str:
        """
        Fallback heuristic for unknown models.
        Uses string matching as backup.
        """
        model_lower = model_id.lower()
        if "claude" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "o1" in model_lower:
            return "openai"
        elif "gemini" in model_lower:
            return "google"
        else:
            # Default to anthropic
            return "anthropic"
