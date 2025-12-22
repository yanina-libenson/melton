"""LLM-only tool implementation."""

import logging
from typing import Any

from app.llm.factory import LLMProviderFactory
from app.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


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
        # Get temperature from creativity level (defaults to medium)
        self.temperature = self._get_temperature_from_creativity(
            config.get("creativity_level", "medium")
        )

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
            logger.info(f"Executing LLM tool '{self.name}' with provider: {provider_type}, model: {self.llm_model}")

            if not self.api_key:
                logger.error(f"No API key configured for {provider_type}")
                return {
                    "success": False,
                    "error": f"No API key configured for {provider_type}",
                }

            # Create LLM provider
            provider = LLMProviderFactory.create_provider(provider_type, self.api_key)

            # Build prompt from instructions and input
            prompt = self._build_prompt(input_data)

            # Check if tool has an output schema for structured output
            output_schema = self.tool_schema_data.get("output_schema")
            logger.info(f"Tool has output schema: {output_schema is not None}")

            if output_schema:
                logger.info(f"Using structured output with schema: {output_schema}")
                logger.info(f"Temperature: {self.temperature}, Max tokens: 2048")
                # Use structured output with configured creativity level
                structured_result = await provider.generate_structured_output(
                    model=self.llm_model,
                    prompt=prompt,
                    output_schema=output_schema,
                    system=self.llm_instructions,
                    temperature=self.temperature,
                    max_tokens=2048,
                )

                logger.info(f"Structured output generated successfully: {structured_result}")

                # Clean up provider
                if hasattr(provider, 'close'):
                    await provider.close()

                return {
                    "success": True,
                    **structured_result,  # Spread structured fields directly
                }
            else:
                logger.info("Using freeform text generation")
                # Use freeform text generation
                response_text = ""
                async for event in provider.stream_with_tools(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    tools=[],  # No tools - pure LLM response
                    system=self.llm_instructions,
                    temperature=self.temperature,
                    max_tokens=2048,
                ):
                    if event.type == "content_delta":
                        response_text += event.delta

                logger.info(f"Freeform text generated successfully, length: {len(response_text)}")

                # Clean up provider
                if hasattr(provider, 'close'):
                    await provider.close()

                return {
                    "success": True,
                    "result": response_text,
                }

        except Exception as e:
            logger.error(f"LLM tool execution failed: {str(e)}", exc_info=True)
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

    def _get_temperature_from_creativity(self, creativity_level: str) -> float:
        """Map creativity level to temperature value."""
        creativity_map = {
            "low": 0.3,
            "medium": 0.7,
            "high": 1.0,
        }
        return creativity_map.get(creativity_level.lower(), 1.0)

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
