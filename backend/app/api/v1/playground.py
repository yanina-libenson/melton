"""Playground WebSocket endpoint for real-time agent testing."""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import async_session_maker
from app.services.execution_service import AgentExecutionService
from app.services.user_api_key_service import UserApiKeyService

router = APIRouter()


@router.websocket("/{agent_id}")
async def playground_websocket(websocket: WebSocket, agent_id: str) -> None:
    """
    WebSocket endpoint for playground testing.

    Protocol:
        Client -> Server: {"type": "user_message", "content": "...", "conversation_id": "..."}
        Server -> Client: {"type": "content_delta", "delta": "..."}
        Server -> Client: {"type": "tool_use_start", "tool_name": "...", "tool_input": {...}}
        Server -> Client: {"type": "tool_use_complete", "tool_name": "...", "result": {...}}
        Server -> Client: {"type": "message_complete", "message_id": "..."}
        Server -> Client: {"type": "error", "error": "..."}
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") != "user_message":
                await websocket.send_json({"type": "error", "error": "Invalid message type"})
                continue

            user_content = message.get("content")
            attachments = message.get("attachments", [])
            conversation_id_str = message.get("conversation_id")

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

                # Get user API keys (using mock user in dev mode)
                mock_user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
                mock_org_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
                user_api_keys = await user_api_key_service.get_all_api_keys(mock_user_id, mock_org_id)

                async for event in execution_service.execute_conversation(
                    agent_id=agent_uuid,
                    user_message=user_content,
                    conversation_id=conversation_uuid,
                    user_api_keys=user_api_keys,
                    attachments=attachments,
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
