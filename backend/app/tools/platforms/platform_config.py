"""Platform configuration and OAuth settings for pre-built integrations."""

from dataclasses import dataclass


@dataclass
class OAuthConfig:
    """OAuth 2.0 configuration for a platform."""

    authorize_url: str
    token_url: str
    client_id_env: str  # Environment variable name for client ID
    client_secret_env: str  # Environment variable name for client secret
    scopes: list[str]
    redirect_uri_path: str  # Path appended to base URL for redirect

    def get_redirect_uri(self, base_url: str) -> str:
        """Build complete redirect URI from base URL and path."""
        return f"{base_url.rstrip('/')}{self.redirect_uri_path}"


@dataclass
class PlatformConfig:
    """Pre-built platform configuration."""

    id: str
    name: str
    description: str
    category: str
    oauth_config: OAuthConfig | None
    base_api_url: str
    rate_limit: dict[str, int]  # {"requests": 1500, "per": "minute"}


# Platform Registry - Add new pre-built platforms here
PLATFORMS: dict[str, PlatformConfig] = {
    "mercadolibre": PlatformConfig(
        id="mercadolibre",
        name="Mercado Libre",
        description="Marketplace integration for publications and customer questions",
        category="E-commerce",
        oauth_config=OAuthConfig(
            authorize_url="https://auth.mercadolibre.com.ar/authorization",
            token_url="https://api.mercadolibre.com/oauth/token",
            client_id_env="MERCADOLIBRE_CLIENT_ID",
            client_secret_env="MERCADOLIBRE_CLIENT_SECRET",
            scopes=["read", "write", "offline_access"],
            redirect_uri_path="/es-AR/oauth/callback/mercadolibre",
        ),
        base_api_url="https://api.mercadolibre.com",
        rate_limit={"requests": 1500, "per": "minute"},
    )
}


def get_platform(platform_id: str) -> PlatformConfig:
    """
    Get platform configuration by ID.

    Args:
        platform_id: Platform identifier

    Returns:
        Platform configuration

    Raises:
        ValueError: If platform not found
    """
    platform = PLATFORMS.get(platform_id)
    if not platform:
        raise ValueError(f"Unknown platform: {platform_id}")
    return platform
