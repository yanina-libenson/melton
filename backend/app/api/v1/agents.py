"""Agent API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.dependencies import AgentServiceDep, CurrentUser, PermissionServiceDep
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.schemas.integration import IntegrationResponse
from app.services.integration_service import IntegrationService

router = APIRouter()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    current_user: CurrentUser,
    agent_service: AgentServiceDep,
) -> AgentResponse:
    """Create a new agent."""
    agent = await agent_service.create_agent(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
        agent_data=agent_data,
    )
    return AgentResponse.model_validate(agent)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    current_user: CurrentUser,
    agent_service: AgentServiceDep,
    permission_service: PermissionServiceDep,
    include_shared: bool = True,
    admin_only: bool = True,
) -> list[AgentResponse]:
    """
    List agents for the current user.

    By default, returns only agents the user can manage (admin permission).
    Set admin_only=false to include agents with "use" permission.
    Set include_shared=false to only show owned agents (ignore shared).
    """
    # Get owned agents (user always has admin permission on these)
    owned_agents = await agent_service.list_agents_for_user(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
    )

    if not include_shared:
        return [AgentResponse.model_validate(agent) for agent in owned_agents]

    # Get shared agents (with optional admin-only filter)
    shared_agents = await permission_service.list_user_agents(
        user_id=current_user["user_id"],
        permission_type="admin" if admin_only else None,
    )

    # Combine and deduplicate (owned agents are already in the list)
    owned_ids = {agent.id for agent in owned_agents}
    all_agents = list(owned_agents) + [agent for agent in shared_agents if agent.id not in owned_ids]

    # Sort by updated_at descending
    all_agents.sort(key=lambda a: a.updated_at, reverse=True)

    return [AgentResponse.model_validate(agent) for agent in all_agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    current_user: CurrentUser,
    agent_service: AgentServiceDep,
    permission_service: PermissionServiceDep,
) -> AgentResponse:
    """Get an agent by ID. Requires at least 'use' permission."""
    agent = await agent_service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    # Check permission
    has_access = await permission_service.has_permission(
        agent_id=agent_id,
        user_id=current_user["user_id"],
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this agent",
        )

    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    agent_data: AgentUpdate,
    current_user: CurrentUser,
    agent_service: AgentServiceDep,
    permission_service: PermissionServiceDep,
) -> AgentResponse:
    """Update an agent. Requires 'admin' permission."""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"📥 Backend received AgentUpdate: {agent_data.model_dump(exclude_unset=True)}")
    logger.error(f"📥 With aliases: {agent_data.model_dump(exclude_unset=True, by_alias=True)}")

    # Check admin permission
    is_admin = await permission_service.is_admin(
        agent_id=agent_id,
        user_id=current_user["user_id"],
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have admin permission to update this agent",
        )

    agent = await agent_service.update_agent(agent_id, agent_data)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    current_user: CurrentUser,
    agent_service: AgentServiceDep,
    permission_service: PermissionServiceDep,
) -> None:
    """Delete an agent. Requires 'admin' permission."""
    # Check admin permission
    is_admin = await permission_service.is_admin(
        agent_id=agent_id,
        user_id=current_user["user_id"],
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have admin permission to delete this agent",
        )

    success = await agent_service.delete_agent(agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )


@router.get("/{agent_id}/integrations", response_model=list[IntegrationResponse])
async def list_agent_integrations(
    agent_id: uuid.UUID,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[IntegrationResponse]:
    """List all integrations for an agent."""
    service = IntegrationService(session)
    integrations = await service.get_agent_integrations(agent_id)
    return [IntegrationResponse.model_validate(integration) for integration in integrations]
