"""Conversation service for managing conversation history."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message


class ConversationService:
    """Service for managing conversations and messages. Focused on persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_conversation(
        self, agent_id: uuid.UUID, conversation_id: uuid.UUID | None, channel_type: str = "playground"
    ) -> Conversation:
        """Get existing conversation or create new one."""
        if conversation_id:
            conversation = await self.get_conversation_by_id(conversation_id)
            if conversation:
                return conversation

        # Create new conversation
        conversation = Conversation(
            agent_id=agent_id,
            channel_type=channel_type,
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def get_conversation_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Get conversation by ID with messages."""
        query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_conversation_history(
        self, conversation_id: uuid.UUID, limit: int = 50
    ) -> list[dict[str, str]]:
        """
        Get conversation history in LLM format.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages in format: [{"role": "user", "content": "..."}, ...]
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()

        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def save_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        tool_calls: list | None = None,
    ) -> Message:
        """Save a message to the conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls or [],
        )

        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        return message
