"""Unit tests for AgentService."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate, ModelConfig
from app.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_create_agent(test_session: AsyncSession):
    """Test creating an agent."""
    service = AgentService(test_session)

    agent_data = AgentCreate(
        name="Customer Support Agent",
        instructions="You are a helpful customer support agent",
        status="draft",
        model_config=ModelConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            temperature=0.7,
            max_tokens=4096,
        ),
    )

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    agent = await service.create_agent(user_id, org_id, agent_data)

    assert agent.id is not None
    assert agent.name == "Customer Support Agent"
    assert agent.status == "draft"
    assert agent.user_id == user_id
    assert agent.organization_id == org_id
    assert agent.model_config["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_get_agent_by_id(test_session: AsyncSession, sample_agent: Agent):
    """Test retrieving an agent by ID."""
    service = AgentService(test_session)

    agent = await service.get_agent_by_id(sample_agent.id)

    assert agent is not None
    assert agent.id == sample_agent.id
    assert agent.name == sample_agent.name


@pytest.mark.asyncio
async def test_update_agent(test_session: AsyncSession, sample_agent: Agent):
    """Test updating an agent."""
    service = AgentService(test_session)

    update_data = AgentUpdate(
        name="Updated Agent Name",
        status="active",
    )

    updated_agent = await service.update_agent(sample_agent.id, update_data)

    assert updated_agent is not None
    assert updated_agent.name == "Updated Agent Name"
    assert updated_agent.status == "active"


@pytest.mark.asyncio
async def test_delete_agent(test_session: AsyncSession, sample_agent: Agent):
    """Test deleting an agent."""
    service = AgentService(test_session)

    success = await service.delete_agent(sample_agent.id)
    assert success is True

    # Verify agent is deleted
    agent = await service.get_agent_by_id(sample_agent.id)
    assert agent is None


@pytest.mark.asyncio
async def test_list_agents_for_user(test_session: AsyncSession):
    """Test listing agents for a user."""
    service = AgentService(test_session)

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    # Create multiple agents
    for i in range(3):
        agent_data = AgentCreate(
            name=f"Agent {i}",
            instructions="Test instructions",
            status="draft",
            model_config=ModelConfig(
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                temperature=0.7,
                max_tokens=4096,
            ),
        )
        await service.create_agent(user_id, org_id, agent_data)

    # List agents
    agents = await service.list_agents_for_user(user_id, org_id)

    assert len(agents) == 3
    assert all(agent.user_id == user_id for agent in agents)
