"""Custom API tool implementation with full authentication support."""

from datetime import datetime, timedelta
from typing import Any

import httpx

from app.llm.factory import LLMProviderFactory
from app.tools.base_tool import BaseTool
from app.utils.encryption import encryption_service


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

        # LLM enhancement settings
        self.llm_enhanced = config.get("llm_enhanced", False)
        self.llm_provider = config.get("llm_provider")
        self.llm_model = config.get("llm_model")
        self.llm_api_key = config.get("llm_api_key")
        self.llm_pre_instructions = config.get("llm_pre_instructions")
        self.llm_post_instructions = config.get("llm_post_instructions")

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the API tool with authentication and optional LLM enhancement."""
        try:
            # Pre-process with LLM if enabled
            if self.llm_enhanced and self.llm_pre_instructions:
                input_data = await self._preprocess_with_llm(input_data)

            # Make API call with auth
            result = await self._make_api_call(input_data)

            # Post-process with LLM if enabled
            if self.llm_enhanced and self.llm_post_instructions:
                result = await self._postprocess_with_llm(result)

            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _make_api_call(self, input_data: dict[str, Any]) -> Any:
        """Make HTTP request with authentication."""
        headers = await self._build_headers()
        url = self._build_url(input_data)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Retry logic for OAuth token refresh
            for attempt in range(2):
                try:
                    if self.method == "GET":
                        response = await client.get(url, headers=headers, params=input_data)
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

                    # Check for 401 and refresh token if OAuth
                    if response.status_code == 401 and self.auth_type == "oauth" and attempt == 0:
                        await self._refresh_oauth_token()
                        headers = await self._build_headers()
                        continue

                    response.raise_for_status()
                    return response.json() if response.content else {}

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401 and attempt == 0:
                        continue
                    raise

    async def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers with authentication."""
        headers = {"Content-Type": "application/json"}

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

    def _build_url(self, input_data: dict[str, Any]) -> str:
        """Build URL with path parameters."""
        url = self.endpoint
        # Simple path parameter substitution
        for key, value in input_data.items():
            url = url.replace(f"{{{key}}}", str(value))
        return url

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
