"""OAuth 2.0 authorization endpoints."""

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_database_session
from app.services.oauth_service import OAuthService

router = APIRouter(tags=["oauth"])


@router.get("/oauth/authorize/{platform_id}")
async def initiate_oauth(
    request: Request,
    platform_id: str,
    integration_id: str = Query(..., description="Integration ID to associate with OAuth flow"),
    session: AsyncSession = Depends(get_database_session),
):
    """
    Initiate OAuth authorization flow.

    Args:
        request: FastAPI request object
        platform_id: Platform identifier (e.g., 'mercadolibre')
        integration_id: Integration ID to associate with this OAuth flow
        session: Database session

    Returns:
        JSON with authorization_url to redirect user to
    """
    oauth_service = OAuthService(session)

    try:
        # Convert integration_id to UUID
        integration_uuid = uuid.UUID(integration_id)

        # Use frontend URL for OAuth redirect (not backend URL)
        base_url = settings.frontend_url

        # Generate authorization URL
        auth_url = await oauth_service.get_authorization_url(
            platform_id=platform_id,
            integration_id=integration_uuid,
            base_url=base_url,
        )

        return {"authorization_url": auth_url}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initiation failed: {str(e)}")
    finally:
        await oauth_service.close()


@router.post("/oauth/exchange/{platform_id}")
async def exchange_oauth_code(
    platform_id: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    session: AsyncSession = Depends(get_database_session),
):
    """
    Exchange OAuth code for tokens (called by frontend after redirect).

    Args:
        platform_id: Platform identifier
        code: Authorization code from OAuth provider
        state: State parameter for validation
        session: Database session

    Returns:
        JSON with integration_id and status
    """
    oauth_service = OAuthService(session)

    try:
        # Exchange code for tokens
        integration = await oauth_service.handle_callback(
            platform_id=platform_id,
            code=code,
            state=state,
        )

        return {
            "success": True,
            "integration_id": str(integration.id),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")
    finally:
        await oauth_service.close()


@router.post("/oauth/test-users/mercadolibre")
async def create_mercadolibre_test_user():
    """
    Create a Mercado Libre test user using Client Credentials flow.

    This endpoint uses your app's client_id and client_secret from environment variables
    to obtain an access token via Client Credentials, then creates a test user.

    Returns:
        JSON with test user credentials (id, nickname, password, email)
    """
    try:
        # Get client credentials from settings
        client_id = settings.mercadolibre_client_id
        client_secret = settings.mercadolibre_client_secret

        if not client_id or not client_secret:
            raise HTTPException(
                status_code=500,
                detail="Mercado Libre credentials not configured. Set MERCADOLIBRE_CLIENT_ID and MERCADOLIBRE_CLIENT_SECRET.",
            )

        async with httpx.AsyncClient() as client:
            # Step 1: Get access token using Client Credentials flow
            token_response = await client.post(
                "https://api.mercadolibre.com/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=token_response.status_code,
                    detail=f"Failed to get access token: {token_response.text}",
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(status_code=500, detail="No access token in response")

            # Step 2: Create test user with the access token
            user_response = await client.post(
                "https://api.mercadolibre.com/users/test_user",
                json={"site_id": "MLA"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            if user_response.status_code != 201:
                error_detail = user_response.text
                raise HTTPException(
                    status_code=user_response.status_code,
                    detail=f"Failed to create test user: {error_detail}",
                )

            test_user = user_response.json()

            return {
                "success": True,
                "test_user": {
                    "id": test_user.get("id"),
                    "nickname": test_user.get("nickname"),
                    "password": test_user.get("password"),
                    "email": test_user.get("email"),
                    "site_status": test_user.get("site_status"),
                },
            }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create test user: {str(e)}")
