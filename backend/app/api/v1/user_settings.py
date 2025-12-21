"""User settings API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.dependencies import get_current_user
from app.schemas.user_api_key import (
    UserApiKeyResponse,
    UserApiKeysResponse,
    UserApiKeysUpdate,
)
from app.services.user_api_key_service import UserApiKeyService

router = APIRouter(prefix="/user-settings", tags=["User Settings"])


def mask_api_key(api_key: str) -> str:
    """Mask API key for display (show first 7 chars and last 4 chars)."""
    if len(api_key) <= 11:
        return api_key[:3] + "..." + api_key[-2:]
    return api_key[:7] + "..." + api_key[-4:]


@router.get("/api-keys", response_model=UserApiKeysResponse)
async def get_user_api_keys(
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """
    Get all user API keys (masked for security).
    Returns whether each provider has a key configured.
    """
    service = UserApiKeyService(session)

    # Get all configured API keys
    api_keys = await service.get_all_api_keys(
        current_user["user_id"], current_user["organization_id"]
    )

    # Build response with masked keys
    def build_response(provider: str) -> UserApiKeyResponse:
        api_key = api_keys.get(provider)
        if api_key:
            return UserApiKeyResponse(
                provider=provider,
                is_configured=True,
                masked_key=mask_api_key(api_key),
            )
        return UserApiKeyResponse(provider=provider, is_configured=False, masked_key=None)

    return UserApiKeysResponse(
        openai=build_response("openai"),
        anthropic=build_response("anthropic"),
        google=build_response("google"),
    )


@router.post("/api-keys", response_model=UserApiKeysResponse)
async def update_user_api_keys(
    api_keys: UserApiKeysUpdate,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """
    Update user API keys for LLM providers.
    Only updates keys that are provided (non-null).
    """
    service = UserApiKeyService(session)

    # Update each provided API key
    if api_keys.openai:
        await service.save_api_key(
            current_user["user_id"],
            current_user["organization_id"],
            "openai",
            api_keys.openai,
        )

    if api_keys.anthropic:
        await service.save_api_key(
            current_user["user_id"],
            current_user["organization_id"],
            "anthropic",
            api_keys.anthropic,
        )

    if api_keys.google:
        await service.save_api_key(
            current_user["user_id"],
            current_user["organization_id"],
            "google",
            api_keys.google,
        )

    await session.commit()

    # Return updated API keys status
    return await get_user_api_keys(current_user, session)


@router.delete("/api-keys/{provider}")
async def delete_user_api_key(
    provider: str,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """Delete user API key for a specific provider."""
    if provider not in ["openai", "anthropic", "google"]:
        raise HTTPException(status_code=400, detail="Invalid provider")

    service = UserApiKeyService(session)
    deleted = await service.delete_api_key(
        current_user["user_id"], current_user["organization_id"], provider
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")

    await session.commit()
    return {"success": True, "message": f"Deleted {provider} API key"}
