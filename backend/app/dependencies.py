"""Dependency injection for FastAPI."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.database import DatabaseSession
from app.services.agent_service import AgentService

# HTTP Bearer token authentication (JWT) - auto_error=False allows optional auth in dev
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
) -> dict[str, uuid.UUID]:
    """
    Get current user from JWT token.

    For now, this is a simple placeholder that returns a mock user.
    In production, this would verify the JWT token and extract user info.
    """
    # In development mode, allow requests without authentication
    if settings.debug and credentials is None:
        return {
            "user_id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
            "organization_id": uuid.UUID("550e8400-e29b-41d4-a716-446655440001"),
        }

    # If credentials provided or in production, validate them
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # TODO: Implement proper JWT validation
    # For now, return a mock user for development
    return {
        "user_id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        "organization_id": uuid.UUID("550e8400-e29b-41d4-a716-446655440001"),
    }


async def get_agent_service(session: DatabaseSession) -> AgentService:
    """Dependency to get AgentService instance."""
    return AgentService(session)


# Type annotations for dependencies
CurrentUser = Annotated[dict[str, uuid.UUID], Depends(get_current_user)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
