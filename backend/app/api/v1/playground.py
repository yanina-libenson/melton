"""Playground WebSocket endpoint for real-time agent testing."""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from app.config import settings
from app.database import async_session_maker
from app.services.execution_service import AgentExecutionService
from app.services.user_api_key_service import UserApiKeyService
from app.services.permission_service import PermissionService

router = APIRouter()


@router.websocket("/{agent_id}")
async def playground_websocket(
    websocket: WebSocket,
    agent_id: str,
    token: str = Query(..., description="JWT authentication token"),
) -> None:
    """
    WebSocket endpoint for playground testing.

    Requires at least "use" permission on the agent.

    Protocol:
        Client -> Server: {"type": "user_message", "content": "...", "conversation_id": "..."}
        Server -> Client: {"type": "content_delta", "delta": "..."}
        Server -> Client: {"type": "tool_use_start", "tool_name": "...", "tool_input": {...}}
        Server -> Client: {"type": "tool_use_complete", "tool_name": "...", "result": {...}}
        Server -> Client: {"type": "message_complete", "message_id": "..."}
        Server -> Client: {"type": "error", "error": "..."}
    """
    await websocket.accept()

    # Verify JWT token and get current user
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        current_user_id = uuid.UUID(payload.get("user_id"))
        organization_id = payload.get("organization_id")
    except (JWTError, ValueError, KeyError):
        await websocket.send_json({"type": "error", "error": "Invalid authentication token"})
        await websocket.close()
        return

    try:
        while True:
            # Receive message from client
            print("[Playground] Waiting for message...")
            data = await websocket.receive_text()
            print(f"[Playground] Received data: {data[:200]}...")  # Log first 200 chars
            message = json.loads(data)
            print(f"[Playground] Parsed message: type={message.get('type')}, content_length={len(message.get('content', ''))}, attachments={len(message.get('attachments', []))}")

            if message.get("type") != "user_message":
                print(f"[Playground] Invalid message type: {message.get('type')}")
                await websocket.send_json({"type": "error", "error": "Invalid message type"})
                continue

            user_content = message.get("content")
            attachments = message.get("attachments", [])
            conversation_id_str = message.get("conversation_id")
            print(f"[Playground] Processing user message: content='{user_content[:50]}...', {len(attachments)} attachments")

            if not user_content and not attachments:
                await websocket.send_json({"type": "error", "error": "Missing content or attachments"})
                continue

            # Parse IDs
            try:
                agent_uuid = uuid.UUID(agent_id)
                conversation_uuid = uuid.UUID(conversation_id_str) if conversation_id_str else None
            except ValueError:
                await websocket.send_json({"type": "error", "error": "Invalid UUID format"})
                continue

            # Execute conversation with streaming
            async with async_session_maker() as session:
                execution_service = AgentExecutionService(session)
                user_api_key_service = UserApiKeyService(session)
                permission_service = PermissionService(session)

                # Get the agent to find its owner
                from sqlalchemy import select
                from app.models.agent import Agent

                result = await session.execute(select(Agent).where(Agent.id == agent_uuid))
                agent = result.scalar_one_or_none()

                if not agent:
                    await websocket.send_json({"type": "error", "error": "Agent not found"})
                    continue

                # Verify user has permission to use this agent
                has_permission = await permission_service.has_permission(agent_uuid, current_user_id)
                is_owner = agent.user_id == current_user_id

                if not has_permission and not is_owner:
                    await websocket.send_json({"type": "error", "error": "You don't have permission to use this agent"})
                    continue

                # Get user API keys from the agent's owner (for tool execution)
                user_api_keys = await user_api_key_service.get_all_api_keys(
                    agent.user_id, agent.organization_id
                )

                # Create conversation associated with current user (not agent owner)
                async for event in execution_service.execute_conversation(
                    agent_id=agent_uuid,
                    user_message=user_content,
                    conversation_id=conversation_uuid,
                    user_api_keys=user_api_keys,
                    attachments=attachments,
                    user_id=current_user_id,  # Use authenticated user's ID
                ):
                    await websocket.send_json(event.to_dict())

                # Commit session after execution
                await session.commit()

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            # Connection already closed
            pass
