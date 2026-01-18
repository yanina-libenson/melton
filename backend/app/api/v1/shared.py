"""Shared agents API endpoints - for accessing agents shared with you."""

import uuid

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, PermissionServiceDep
from app.schemas.agent import AgentResponse

router = APIRouter()


@router.get("/shared/agents", response_model=list[AgentResponse])
async def list_shared_agents(
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
) -> list[AgentResponse]:
    """
    List all agents shared with the current user.

    This returns agents where the user has been granted permission
    (either "use" or "admin") by another user.
    """
    agents = await permission_service.list_user_agents(
        user_id=current_user["user_id"]
    )

    return [AgentResponse.model_validate(agent) for agent in agents]


@router.get("/shared/agents/admin", response_model=list[AgentResponse])
async def list_shared_agents_admin_only(
    current_user: CurrentUser,
    permission_service: PermissionServiceDep,
) -> list[AgentResponse]:
    """
    List agents where the current user has admin permission.

    Useful for showing agents the user can manage.
    """
    agents = await permission_service.list_user_agents(
        user_id=current_user["user_id"],
        permission_type="admin",
    )

    return [AgentResponse.model_validate(agent) for agent in agents]
