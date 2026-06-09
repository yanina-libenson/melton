"""Tests for channel deployments: DeploymentService + derived Agent.is_active."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.services.deployment_service import DEPLOYMENT_CHANNELS, DeploymentService


async def _load_agent(session, agent_id):
    # Expire the identity map so the relationship reloads fresh. In production
    # each request uses a new session, so this staleness never occurs there;
    # here a single test session would otherwise return a cached empty collection.
    session.expire_all()
    query = select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.deployments))
    return (await session.execute(query)).scalar_one()


def test_channels_constant():
    assert DEPLOYMENT_CHANNELS == {"web", "whatsapp", "email", "mobile", "apple_watch"}


@pytest.mark.asyncio
async def test_deploy_creates_active_row(test_session, sample_agent):
    svc = DeploymentService(test_session)
    dep = await svc.deploy(sample_agent.id, "apple_watch")
    assert dep.channel_type == "apple_watch"
    assert dep.is_active is True
    rows = await svc.list_for_agent(sample_agent.id)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_deploy_is_idempotent(test_session, sample_agent):
    svc = DeploymentService(test_session)
    await svc.deploy(sample_agent.id, "mobile")
    await svc.deploy(sample_agent.id, "mobile")
    rows = await svc.list_for_agent(sample_agent.id)
    assert len([r for r in rows if r.channel_type == "mobile"]) == 1


@pytest.mark.asyncio
async def test_undeploy(test_session, sample_agent):
    svc = DeploymentService(test_session)
    await svc.deploy(sample_agent.id, "web")
    assert await svc.undeploy(sample_agent.id, "web") is True
    # undeploying again is a no-op
    assert await svc.undeploy(sample_agent.id, "web") is False
    assert await svc.list_for_agent(sample_agent.id) == []


@pytest.mark.asyncio
async def test_agent_is_active_derived(test_session, sample_agent):
    svc = DeploymentService(test_session)

    # No deployments → inactive, no channels.
    agent = await _load_agent(test_session, sample_agent.id)
    assert agent.is_active is False
    assert agent.channels == []

    # Deploy to two channels → active, channels sorted.
    await svc.deploy(sample_agent.id, "apple_watch")
    await svc.deploy(sample_agent.id, "mobile")
    agent = await _load_agent(test_session, sample_agent.id)
    assert agent.is_active is True
    assert agent.channels == ["apple_watch", "mobile"]

    # Undeploy one → still active, channels shrink.
    await svc.undeploy(sample_agent.id, "mobile")
    agent = await _load_agent(test_session, sample_agent.id)
    assert agent.is_active is True
    assert agent.channels == ["apple_watch"]

    # Undeploy the last → inactive again.
    await svc.undeploy(sample_agent.id, "apple_watch")
    agent = await _load_agent(test_session, sample_agent.id)
    assert agent.is_active is False
    assert agent.channels == []
