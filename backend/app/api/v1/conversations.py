"""Conversations API endpoints for debugging and observability."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_database_session
from app.dependencies import get_current_user
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.integration import Integration
from app.models.message import Message

router = APIRouter()


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


@router.get("")
async def list_conversations(
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    limit: int = 50,
    offset: int = 0,
):
    """
    List all conversations for the user's agents.
    Returns conversation metadata including agent name, channel type, and message count.
    """
    # Get all conversations for user's agents
    query = (
        select(Conversation)
        .join(Agent)
        .where(Agent.user_id == current_user["user_id"])
        .options(selectinload(Conversation.agent))
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(query)
    conversations = result.scalars().all()

    # Get message counts for each conversation
    conversation_data = []
    for conv in conversations:
        message_count_query = select(Message).where(Message.conversation_id == conv.id)
        message_result = await session.execute(message_count_query)
        messages = message_result.scalars().all()
        message_count = len(messages)

        # Get first user message as preview
        first_user_msg = next((msg for msg in messages if msg.role == "user"), None)
        preview = first_user_msg.content[:100] if first_user_msg else "(no messages)"

        conversation_data.append(
            {
                "id": str(conv.id),
                "agent_id": str(conv.agent_id),
                "agent_name": conv.agent.name,
                "channel_type": conv.channel_type,
                "message_count": message_count,
                "preview": preview,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
        )

    return {"conversations": conversation_data, "total": len(conversation_data)}


@router.get("/{conversation_id}")
async def get_conversation_detail(
    conversation_id: uuid.UUID,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """
    Get full conversation details including:
    - All messages (user and agent)
    - Tool calls with inputs/outputs
    - Agent's system prompt at time of conversation (with tool documentation)
    - Agent configuration
    """
    # Get conversation with agent, messages, and tools
    # Need to load: Conversation -> Agent -> Integrations -> Tools
    query = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.agent)
            .selectinload(Agent.integrations)
            .selectinload(Integration.tools),
            selectinload(Conversation.messages),
        )
    )

    result = await session.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # Verify user owns this conversation's agent
    if conversation.agent.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    # Build tool schemas (same logic as execution_service._get_tool_schemas)
    tool_schemas = []
    for integration in conversation.agent.integrations:
        for tool in integration.tools:
            if tool.is_enabled:
                schema = {
                    "name": tool.tool_schema.get("name", tool.name),
                    "description": tool.description or tool.tool_schema.get("description", ""),
                    "input_schema": tool.tool_schema.get("input_schema", {"type": "object", "properties": {}}),
                }
                tool_schemas.append(schema)

    # Build enhanced system prompt with tool documentation
    enhanced_instructions = _build_enhanced_system_prompt(
        conversation.agent.instructions, tool_schemas
    )

    # Build messages with full details
    messages_data = []
    for msg in sorted(conversation.messages, key=lambda m: m.created_at):
        messages_data.append(
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "created_at": msg.created_at.isoformat(),
            }
        )

    return {
        "id": str(conversation.id),
        "agent_id": str(conversation.agent_id),
        "agent_name": conversation.agent.name,
        "agent_instructions": enhanced_instructions,  # Enhanced with tool documentation
        "agent_model_config": conversation.agent.model_config,
        "channel_type": conversation.channel_type,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "messages": messages_data,
    }
