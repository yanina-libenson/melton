"""Base LLM provider abstract class."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class StreamEvent:
    """Streaming event from LLM."""

    def __init__(
        self,
        event_type: str,
        delta: str | None = None,
        tool_name: str | None = None,
        tool_input: dict[str, Any] | None = None,
        tool_use_id: str | None = None,
    ):
        self.type = event_type
        self.delta = delta
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_use_id = tool_use_id


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers. Keep implementations focused."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def stream_with_tools(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        """
        Stream LLM response with tool calling support.

        Args:
            model: Model identifier
            messages: Conversation history
            tools: Available tools in provider format
            system: System instructions
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate

        Yields:
            StreamEvent objects for content deltas and tool calls
        """
        pass

    @abstractmethod
    async def generate_without_tools(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate text without tool calling (for stateless tool LLMs).

        Args:
            model: Model identifier
            prompt: Input prompt
            system: System instructions
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def convert_tool_schema(self, tool_schema: dict[str, Any]) -> dict[str, Any]:
        """
        Convert our tool schema format to provider-specific format.

        Args:
            tool_schema: Our standard tool schema

        Returns:
            Provider-specific tool schema
        """
        pass
