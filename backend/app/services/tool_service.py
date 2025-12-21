"""Tool service for managing tools within integrations."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import Tool
from app.models.integration import Integration


class ToolService:
    """Service for managing tools."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_tool(
        self,
        integration_id: uuid.UUID,
        name: str,
        description: str | None,
        tool_type: str | None,
        tool_schema: dict,
        config: dict,
        is_enabled: bool = True,
    ) -> Tool:
        """Create a new tool."""
        # Verify integration exists
        result = await self.session.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise ValueError(f"Integration with ID {integration_id} not found")

        tool = Tool(
            integration_id=integration_id,
            name=name,
            description=description,
            tool_type=tool_type,
            tool_schema=tool_schema or {},
            config=config or {},
            is_enabled=is_enabled,
        )

        self.session.add(tool)
        await self.session.flush()
        await self.session.refresh(tool)

        return tool

    async def get_tool(self, tool_id: uuid.UUID) -> Tool | None:
        """Get a tool by ID."""
        result = await self.session.execute(
            select(Tool).where(Tool.id == tool_id)
        )
        return result.scalar_one_or_none()

    async def get_integration_tools(self, integration_id: uuid.UUID) -> list[Tool]:
        """Get all tools for an integration."""
        result = await self.session.execute(
            select(Tool)
            .where(Tool.integration_id == integration_id)
            .order_by(Tool.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_tool(
        self,
        tool_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        tool_schema: dict | None = None,
        config: dict | None = None,
        is_enabled: bool | None = None,
    ) -> Tool:
        """Update a tool."""
        tool = await self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool with ID {tool_id} not found")

        if name is not None:
            tool.name = name
        if description is not None:
            tool.description = description
        if tool_schema is not None:
            tool.tool_schema = tool_schema
        if config is not None:
            tool.config = config
        if is_enabled is not None:
            tool.is_enabled = is_enabled

        tool.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(tool)

        return tool

    async def delete_tool(self, tool_id: uuid.UUID) -> None:
        """Delete a tool."""
        tool = await self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool with ID {tool_id} not found")

        await self.session.delete(tool)
        await self.session.flush()
