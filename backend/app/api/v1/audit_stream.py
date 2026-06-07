"""Audit streaming API endpoint using Server-Sent Events (SSE)."""

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy import select

from app.database import async_session_maker
from app.models.agent import Agent
from app.models.agent_permission import AgentPermission
from app.services.auth_service import AuthService
from app.services.event_bus import event_bus

router = APIRouter(prefix="/audit", tags=["audit"])


async def get_user_agent_ids(user_id: uuid.UUID) -> set[str]:
    """
    Get all agent IDs that the user has admin access to.

    Returns IDs for:
    - Agents owned by the user
    - Agents where user has admin permission
    """
    async with async_session_maker() as session:
        # Get agents owned by user
        owned_query = select(Agent.id).where(Agent.user_id == user_id)
        owned_result = await session.execute(owned_query)
        owned_ids = {str(row[0]) for row in owned_result.fetchall()}

        # Get agents where user has admin permission
        admin_query = select(AgentPermission.agent_id).where(
            AgentPermission.user_id == user_id,
            AgentPermission.permission_type == "admin",
        )
        admin_result = await session.execute(admin_query)
        admin_ids = {str(row[0]) for row in admin_result.fetchall()}

        return owned_ids | admin_ids


async def event_generator(subscriber_id: str, queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """
    Generate SSE events from the event queue.

    Yields SSE-formatted events:
    event: <event_type>
    data: <json_data>
    """
    try:
        while True:
            try:
                # Wait for events with timeout to allow periodic keepalive
                event = await asyncio.wait_for(queue.get(), timeout=30.0)

                # Format as SSE
                event_dict = event.to_dict()
                yield f"event: {event_dict['event']}\n"
                yield f"data: {json.dumps(event_dict['data'])}\n\n"

            except asyncio.TimeoutError:
                # Send keepalive comment to prevent connection timeout
                yield ": keepalive\n\n"

    except asyncio.CancelledError:
        pass
    finally:
        # Clean up subscription when client disconnects
        event_bus.unsubscribe(subscriber_id)


@router.get("/stream")
async def audit_stream(
    token: str = Query(..., description="JWT authentication token"),
):
    """
    Server-Sent Events endpoint for streaming live audit events.

    Streams real-time events for:
    - conversation_started: When a new conversation begins
    - tool_use_start: When a tool execution begins
    - tool_use_complete: When a tool execution finishes
    - message_complete: When an agent message is complete

    Events are filtered to only include agents the authenticated user
    owns or has admin permission for.

    Query Parameters:
        token: JWT authentication token (required since SSE doesn't support headers)

    Returns:
        StreamingResponse with SSE content type
    """
    # Validate JWT token from query parameter
    try:
        user_info = AuthService.verify_token(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
        )

    user_id = user_info["user_id"]

    # Get agent IDs user has access to
    agent_ids = await get_user_agent_ids(user_id)

    if not agent_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No agents found. Create an agent to use audit streaming.",
        )

    # Subscribe to event bus
    subscriber_id, queue = await event_bus.subscribe(agent_ids)

    # Return SSE streaming response
    return StreamingResponse(
        event_generator(subscriber_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
