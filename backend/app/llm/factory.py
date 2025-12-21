"""LLM provider factory for creating provider instances."""

from typing import Literal

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base_provider import BaseLLMProvider
from app.llm.google_provider import GoogleProvider
from app.llm.openai_provider import OpenAIProvider


class LLMProviderFactory:
    """Factory for creating LLM provider instances. Single responsibility."""

    @staticmethod
    def create_provider(
        provider_type: Literal["anthropic", "openai", "google"],
        api_key: str,
    ) -> BaseLLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_type: Provider type ('anthropic', 'openai', 'google')
            api_key: API key for the provider

        Returns:
            Provider instance

        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type == "anthropic":
            return AnthropicProvider(api_key)
        elif provider_type == "openai":
            return OpenAIProvider(api_key)
        elif provider_type == "google":
            return GoogleProvider(api_key)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
