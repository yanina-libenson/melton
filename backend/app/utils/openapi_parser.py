"""OpenAPI specification parser for auto-discovering tools."""

from typing import Any

import httpx
import yaml


class OpenAPIParser:
    """Parser for OpenAPI specifications. Keeps methods focused and small."""

    async def parse_from_url(self, openapi_url: str) -> dict[str, Any]:
        """
        Fetch and parse OpenAPI spec from URL.

        Args:
            openapi_url: URL to OpenAPI specification (JSON or YAML)

        Returns:
            Parsed OpenAPI specification

        Raises:
            ValueError: If fetching or parsing fails
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(openapi_url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                if "json" in content_type:
                    return response.json()
                elif "yaml" in content_type or "yml" in openapi_url.lower():
                    return yaml.safe_load(response.text)
                else:
                    # Try JSON first, then YAML
                    try:
                        return response.json()
                    except Exception:
                        return yaml.safe_load(response.text)

            except Exception as e:
                raise ValueError(f"Failed to fetch OpenAPI spec: {str(e)}")

    def extract_tools(self, openapi_spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract tools from OpenAPI specification.

        Args:
            openapi_spec: Parsed OpenAPI specification

        Returns:
            List of tool definitions
        """
        tools = []
        paths = openapi_spec.get("paths", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    tool = self._create_tool_from_operation(path, method.upper(), operation)
                    if tool:
                        tools.append(tool)

        return tools

    def _create_tool_from_operation(
        self, path: str, method: str, operation: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create tool definition from OpenAPI operation."""
        operation_id = operation.get("operationId")
        if not operation_id:
            # Generate operation ID from path and method
            operation_id = f"{method.lower()}_{path.replace('/', '_').strip('_')}"

        summary = operation.get("summary", "")
        description = operation.get("description", summary)

        # Extract parameters
        parameters = operation.get("parameters", [])
        input_schema = self._build_input_schema(parameters)

        return {
            "name": operation_id,
            "description": description or f"{method} {path}",
            "endpoint": path,
            "method": method,
            "input_schema": input_schema,
        }

    def _build_input_schema(self, parameters: list[dict[str, Any]]) -> dict[str, Any]:
        """Build JSON schema from OpenAPI parameters."""
        properties = {}
        required = []

        for param in parameters:
            param_name = param.get("name")
            param_schema = param.get("schema", {})
            param_required = param.get("required", False)

            if param_name:
                properties[param_name] = {
                    "type": param_schema.get("type", "string"),
                    "description": param.get("description", ""),
                }

                if param_required:
                    required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def extract_auth_requirements(self, openapi_spec: dict[str, Any]) -> dict[str, Any]:
        """
        Extract authentication requirements from OpenAPI spec.

        Args:
            openapi_spec: Parsed OpenAPI specification

        Returns:
            Authentication configuration
        """
        security_schemes = (
            openapi_spec.get("components", {}).get("securitySchemes", {})
            or openapi_spec.get("securityDefinitions", {})
        )

        if not security_schemes:
            return {"type": "none"}

        # Take the first security scheme
        scheme_name, scheme = next(iter(security_schemes.items()))
        scheme_type = scheme.get("type", "").lower()

        if scheme_type == "apikey":
            return {
                "type": "api-key",
                "header": scheme.get("name", "X-API-Key"),
                "in": scheme.get("in", "header"),
            }
        elif scheme_type == "http":
            http_scheme = scheme.get("scheme", "").lower()
            if http_scheme == "bearer":
                return {"type": "bearer"}
            elif http_scheme == "basic":
                return {"type": "basic"}
        elif scheme_type == "oauth2":
            return {
                "type": "oauth",
                "flows": scheme.get("flows", {}),
            }

        return {"type": "none"}


# Global instance
openapi_parser = OpenAPIParser()
