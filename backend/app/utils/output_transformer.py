"""Output transformation utilities for API tools."""

import logging
from typing import Any

from jsonpath_ng import parse as jsonpath_parse

logger = logging.getLogger(__name__)


class OutputTransformer:
    """Handles transformation of API responses to tool outputs."""

    @staticmethod
    def transform(
        api_response: dict | list,
        output_mode: str,
        output_mapping: dict[str, str] | None = None,
    ) -> dict | list | Any:
        """
        Transform API response based on output mode.

        Args:
            api_response: Raw API response
            output_mode: "full", "extract", or "llm"
            output_mapping: Field mapping for extract mode (e.g., {"temp": "current_condition[0].temp_C"})

        Returns:
            Transformed output based on mode
        """
        if output_mode == "full":
            return api_response

        elif output_mode == "extract":
            return OutputTransformer._extract_fields(api_response, output_mapping or {})

        elif output_mode == "llm":
            # LLM transformation is handled separately in APITool
            return api_response

        else:
            logger.warning(f"Unknown output_mode: {output_mode}, returning full response")
            return api_response

    @staticmethod
    def _extract_fields(data: dict | list, mapping: dict[str, str]) -> dict:
        """
        Extract specific fields from API response using JSONPath.

        Args:
            data: API response data
            mapping: Dict mapping output field names to JSONPath expressions
                    Example: {"temperature": "current_condition[0].temp_C"}

        Returns:
            Dict with extracted fields
        """
        result = {}

        for output_field, jsonpath_expr in mapping.items():
            try:
                # Parse JSONPath expression
                jsonpath = jsonpath_parse(jsonpath_expr)

                # Find matches
                matches = jsonpath.find(data)

                if matches:
                    # If single match, return the value directly
                    if len(matches) == 1:
                        result[output_field] = matches[0].value
                    else:
                        # Multiple matches, return as array
                        result[output_field] = [match.value for match in matches]
                else:
                    # No match found
                    result[output_field] = None
                    logger.warning(
                        f"JSONPath '{jsonpath_expr}' returned no matches for field '{output_field}'"
                    )

            except Exception as e:
                logger.error(f"Error extracting field '{output_field}': {e}")
                result[output_field] = None

        return result
