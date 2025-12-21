"""Observability utilities with LangFuse integration."""

from typing import Any

from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe

from app.config import settings


class ObservabilityService:
    """Service for managing observability and tracing. Focused on LangFuse integration."""

    def __init__(self) -> None:
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            self.client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            self.enabled = True
        else:
            self.client = None
            self.enabled = False

    def trace_llm_call(
        self,
        model: str,
        provider: str,
        input_data: dict[str, Any],
        output_data: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Trace an LLM call.

        Args:
            model: Model identifier
            provider: Provider name (anthropic, openai, google)
            input_data: Input to LLM
            output_data: Output from LLM
            metadata: Additional metadata
        """
        if not self.enabled:
            return

        try:
            langfuse_context.update_current_trace(
                name=f"{provider}_{model}",
                metadata={
                    "provider": provider,
                    "model": model,
                    **(metadata or {}),
                },
            )

            langfuse_context.update_current_observation(
                input=input_data,
                output=output_data,
                metadata=metadata or {},
            )
        except Exception:
            # Don't fail execution if observability fails
            pass

    def trace_tool_execution(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        duration_ms: int,
        success: bool,
    ) -> None:
        """
        Trace a tool execution.

        Args:
            tool_name: Tool name
            input_data: Tool input
            output_data: Tool output
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
        """
        if not self.enabled:
            return

        try:
            langfuse_context.update_current_observation(
                name=f"tool_{tool_name}",
                input=input_data,
                output=output_data,
                metadata={
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "success": success,
                },
            )
        except Exception:
            pass

    def flush(self) -> None:
        """Flush pending traces to LangFuse."""
        if self.enabled and self.client:
            try:
                self.client.flush()
            except Exception:
                pass


# Global instance
observability_service = ObservabilityService()


# Decorator for automatic tracing
def trace_execution(name: str | None = None):
    """
    Decorator to automatically trace function execution.

    Usage:
        @trace_execution("agent_execution")
        async def execute_agent(...):
            ...
    """
    if observability_service.enabled:
        return observe(name=name)
    else:
        # Return no-op decorator if observability is disabled
        def decorator(func):
            return func

        return decorator
