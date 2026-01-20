"""Base class for pre-built platform tools."""

import asyncio
import logging
from abc import ABC
from typing import Any

import httpx

from app.models.integration import Integration
from app.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class BasePlatformTool(BaseTool, ABC):
    """
    Base class for pre-built platform tools.
    Handles common OAuth token management and HTTP client setup.
    """

    def __init__(self, tool_id: str, config: dict[str, Any], integration: Integration):
        """
        Initialize platform tool.

        Args:
            tool_id: Unique tool identifier
            config: Tool configuration
            integration: Integration record with credentials
        """
        super().__init__(tool_id, config)
        self.integration = integration
        self.platform_id = integration.platform_id
        self.base_url = config.get("base_url", integration.config.get("baseUrl", ""))

    def get_site_id(self) -> str:
        """
        Get site ID from integration config or use default.

        Returns:
            Site ID (e.g., "MLA", "MLB", "MLM")
        """
        from app.tools.platforms.mercadolibre import config as ml_config

        return self.integration.config.get("site_id", ml_config.DEFAULT_SITE_ID)

    async def _get_cached(self, cache_key: str, ttl: int = 3600) -> dict[str, Any] | None:
        """
        Get cached data (no-op without Redis).

        Args:
            cache_key: Cache key
            ttl: Time to live in seconds (unused)

        Returns:
            None (caching disabled)
        """
        return None

    async def _set_cache(self, cache_key: str, data: dict[str, Any], ttl: int = 3600) -> None:
        """
        Set cached data (no-op without Redis).

        Args:
            cache_key: Cache key
            data: Data to cache (unused)
            ttl: Time to live in seconds (unused)
        """
        pass

    async def _get_access_token(self) -> str:
        """
        Get valid access token, refreshing if needed.

        Returns:
            Valid OAuth access token

        Raises:
            ValueError: If no credentials found or refresh fails
        """
        from app.services.credential_service import CredentialService
        from app.database import get_database_session

        async for session in get_database_session():
            cred_service = CredentialService(session)

            # Get credentials
            credential = await cred_service.get_credentials(self.integration.id)
            if not credential:
                raise ValueError(f"No credentials found for integration {self.integration.id}")

            # Check if token is expired
            if await cred_service.is_token_expired(credential):
                # Refresh token
                from app.services.oauth_service import OAuthService

                oauth_service = OAuthService(session)
                new_token = await oauth_service.refresh_token(self.integration.id)
                return new_token

            # Decrypt and return token
            return await cred_service.decrypt_token(credential)

    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with automatic token refresh and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (will be appended to base_url)
            max_retries: Maximum number of retry attempts for transient failures
            **kwargs: Additional arguments for httpx.request

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPStatusError: For non-2xx responses after all retries
        """
        # Get access token
        access_token = await self._get_access_token()

        # Build full URL
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        # Add authorization header
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"

        # Retry logic with exponential backoff
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(
                        method=method.upper(),
                        url=url,
                        headers=headers,
                        **kwargs,
                    )
                    response.raise_for_status()

                    # Try to parse JSON, return empty dict if not JSON
                    try:
                        return response.json()
                    except Exception:
                        return {}

            except httpx.HTTPStatusError as e:
                # If 401, try to refresh token and retry once
                if e.response.status_code == 401:
                    logger.info(f"Received 401, refreshing token for integration {self.integration.id}")

                    # Force token refresh
                    from app.services.oauth_service import OAuthService
                    from app.database import get_database_session

                    async for session in get_database_session():
                        oauth_service = OAuthService(session)
                        new_token = await oauth_service.refresh_token(self.integration.id)

                        # Retry request with new token
                        headers["Authorization"] = f"Bearer {new_token}"
                        async with httpx.AsyncClient(timeout=30.0) as retry_client:
                            retry_response = await retry_client.request(
                                method=method.upper(),
                                url=url,
                                headers=headers,
                                **kwargs,
                            )
                            retry_response.raise_for_status()

                            try:
                                return retry_response.json()
                            except Exception:
                                return {}

                # If 429 (rate limit), wait and retry
                elif e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        retry_after = int(e.response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited (429), waiting {retry_after}s before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(retry_after)
                        last_exception = e
                        continue
                    else:
                        # Sanitize error message
                        logger.error(f"Rate limit exceeded after {max_retries} attempts")
                        raise Exception(f"Rate limit exceeded (HTTP 429). Please try again later.")

                # If 5xx (server error), retry with exponential backoff
                elif 500 <= e.response.status_code < 600:
                    if attempt < max_retries - 1:
                        backoff = 2 ** attempt
                        logger.warning(f"Server error {e.response.status_code}, retrying in {backoff}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(backoff)
                        last_exception = e
                        continue
                    else:
                        # Sanitize error message
                        logger.error(f"Server error {e.response.status_code} after {max_retries} attempts")
                        raise Exception(f"API server error (HTTP {e.response.status_code}). Please try again later.")

                # For other errors, handle based on status code
                else:
                    logger.error(f"API error {e.response.status_code}: {url}")

                    # For 403 (Forbidden), include error details
                    if e.response.status_code == 403:
                        try:
                            error_body = e.response.json()
                            logger.error(f"403 Forbidden response: {error_body}")
                            error_msg = error_body.get("message") or error_body.get("error") or str(error_body)
                            raise Exception(f"Access denied (HTTP 403): {error_msg}")
                        except Exception:
                            error_text = e.response.text[:500] if hasattr(e.response, 'text') else "Access denied"
                            raise Exception(f"Access denied (HTTP 403): {error_text}")

                    # For 400 (Bad Request), include error details as they contain validation info
                    elif e.response.status_code == 400:
                        try:
                            error_body = e.response.json()
                            # Extract meaningful error information
                            if isinstance(error_body, dict):
                                error_msg = error_body.get("message") or error_body.get("error") or str(error_body)
                                raise Exception(f"Validation error (HTTP 400): {error_msg}")
                            else:
                                raise Exception(f"Validation error (HTTP 400): {str(error_body)}")
                        except Exception as json_err:
                            # If can't parse JSON, include raw text (but truncated)
                            error_text = e.response.text[:500] if hasattr(e.response, 'text') else "Unknown error"
                            raise Exception(f"Validation error (HTTP 400): {error_text}")
                    else:
                        # For other status codes, don't expose details
                        raise Exception(f"API error (HTTP {e.response.status_code})")

            except httpx.RequestError as e:
                # Network errors, retry with exponential backoff
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    logger.warning(f"Request error: {e}, retrying in {backoff}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(backoff)
                    last_exception = e
                    continue
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise Exception(f"Network error: Unable to connect to API")

        # If we exhaust all retries, raise the last exception
        if last_exception:
            raise last_exception

    async def _update_integration_config(self, updates: dict[str, Any]) -> None:
        """
        Update integration config with new values using database-level locking.

        Args:
            updates: Dictionary of config updates to merge
        """
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified

        from app.database import get_database_session
        from app.models.integration import Integration

        async for session in get_database_session():
            # Use SELECT FOR UPDATE to lock the row
            stmt = select(Integration).where(Integration.id == self.integration.id).with_for_update()
            result = await session.execute(stmt)
            integration = result.scalar_one_or_none()

            if not integration:
                raise ValueError(f"Integration {self.integration.id} not found")

            # Merge updates into config
            if integration.config is None:
                integration.config = {}
            integration.config.update(updates)

            # Mark as modified for SQLAlchemy to detect the change
            flag_modified(integration, "config")

            # Commit changes
            await session.commit()
            await session.refresh(integration)

            # Update self.integration with new values
            self.integration.config = integration.config
