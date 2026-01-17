"""Custom API tool implementation with full authentication support."""

from datetime import datetime, timedelta
from typing import Any

import httpx

from app.llm.factory import LLMProviderFactory
from app.tools.base_tool import BaseTool
from app.utils.encryption import encryption_service
from app.utils.output_transformer import OutputTransformer


class APITool(BaseTool):
    """
    Custom API tool with comprehensive authentication support.
    Supports: API Key, Bearer, Basic, OAuth 2.0, Custom Headers.
    """

    def __init__(self, tool_id: str, config: dict[str, Any]):
        super().__init__(tool_id, config)

        self.endpoint = config.get("endpoint", "")
        self.method = config.get("method", "GET")
        self.auth_type = config.get("authentication", "none")
        self.timeout = config.get("timeout", 30)

        # Output transformation settings
        self.output_mode = config.get("output_mode", "full")  # "full", "extract", "llm"
        self.output_mapping = config.get("output_mapping", {})

        # LLM enhancement settings
        self.llm_enhanced = config.get("llm_enhanced", False)
        self.llm_provider = config.get("llm_provider")
        self.llm_model = config.get("llm_model")
        self.llm_api_key = config.get("llm_api_key")
        self.llm_pre_instructions = config.get("llm_pre_instructions")
        self.llm_post_instructions = config.get("llm_post_instructions")

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the API tool with authentication and optional output transformation."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"APITool.execute called: name={self.name}, input={input_data}, endpoint={self.endpoint}")

        try:
            # Validate required parameters from tool schema
            validation_error = self._validate_required_params(input_data)
            if validation_error:
                logger.error(f"APITool validation failed: {validation_error}")
                return {"success": False, "error": validation_error}

            # Make API call with auth
            api_response = await self._make_api_call(input_data)

            # Log the raw API response for debugging
            logger.error(f"[DEBUG] Raw API response for {self.name}: {api_response}")

            # If response is plain text (not JSON), return it as-is without transformation
            if isinstance(api_response, str):
                result = api_response
            # Apply output transformation only for dict/list responses
            elif self.output_mode == "full":
                result = api_response
            elif self.output_mode == "extract":
                result = OutputTransformer.transform(
                    api_response,
                    output_mode="extract",
                    output_mapping=self.output_mapping
                )
            elif self.output_mode == "llm":
                # LLM transformation for complex cases
                if self.llm_post_instructions:
                    result = await self._postprocess_with_llm(api_response)
                else:
                    result = api_response
            else:
                # Default to full response
                result = api_response

            logger.info(f"APITool.execute succeeded: output={result}")
            return {"success": True, "data": result}

        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            logger.error(f"APITool.execute failed: {error_msg}", exc_info=True)
            return {"success": False, "error": error_msg}

    async def _make_api_call(self, input_data: dict[str, Any]) -> Any:
        """Make HTTP request with authentication."""
        import logging
        from urllib.parse import urlencode
        logger = logging.getLogger(__name__)

        headers = await self._build_headers()
        url, remaining_params = self._build_url(input_data)

        logger.error(f"[DEBUG] remaining_params before urlencode: {remaining_params}")

        # For GET requests with query params, build URL manually to avoid over-encoding
        if self.method == "GET" and remaining_params:
            # Use safe parameter to preserve special characters like |, :, etc.
            query_string = urlencode(remaining_params, safe=':,|')
            logger.error(f"[DEBUG] query_string after urlencode: {query_string}")
            url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"
            remaining_params = None

        logger.error(f"[DEBUG] Final URL: {url}")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            # Retry logic for OAuth token refresh
            for attempt in range(2):
                try:
                    # Make HTTP request based on method
                    if self.method == "GET":
                        response = await client.get(url, headers=headers)
                    elif self.method == "POST":
                        response = await client.post(url, headers=headers, json=input_data)
                    elif self.method == "PUT":
                        response = await client.put(url, headers=headers, json=input_data)
                    elif self.method == "DELETE":
                        response = await client.delete(url, headers=headers)
                    elif self.method == "PATCH":
                        response = await client.patch(url, headers=headers, json=input_data)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {self.method}")

                    # Check for 401 and refresh OAuth token if needed
                    if response.status_code == 401 and self.auth_type == "oauth" and attempt == 0:
                        await self._refresh_oauth_token()
                        headers = await self._build_headers()
                        continue

                    response.raise_for_status()

                    # Check content type to handle different response types
                    content_type = response.headers.get("content-type", "").lower()

                    # If response is an image, return the URL instead of the image data
                    if content_type.startswith("image/"):
                        logger.info(f"Response is an image ({content_type}), returning URL instead of binary data")
                        return url

                    # Try to parse as JSON, otherwise return text
                    if response.content:
                        try:
                            return response.json()
                        except Exception:
                            # Not JSON - return as plain text
                            return response.text
                    return ""

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401 and attempt == 0:
                        continue
                    raise

    async def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers with authentication."""
        headers = {}

        # Only set Content-Type for requests with body
        if self.method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/json"

        if self.auth_type == "api-key":
            key_header = self.config.get("api_key_header", "X-API-Key")
            encrypted_key = self.config.get("api_key_value")
            if encrypted_key:
                api_key = encryption_service.decrypt(encrypted_key)
                headers[key_header] = api_key

        elif self.auth_type == "bearer":
            encrypted_token = self.config.get("bearer_token")
            if encrypted_token:
                token = encryption_service.decrypt(encrypted_token)
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == "basic":
            username = self.config.get("username", "")
            encrypted_password = self.config.get("password", "")
            if encrypted_password:
                import base64

                password = encryption_service.decrypt(encrypted_password)
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

        elif self.auth_type == "oauth":
            encrypted_token = self.config.get("access_token")
            if encrypted_token:
                token = encryption_service.decrypt(encrypted_token)
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == "custom":
            custom_headers = self.config.get("custom_headers", {})
            for key, encrypted_value in custom_headers.items():
                value = encryption_service.decrypt(encrypted_value)
                headers[key] = value

        return headers

    async def _refresh_oauth_token(self) -> None:
        """Refresh OAuth access token using refresh token."""
        refresh_token_encrypted = self.config.get("refresh_token")
        token_url = self.config.get("oauth_token_url")

        if not refresh_token_encrypted or not token_url:
            raise ValueError("OAuth refresh token or token URL not configured")

        refresh_token = encryption_service.decrypt(refresh_token_encrypted)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.config.get("oauth_client_id"),
                    "client_secret": self.config.get("oauth_client_secret"),
                },
            )
            response.raise_for_status()

            token_data = response.json()
            new_access_token = token_data.get("access_token")
            expiry_seconds = token_data.get("expires_in", 3600)

            # Update config with new token (in production, save to database)
            self.config["access_token"] = encryption_service.encrypt(new_access_token)
            self.config["token_expiry"] = datetime.utcnow() + timedelta(seconds=expiry_seconds)

    def _build_url(self, input_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        Build URL with path parameters and return remaining params for query string.

        Returns:
            Tuple of (url, remaining_params) where remaining_params are inputs
            that weren't used in URL templating
        """
        from urllib.parse import quote

        url = self.endpoint
        used_keys = set()

        # Replace template variables with URL-encoded values
        for key, value in input_data.items():
            template = f"{{{key}}}"
            if template in url:
                # URL-encode the value but preserve special chars like |, :, ,
                encoded_value = quote(str(value), safe=':,|')
                url = url.replace(template, encoded_value)
                used_keys.add(key)

        # Return remaining params that weren't used in URL template
        remaining_params = {k: v for k, v in input_data.items() if k not in used_keys}
        return url, remaining_params

    def _validate_required_params(self, input_data: dict[str, Any]) -> str | None:
        """
        Validate that all required parameters are provided.
        Returns error message if validation fails, None if valid.
        """
        # Get required fields from tool config's input_schema
        input_schema = self.config.get("input_schema", {})
        required_fields = input_schema.get("required", [])
        properties = input_schema.get("properties", {})

        if not required_fields:
            return None  # No required fields

        missing_fields = []
        for field in required_fields:
            if field not in input_data or not input_data[field]:
                field_desc = properties.get(field, {}).get("description", field)
                missing_fields.append(f"{field} ({field_desc})")

        if missing_fields:
            return (
                f"Missing required parameters: {', '.join(missing_fields)}. "
                f"You must provide these parameters to call this tool. "
                f"Do not call the tool with empty input {{}}."
            )

        return None

    async def _preprocess_with_llm(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Use LLM to preprocess user input into API parameters (stateless)."""
        if not self.llm_provider or not self.llm_api_key:
            return input_data

        provider = LLMProviderFactory.create_provider(self.llm_provider, self.llm_api_key)

        prompt = f"User request: {input_data}\n\nConvert to API parameters."

        result = await provider.generate_without_tools(
            model=self.llm_model,
            prompt=prompt,
            system=self.llm_pre_instructions,
            temperature=0.3,
            max_tokens=1024,
        )

        # Parse LLM output as JSON
        import json

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return input_data

    async def _postprocess_with_llm(self, api_result: Any) -> dict[str, Any]:
        """Use LLM to postprocess API response (stateless)."""
        if not self.llm_provider or not self.llm_api_key:
            return api_result

        provider = LLMProviderFactory.create_provider(self.llm_provider, self.llm_api_key)

        prompt = f"API response: {api_result}\n\nSummarize or transform as needed."

        result = await provider.generate_without_tools(
            model=self.llm_model,
            prompt=prompt,
            system=self.llm_post_instructions,
            temperature=0.5,
            max_tokens=2048,
        )

        return {"summary": result, "raw": api_result}

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.config.get("input_schema", {"type": "object", "properties": {}}),
        }
