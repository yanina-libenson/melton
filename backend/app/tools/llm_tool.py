"""LLM-only tool implementation."""

from typing import Any

from app.llm.factory import LLMProviderFactory
from app.tools.base_tool import BaseTool


class LLMTool(BaseTool):
    """
    Tool that uses LLM for execution without external API calls.
    Used for reasoning, summarization, or generation tasks.
    Stateless - no conversation history.
    """

    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        tool_schema: dict[str, Any],
        config: dict[str, Any],
        api_key: str | None = None,
    ):
        super().__init__(tool_id, config)
        self.name = name
        self.description = description
        self.tool_schema_data = tool_schema
        # Use default model if not specified or empty string
        self.llm_model = config.get("llm_model") or "claude-sonnet-4-5-20250929"
        self.llm_instructions = config.get("llm_instructions") or description
        self.api_key = api_key

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute LLM tool with stateless LLM call.

        Args:
            input_data: Tool input parameters

        Returns:
            Tool execution result with LLM response
        """
        try:
            # Determine provider from model
            provider_type = self._get_provider_from_model(self.llm_model)

            if not self.api_key:
                return {
                    "success": False,
                    "error": f"No API key configured for {provider_type}",
                }

            # Create LLM provider
            provider = LLMProviderFactory.create_provider(provider_type, self.api_key)

            # Build prompt from instructions and input
            prompt = self._build_prompt(input_data)

            # Make stateless LLM call (no history)
            response_text = ""
            async for event in provider.stream_with_tools(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                tools=[],  # No tools - pure LLM response
                system=self.llm_instructions,
                temperature=0.7,
                max_tokens=2048,
            ):
                if event.type == "content_delta":
                    response_text += event.delta

            # Clean up provider
            if hasattr(provider, 'close'):
                await provider.close()

            return {
                "success": True,
                "result": response_text,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _get_provider_from_model(self, model: str) -> str:
        """Determine provider from model name."""
        if "claude" in model.lower():
            return "anthropic"
        elif "gpt" in model.lower() or "o1" in model.lower():
            return "openai"
        elif "gemini" in model.lower():
            return "google"
        else:
            return "anthropic"  # Default

    def _build_prompt(self, input_data: dict[str, Any]) -> str:
        """Build prompt from input data."""
        if not input_data:
            # No input - just execute the tool's purpose
            return "Execute the task."

        # Format input data into prompt
        prompt_parts = ["Execute the task with the following inputs:"]
        for key, value in input_data.items():
            prompt_parts.append(f"- {key}: {value}")

        return "\n".join(prompt_parts)

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LLM."""
        return self.tool_schema_data
