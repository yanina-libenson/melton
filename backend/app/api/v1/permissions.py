"""Agent permissions API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.database import DatabaseSession
from app.dependencies import CurrentUser
from app.services.permission_service import PermissionService

router = APIRouter()


# Request/Response Models
class GrantPermissionRequest(BaseModel):
    """Request to grant permission to a user."""

    user_email: EmailStr
    permission_type: str  # "use" or "admin"


class ShareCodeResponse(BaseModel):
    """Response with share code information."""

    share_code: str
    share_url: str


class AcceptShareCodeRequest(BaseModel):
    """Request to accept a share code."""

    share_code: str


class PermissionResponse(BaseModel):
    """User permission information."""

    user_id: str
    email: str
    full_name: str | None
    permission_type: str
    granted_at: str
    granted_by: str


# Dependency to get PermissionService
async def get_permission_service(session: DatabaseSession) -> PermissionService:
    """Dependency to get PermissionService instance."""
    return PermissionService(session)


PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]


@router.post(
    "/agents/{agent_id}/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_permission(
    agent_id: str,
    request: GrantPermissionRequest,
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
    session: DatabaseSession,
) -> PermissionResponse:
    """
    Grant permission to a user for an agent.

    Only admins can grant permissions.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
        current_user_id = current_user["user_id"]

        # Find user by email
        from sqlalchemy import select
        from app.models.user import User

        result = await session.execute(select(User).where(User.email == request.user_email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {request.user_email} not found",
            )

        # Grant permission
        permission = await permission_service.grant_permission(
            agent_id=agent_uuid,
            user_id=user.id,
            granted_by=current_user_id,
            permission_type=request.permission_type,
        )

        return PermissionResponse(
            user_id=str(permission.user_id),
            email=user.email,
            full_name=user.full_name,
            permission_type=permission.permission_type,
            granted_at=permission.granted_at.isoformat(),
            granted_by=str(permission.granted_by),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/agents/{agent_id}/my-permission")
async def get_my_permission(
    agent_id: str,
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
    session: DatabaseSession,
) -> dict:
    """
    Get the current user's permission level for an agent.

    Returns:
        - has_permission: bool
        - permission_type: "admin" | "use" | null
    """
    try:
        from sqlalchemy import select
        from app.models.agent import Agent

        agent_uuid = uuid.UUID(agent_id)
        current_user_id = current_user["user_id"]

        # First check if user is the owner of the agent (always admin)
        result = await session.execute(
            select(Agent).where(Agent.id == agent_uuid)
        )
        agent = result.scalar_one_or_none()
        if agent and agent.user_id == current_user_id:
            return {"has_permission": True, "permission_type": "admin"}

        # Check if user is admin via permission table
        is_admin = await permission_service.is_admin(agent_uuid, current_user_id)
        if is_admin:
            return {"has_permission": True, "permission_type": "admin"}

        # Check if user has any permission
        has_permission = await permission_service.has_permission(agent_uuid, current_user_id)
        if has_permission:
            return {"has_permission": True, "permission_type": "use"}

        return {"has_permission": False, "permission_type": None}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/agents/{agent_id}/permissions", response_model=list[PermissionResponse])
async def list_agent_permissions(
    agent_id: str,
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
) -> list[PermissionResponse]:
    """
    List all users with permissions on an agent.

    Only users with at least "use" permission can view this.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
        current_user_id = current_user["user_id"]

        # Check if current user has permission to view
        if not await permission_service.has_permission(agent_uuid, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this agent's permissions",
            )

        users = await permission_service.list_agent_users(agent_uuid)
        return [PermissionResponse(**user) for user in users]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/agents/{agent_id}/permissions/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_permission(
    agent_id: str,
    user_id: str,
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
) -> None:
    """
    Revoke permission from a user for an agent.

    Only admins can revoke permissions.
    Cannot remove the last admin.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
        user_uuid = uuid.UUID(user_id)
        current_user_id = current_user["user_id"]

        success = await permission_service.revoke_permission(
            agent_id=agent_uuid,
            user_id=user_uuid,
            revoked_by=current_user_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found",
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/agents/{agent_id}/share-code", response_model=ShareCodeResponse)
async def generate_share_code(
    agent_id: str,
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
) -> ShareCodeResponse:
    """
    Generate a share code for an agent.

    Only admins can generate share codes.
    Returns a short code that can be shared with others.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
        current_user_id = current_user["user_id"]

        share_code = await permission_service.generate_share_code(
            agent_id=agent_uuid,
            generated_by=current_user_id,
        )

        # TODO: Update this URL when we have the actual domain
        share_url = f"https://meltonagents.com/share/{share_code}"

        return ShareCodeResponse(
            share_code=share_code,
            share_url=share_url,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/agents/{agent_id}/share-code",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_share_code(
    agent_id: str,
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
) -> None:
    """
    Revoke the share code for an agent.

    Only admins can revoke share codes.
    This prevents new users from joining via the old share code.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
        current_user_id = current_user["user_id"]

        await permission_service.revoke_share_code(
            agent_id=agent_uuid,
            revoked_by=current_user_id,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/share/accept")
async def accept_share_code(
    request: AcceptShareCodeRequest,
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
) -> dict:
    """
    Accept a share code and gain access to an agent.

    Anyone with a valid share code can use this endpoint to get "use" permission.
    """
    try:
        current_user_id = current_user["user_id"]

        agent = await permission_service.accept_share_code(
            share_code=request.share_code,
            user_id=current_user_id,
        )

        return {
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "message": f"You now have access to {agent.name}",
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
