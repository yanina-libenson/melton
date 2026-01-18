"""Dependency injection for FastAPI."""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.database import DatabaseSession
from app.services.agent_service import AgentService
from app.services.auth_service import AuthService

# HTTP Bearer token authentication (JWT) - auto_error=False allows optional auth in dev
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
) -> dict[str, uuid.UUID]:
    """
    Get current user from JWT token.

    Validates JWT token and returns user_id and organization_id.

    In development mode with no credentials, returns a mock user for easier testing.
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

    # Validate JWT token
    try:
        token = credentials.credentials
        user_info = AuthService.verify_token(token)
        return user_info
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
        )


async def get_agent_service(session: DatabaseSession) -> AgentService:
    """Dependency to get AgentService instance."""
    return AgentService(session)


async def get_permission_service(session: DatabaseSession):
    """Dependency to get PermissionService instance."""
    from app.services.permission_service import PermissionService
    return PermissionService(session)


async def require_agent_permission(
    agent_id: uuid.UUID,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    permission_service: Annotated["PermissionService", Depends(get_permission_service)],
    required_type: str = "use",
) -> None:
    """
    Require user to have specific permission on agent.

    Args:
        agent_id: ID of the agent
        current_user: Current user from JWT
        permission_service: Permission service instance
        required_type: Required permission type ("use" or "admin")

    Raises:
        HTTPException: If user doesn't have required permission
    """
    user_id = current_user["user_id"]

    has_permission = await permission_service.has_permission(
        agent_id=agent_id,
        user_id=user_id,
        required_type=required_type,
    )

    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have {required_type} permission for this agent",
        )


async def require_agent_admin(
    agent_id: uuid.UUID,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    permission_service: Annotated["PermissionService", Depends(get_permission_service)],
) -> None:
    """Require user to have admin permission on agent."""
    return await require_agent_permission(agent_id, current_user, permission_service, "admin")


# Type annotations for dependencies
CurrentUser = Annotated[dict[str, uuid.UUID], Depends(get_current_user)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
PermissionServiceDep = Annotated["PermissionService", Depends(get_permission_service)]
