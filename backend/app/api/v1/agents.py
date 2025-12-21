"""Agent API endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.dependencies import AgentServiceDep, CurrentUser
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate

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
) -> list[AgentResponse]:
    """List all agents for the current user."""
    agents = await agent_service.list_agents_for_user(
        user_id=current_user["user_id"],
        organization_id=current_user["organization_id"],
    )
    return [AgentResponse.model_validate(agent) for agent in agents]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    agent_service: AgentServiceDep,
) -> AgentResponse:
    """Get an agent by ID."""
    agent = await agent_service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    agent_data: AgentUpdate,
    agent_service: AgentServiceDep,
) -> AgentResponse:
    """Update an agent."""
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
    agent_service: AgentServiceDep,
) -> None:
    """Delete an agent."""
    success = await agent_service.delete_agent(agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
