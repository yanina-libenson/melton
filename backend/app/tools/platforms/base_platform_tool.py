"""Base class for pre-built platform tools."""

import asyncio
import logging
import uuid
from abc import ABC
from datetime import datetime
from typing import Any

import httpx
from redis import asyncio as aioredis

from app.config import settings
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
        Get cached data from Redis.

        Args:
            cache_key: Cache key
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            Cached data or None if not found
        """
        try:
            import json

            redis = await aioredis.from_url(settings.redis_url)
            try:
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return json.loads(cached)
                logger.debug(f"Cache miss for key: {cache_key}")
                return None
            finally:
                await redis.close()
        except Exception as e:
            logger.warning(f"Cache get failed for key {cache_key}: {e}")
            return None

    async def _set_cache(self, cache_key: str, data: dict[str, Any], ttl: int = 3600) -> None:
        """
        Set cached data in Redis.

        Args:
            cache_key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        try:
            import json

            redis = await aioredis.from_url(settings.redis_url)
            try:
                await redis.setex(cache_key, ttl, json.dumps(data))
                logger.debug(f"Cache set for key: {cache_key} with TTL: {ttl}s")
            finally:
                await redis.close()
        except Exception as e:
            logger.warning(f"Cache set failed for key {cache_key}: {e}")

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

    async def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limits using Redis.

        Raises:
            Exception: If rate limit exceeded
        """
        try:
            redis = await aioredis.from_url(settings.redis_url)
            try:
                rate_limit_key = f"rate_limit:{self.platform_id}:{self.integration.id}"

                # Get current count
                current = await redis.get(rate_limit_key)
                current_count = int(current) if current else 0

                # Check limit (1500 requests per minute for MercadoLibre)
                if current_count >= 1500:
                    logger.warning(f"Rate limit exceeded for {self.platform_id} integration {self.integration.id}")
                    raise Exception("Rate limit exceeded. Please wait before making more requests.")

                # Increment counter
                pipe = redis.pipeline()
                pipe.incr(rate_limit_key)
                if current_count == 0:
                    # Set expiry on first request
                    pipe.expire(rate_limit_key, 60)
                await pipe.execute()

            finally:
                await redis.close()
        except Exception as e:
            # Log but don't fail request if Redis is down
            logger.warning(f"Rate limit check failed: {e}")

    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with automatic token refresh, retry logic, and rate limiting.

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
        # Check rate limit
        await self._check_rate_limit()

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

                    # Force token refresh with lock to prevent race condition
                    from app.services.oauth_service import OAuthService
                    from app.database import get_database_session

                    async for session in get_database_session():
                        oauth_service = OAuthService(session)

                        # Use Redis lock to prevent concurrent refreshes
                        redis = await aioredis.from_url(settings.redis_url)
                        lock_key = f"token_refresh_lock:{self.integration.id}"

                        try:
                            # Try to acquire lock
                            lock_acquired = await redis.set(lock_key, "1", nx=True, ex=10)

                            if lock_acquired:
                                # We acquired the lock, perform refresh
                                logger.info(f"Acquired refresh lock for integration {self.integration.id}")
                                new_token = await oauth_service.refresh_token(self.integration.id)
                            else:
                                # Another process is refreshing, wait and get fresh token
                                logger.info(f"Waiting for token refresh by another process")
                                await asyncio.sleep(1)
                                new_token = await self._get_access_token()

                            # Retry request with new token in a NEW client context
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
                        finally:
                            await redis.close()

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

                    # For 400 (Bad Request), include error details as they contain validation info
                    if e.response.status_code == 400:
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
