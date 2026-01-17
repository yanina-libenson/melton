"""OAuth 2.0 authorization flow service."""

import os
import secrets
import uuid
from urllib.parse import urlencode

import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.integration import Integration
from app.services.credential_service import CredentialService
from app.tools.platforms import get_platform


class OAuthService:
    """Service for managing OAuth 2.0 authorization flows."""

    def __init__(self, session: AsyncSession):
        """
        Initialize OAuth service.

        Args:
            session: Database session
        """
        self.session = session
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        self.credential_service = CredentialService(session)

    async def get_authorization_url(
        self,
        platform_id: str,
        integration_id: uuid.UUID,
        base_url: str,
    ) -> str:
        """
        Generate OAuth authorization URL with state parameter.

        Args:
            platform_id: Platform identifier
            integration_id: Integration ID to associate with this OAuth flow
            base_url: Base URL for building redirect URI

        Returns:
            Authorization URL to redirect user to

        Raises:
            ValueError: If platform not found or OAuth not configured
        """
        # Get platform config
        platform = get_platform(platform_id)
        if not platform.oauth_config:
            raise ValueError(f"Platform {platform_id} does not support OAuth")

        oauth_config = platform.oauth_config

        # Get client ID from settings
        client_id = getattr(settings, oauth_config.client_id_env.lower(), None)
        if not client_id:
            raise ValueError(
                f"OAuth client ID not configured. Set {oauth_config.client_id_env} environment variable"
            )

        # Generate cryptographically random state token
        state = secrets.token_urlsafe(32)

        # Store state → integration_id mapping in Redis with 10 minute expiry
        await self.redis_client.setex(
            f"oauth_state:{state}",
            600,  # 10 minutes
            str(integration_id),
        )

        # Build redirect URI
        redirect_uri = oauth_config.get_redirect_uri(base_url)

        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }

        # Add scopes if defined
        if oauth_config.scopes:
            params["scope"] = " ".join(oauth_config.scopes)

        auth_url = f"{oauth_config.authorize_url}?{urlencode(params)}"
        return auth_url

    async def handle_callback(
        self,
        platform_id: str,
        code: str,
        state: str,
    ) -> Integration:
        """
        Exchange authorization code for tokens and store credentials.

        Args:
            platform_id: Platform identifier
            code: Authorization code from OAuth provider
            state: State parameter for CSRF protection

        Returns:
            Updated integration with credentials stored

        Raises:
            ValueError: If state invalid, platform not found, or token exchange fails
        """
        # Validate state and get integration_id
        integration_id_str = await self.redis_client.get(f"oauth_state:{state}")
        if not integration_id_str:
            raise ValueError("Invalid or expired OAuth state parameter")

        integration_id = uuid.UUID(integration_id_str)

        # Delete state from Redis (one-time use)
        await self.redis_client.delete(f"oauth_state:{state}")

        # Get platform config
        platform = get_platform(platform_id)
        if not platform.oauth_config:
            raise ValueError(f"Platform {platform_id} does not support OAuth")

        oauth_config = platform.oauth_config

        # Get client credentials from settings
        client_id = getattr(settings, oauth_config.client_id_env.lower(), None)
        client_secret = getattr(settings, oauth_config.client_secret_env.lower(), None)

        if not client_id or not client_secret:
            raise ValueError(
                f"OAuth credentials not configured. Set {oauth_config.client_id_env} "
                f"and {oauth_config.client_secret_env} environment variables"
            )

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                oauth_config.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": oauth_config.get_redirect_uri(
                        settings.frontend_url  # Must match the authorization redirect_uri
                    ),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise ValueError(f"Token exchange failed: {response.text}")

            token_data = response.json()

        # Extract tokens
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour

        if not access_token:
            raise ValueError("No access token in response")

        # Store credentials
        await self.credential_service.store_oauth_credentials(
            integration_id=integration_id,
            access_token=access_token,
            refresh_token=refresh_token or "",
            expires_in=expires_in,
            token_url=oauth_config.token_url,
        )

        # Get integration and update config with metadata
        stmt = select(Integration).where(Integration.id == integration_id)
        result = await self.session.execute(stmt)
        integration = result.scalar_one()

        # Update integration config with user info and OAuth status
        integration.config = integration.config or {}
        integration.config["authentication"] = "oauth"
        integration.config["baseUrl"] = platform.base_api_url

        # Try to get user info from token data (platform-specific)
        if "user_id" in token_data:
            integration.config["user_id"] = token_data["user_id"]
        if "nickname" in token_data:
            integration.config["nickname"] = token_data["nickname"]

        await self.session.commit()
        await self.session.refresh(integration)

        return integration

    async def refresh_token(self, integration_id: uuid.UUID) -> str:
        """
        Refresh access token using refresh token.

        Args:
            integration_id: Integration ID

        Returns:
            New access token

        Raises:
            ValueError: If refresh fails
        """
        # Get credentials
        credential = await self.credential_service.get_credentials(integration_id)
        if not credential:
            raise ValueError(f"No credentials found for integration {integration_id}")

        if not credential.oauth_token_url:
            raise ValueError("No token URL configured for refresh")

        # Get refresh token
        refresh_token = await self.credential_service.decrypt_refresh_token(credential)

        # Get integration to find platform
        stmt = select(Integration).where(Integration.id == integration_id)
        result = await self.session.execute(stmt)
        integration = result.scalar_one()

        if not integration.platform_id:
            raise ValueError("Integration is not a platform integration")

        # Get platform OAuth config
        platform = get_platform(integration.platform_id)
        if not platform.oauth_config:
            raise ValueError(f"Platform {integration.platform_id} does not support OAuth")

        oauth_config = platform.oauth_config

        # Get client credentials from settings
        client_id = getattr(settings, oauth_config.client_id_env.lower(), None)
        client_secret = getattr(settings, oauth_config.client_secret_env.lower(), None)

        if not client_id or not client_secret:
            raise ValueError("OAuth credentials not configured")

        # Request new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                credential.oauth_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise ValueError(f"Token refresh failed: {response.text}")

            token_data = response.json()

        # Extract new tokens
        new_access_token = token_data.get("access_token")
        new_refresh_token = token_data.get("refresh_token", refresh_token)  # Some APIs return new refresh token
        expires_in = token_data.get("expires_in", 3600)

        if not new_access_token:
            raise ValueError("No access token in refresh response")

        # Store new credentials
        await self.credential_service.store_oauth_credentials(
            integration_id=integration_id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=expires_in,
            token_url=credential.oauth_token_url,
        )

        return new_access_token

    async def close(self):
        """Close Redis connection."""
        await self.redis_client.aclose()
