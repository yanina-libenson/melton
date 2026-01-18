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
        self,
        agent_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        channel_type: str = "playground",
        user_id: uuid.UUID | None = None,
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
            user_id=user_id,
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
            Note: "agent" role is converted to "assistant" for LLM API compatibility
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()

        # Convert "agent" role to "assistant" for LLM API compatibility
        return [
            {
                "role": "assistant" if msg.role == "agent" else msg.role,
                "content": msg.content,
            }
            for msg in messages
        ]

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

        # Update conversation's last_message_preview and updated_at
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation:
            # Truncate content for preview (max 200 chars)
            preview = content[:200] + "..." if len(content) > 200 else content
            conversation.last_message_preview = preview
            conversation.updated_at = datetime.utcnow()

            # Auto-generate title from first user message if not already set
            if role == "user" and not conversation.title:
                title = await self.generate_conversation_title(conversation_id)
                conversation.title = title

            await self.session.flush()

        return message

    async def list_user_conversations(
        self, user_id: uuid.UUID, include_archived: bool = False, limit: int = 50
    ) -> list[Conversation]:
        """List conversations for a user."""
        query = select(Conversation).where(Conversation.user_id == user_id)

        if not include_archived:
            query = query.where(Conversation.is_archived == False)

        query = query.order_by(Conversation.updated_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_conversation_title(self, conversation_id: uuid.UUID, title: str) -> None:
        """Update conversation title."""
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation:
            conversation.title = title
            await self.session.flush()

    async def archive_conversation(self, conversation_id: uuid.UUID) -> None:
        """Archive a conversation."""
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation:
            conversation.is_archived = True
            await self.session.flush()

    async def unarchive_conversation(self, conversation_id: uuid.UUID) -> None:
        """Unarchive a conversation."""
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation:
            conversation.is_archived = False
            await self.session.flush()

    async def generate_conversation_title(self, conversation_id: uuid.UUID) -> str:
        """Generate a title for the conversation based on first message."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.role == "user")
            .order_by(Message.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(query)
        first_message = result.scalar_one_or_none()

        if first_message:
            # Use first 50 chars of first user message as title
            title = first_message.content[:50]
            if len(first_message.content) > 50:
                title += "..."
            return title

        return "New Conversation"
