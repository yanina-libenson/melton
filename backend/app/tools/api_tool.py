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

            # Apply output transformation based on mode
            if self.output_mode == "full":
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
        logger = logging.getLogger(__name__)

        headers = await self._build_headers()
        url, remaining_params = self._build_url(input_data)

        logger.error(f"API CALL - Endpoint template: {self.endpoint}")
        logger.error(f"API CALL - Input data: {input_data}")
        logger.error(f"API CALL - Final URL: {url}")
        logger.error(f"API CALL - Remaining params: {remaining_params}")
        logger.error(f"API CALL - Headers: {headers}")

        # Force HTTP/1.1 - some servers (like wttr.in) behave differently with HTTP/2
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            http1=True,
            http2=False
        ) as client:
            # Retry logic for OAuth token refresh
            for attempt in range(2):
                try:
                    # Manually build request to prevent httpx from adding unwanted headers
                    if self.method == "GET":
                        # Build URL with query params
                        request = client.build_request(
                            method="GET",
                            url=url,
                            headers=headers,
                            params=remaining_params
                        )
                    elif self.method == "POST":
                        request = client.build_request(
                            method="POST",
                            url=url,
                            headers=headers,
                            json=input_data
                        )
                    elif self.method == "PUT":
                        request = client.build_request(
                            method="PUT",
                            url=url,
                            headers=headers,
                            json=input_data
                        )
                    elif self.method == "DELETE":
                        request = client.build_request(
                            method="DELETE",
                            url=url,
                            headers=headers
                        )
                    elif self.method == "PATCH":
                        request = client.build_request(
                            method="PATCH",
                            url=url,
                            headers=headers,
                            json=input_data
                        )
                    else:
                        raise ValueError(f"Unsupported HTTP method: {self.method}")

                    # Remove auto-added headers that some APIs (like wttr.in) don't like
                    # These headers can trigger anti-bot measures
                    if 'accept-encoding' in request.headers:
                        del request.headers['accept-encoding']
                    if 'connection' in request.headers:
                        del request.headers['connection']

                    # Send the manually constructed request
                    response = await client.send(request)

                    # Check for 401 and refresh token if OAuth
                    if response.status_code == 401 and self.auth_type == "oauth" and attempt == 0:
                        await self._refresh_oauth_token()
                        headers = await self._build_headers()
                        continue

                    response.raise_for_status()

                    # Log response details for debugging
                    logger.error(f"API RESPONSE - Status: {response.status_code}")
                    logger.error(f"API RESPONSE - Content-Type: {response.headers.get('content-type')}")
                    logger.error(f"API RESPONSE - Response Headers: {dict(response.headers)}")
                    logger.error(f"API RESPONSE - Request Headers Sent: {dict(response.request.headers)}")

                    # Try to parse as JSON
                    if response.content:
                        try:
                            return response.json()
                        except Exception as json_err:
                            # Log the actual response content for debugging
                            content_preview = response.text[:500] if response.text else "(empty)"
                            logger.error(
                                f"Failed to parse API response as JSON. "
                                f"URL: {url}, Status: {response.status_code}, "
                                f"Content-Type: {response.headers.get('content-type')}, "
                                f"Content preview: {content_preview}"
                            )
                            raise ValueError(
                                f"API returned non-JSON response (status {response.status_code}): {content_preview}"
                            ) from json_err
                    return {}

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401 and attempt == 0:
                        continue
                    raise

    async def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers with authentication."""
        headers = {
            "Accept": "application/json",
        }

        # Only set Content-Type for requests with body (POST, PUT, PATCH)
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
        url = self.endpoint
        used_keys = set()

        # Replace template variables
        for key, value in input_data.items():
            template = f"{{{key}}}"
            if template in url:
                url = url.replace(template, str(value))
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
