"""Conversations API endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DatabaseSession
from app.models.agent import Agent
from app.models.agent_permission import AgentPermission
from app.models.conversation import Conversation
from app.models.execution_trace import ExecutionTrace
from app.models.integration import Integration
from app.models.message import Message
from app.models.tool import Tool
from app.models.user import User
from app.services.conversation_service import ConversationService
from app.services.permission_service import PermissionService


router = APIRouter(prefix="/conversations", tags=["conversations"])


def _build_enhanced_system_prompt(base_instructions: str, tool_schemas: list[dict[str, Any]]) -> str:
    """
    Build enhanced system prompt that includes default behavioral instructions and tool descriptions.
    This recreates the exact prompt that was used during agent execution.

    Structure:
    1. User's custom instructions (from agent.instructions)
    2. Default behavioral instructions (auto-added at runtime)
    3. Available tools (auto-added at runtime)
    """
    from app.services.agent_defaults import get_default_agent_instructions

    # Start with user's custom instructions
    enhanced_prompt = base_instructions

    # Append default behavioral instructions
    default_instructions = get_default_agent_instructions()
    enhanced_prompt += f"\n\n{default_instructions}"

    # Append tools section if tools are available
    if not tool_schemas:
        return enhanced_prompt

    tools_section = "\n\n# Available Tools\n\nYou have access to the following tools:\n\n"

    for tool_schema in tool_schemas:
        tool_name = tool_schema.get("name", "unknown")
        tool_description = tool_schema.get("description", "No description")
        input_schema = tool_schema.get("input_schema", {})
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        tools_section += f"## {tool_name}\n"
        tools_section += f"{tool_description}\n\n"

        if properties:
            tools_section += "**Parameters:**\n"
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                is_required = param_name in required_fields
                required_marker = " (REQUIRED)" if is_required else " (optional)"

                tools_section += f"- `{param_name}` ({param_type}){required_marker}: {param_desc}\n"
            tools_section += "\n"
        else:
            tools_section += "No parameters required.\n\n"

    return enhanced_prompt + tools_section


class ConversationResponse(BaseModel):
    """Response model for conversation."""

    id: str
    agent_id: str
    user_id: str | None
    channel_type: str
    title: str | None
    is_archived: bool
    last_message_preview: str | None
    created_at: str
    updated_at: str


class UpdateConversationRequest(BaseModel):
    """Request model for updating conversation."""

    title: str | None = None
    is_archived: bool | None = None


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser,
    session: DatabaseSession,
    include_archived: bool = False,
    limit: int = 50,
):
    """List conversations for the current user."""
    conversation_service = ConversationService(session)
    conversations = await conversation_service.list_user_conversations(
        user_id=current_user["user_id"],
        include_archived=include_archived,
        limit=limit,
    )

    return [
        ConversationResponse(
            id=str(conv.id),
            agent_id=str(conv.agent_id),
            user_id=str(conv.user_id) if conv.user_id else None,
            channel_type=conv.channel_type,
            title=conv.title,
            is_archived=conv.is_archived,
            last_message_preview=conv.last_message_preview,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
        )
        for conv in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    """Get a specific conversation."""
    conversation_service = ConversationService(session)

    try:
        conversation_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    conversation = await conversation_service.get_conversation_by_id(conversation_uuid)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if user owns this conversation
    if conversation.user_id and conversation.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")

    return ConversationResponse(
        id=str(conversation.id),
        agent_id=str(conversation.agent_id),
        user_id=str(conversation.user_id) if conversation.user_id else None,
        channel_type=conversation.channel_type,
        title=conversation.title,
        is_archived=conversation.is_archived,
        last_message_preview=conversation.last_message_preview,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    """Update a conversation (title, archived status)."""
    conversation_service = ConversationService(session)

    try:
        conversation_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    conversation = await conversation_service.get_conversation_by_id(conversation_uuid)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if user owns this conversation
    if conversation.user_id and conversation.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")

    # Update fields
    if request.title is not None:
        await conversation_service.update_conversation_title(conversation_uuid, request.title)

    if request.is_archived is not None:
        if request.is_archived:
            await conversation_service.archive_conversation(conversation_uuid)
        else:
            await conversation_service.unarchive_conversation(conversation_uuid)

    await session.commit()

    # Fetch updated conversation
    conversation = await conversation_service.get_conversation_by_id(conversation_uuid)

    return ConversationResponse(
        id=str(conversation.id),
        agent_id=str(conversation.agent_id),
        user_id=str(conversation.user_id) if conversation.user_id else None,
        channel_type=conversation.channel_type,
        title=conversation.title,
        is_archived=conversation.is_archived,
        last_message_preview=conversation.last_message_preview,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    """Delete a conversation."""
    conversation_service = ConversationService(session)

    try:
        conversation_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    conversation = await conversation_service.get_conversation_by_id(conversation_uuid)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if user owns this conversation
    if conversation.user_id and conversation.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")

    await session.delete(conversation)
    await session.commit()

    return {"message": "Conversation deleted successfully"}


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: int = 50,
):
    """Get messages in a conversation."""
    conversation_service = ConversationService(session)

    try:
        conversation_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    conversation = await conversation_service.get_conversation_by_id(conversation_uuid)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if user owns this conversation
    if conversation.user_id and conversation.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")

    messages = await conversation_service.get_conversation_history(conversation_uuid, limit=limit)

    return {"messages": messages}


@router.get("/audit/all")
async def get_audit_trail(
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: int = 100,
):
    """
    Get audit trail for all conversations across agents where user is admin.

    Returns full conversation history with:
    - User who had the conversation
    - All messages with tool calls
    - Execution traces with API payloads/responses

    Only accessible to agent creators or users with admin permission.
    """
    permission_service = PermissionService(session)
    user_id = current_user["user_id"]

    # Get all agents where user is owner or admin
    # 1. Agents owned by user
    owned_agents_query = select(Agent).where(Agent.user_id == user_id)
    owned_result = await session.execute(owned_agents_query)
    owned_agents = list(owned_result.scalars().all())

    # 2. Agents where user has admin permission
    admin_agents = await permission_service.list_user_agents(user_id, permission_type="admin")

    # Combine and deduplicate
    all_agent_ids = list(set([a.id for a in owned_agents] + [a.id for a in admin_agents]))

    if not all_agent_ids:
        return {"conversations": []}

    # Get all conversations for these agents with full details
    query = (
        select(Conversation)
        .where(Conversation.agent_id.in_(all_agent_ids))
        .options(
            selectinload(Conversation.messages).selectinload(Message.traces),
            selectinload(Conversation.agent)
            .selectinload(Agent.integrations)
            .selectinload(Integration.tools),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    conversations = result.scalars().all()

    print(f"[DEBUG] Found {len(conversations)} conversations")

    # Build response with full audit trail
    audit_data = []
    for conv in conversations:
        print(f"[DEBUG] Processing conversation {conv.id}")
        # Get user info if conversation has a user
        user_info = None
        if conv.user_id:
            user_result = await session.execute(
                select(User).where(User.id == conv.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_info = {
                    "user_id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                }

        # Build tool schemas (same logic as execution_service._get_tool_schemas)
        tool_schemas = []
        if conv.agent:
            print(f"[DEBUG] Agent {conv.agent.name} has {len(conv.agent.integrations)} integrations")
            for integration in conv.agent.integrations:
                print(f"[DEBUG] Integration {integration.name} has {len(integration.tools)} tools")
                for tool in integration.tools:
                    if tool.is_enabled:
                        schema = {
                            "name": tool.tool_schema.get("name", tool.name),
                            "description": tool.description or tool.tool_schema.get("description", ""),
                            "input_schema": tool.tool_schema.get("input_schema", {"type": "object", "properties": {}}),
                        }
                        tool_schemas.append(schema)
            print(f"[DEBUG] Built {len(tool_schemas)} tool schemas")

        # Build enhanced system prompt with tool documentation
        enhanced_instructions = None
        if conv.agent and conv.agent.instructions:
            enhanced_instructions = _build_enhanced_system_prompt(
                conv.agent.instructions, tool_schemas
            )
            print(f"[DEBUG] Enhanced instructions length: {len(enhanced_instructions) if enhanced_instructions else 0}")

        # Build messages with full details
        messages_data = []
        for msg in conv.messages:
            # Build execution traces
            traces_data = []
            for trace in msg.traces:
                traces_data.append({
                    "id": str(trace.id),
                    "step_type": trace.step_type,
                    "step_data": trace.step_data,  # Contains API payloads/responses
                    "duration_ms": trace.duration_ms,
                    "created_at": trace.created_at.isoformat(),
                })

            messages_data.append({
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "metadata": msg.message_metadata,
                "traces": traces_data,
                "created_at": msg.created_at.isoformat(),
            })

        audit_data.append({
            "conversation_id": str(conv.id),
            "agent_id": str(conv.agent_id),
            "agent_name": conv.agent.name if conv.agent else None,
            "agent_instructions": enhanced_instructions,  # Enhanced with tool documentation
            "agent_model_config": conv.agent.model_config if conv.agent else None,
            "channel_type": conv.channel_type,
            "title": conv.title,
            "user": user_info,
            "messages": messages_data,
            "message_count": len(messages_data),
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "is_archived": conv.is_archived,
        })

    return {"conversations": audit_data}
