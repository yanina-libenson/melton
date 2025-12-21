"""Tool API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.dependencies import get_current_user
from app.schemas.tool import ToolCreate, ToolResponse, ToolUpdate
from app.services.tool_service import ToolService

router = APIRouter()


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    data: ToolCreate,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """Create a new tool within an integration."""
    service = ToolService(session)

    try:
        tool = await service.create_tool(
            integration_id=data.integration_id,
            name=data.name,
            description=data.description,
            tool_type=data.tool_type,
            tool_schema=data.tool_schema,
            config=data.config,
            is_enabled=data.is_enabled,
        )
        await session.commit()
        return tool
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}",
        )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: uuid.UUID,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """Get a tool by ID."""
    service = ToolService(session)
    tool = await service.get_tool(tool_id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool with ID {tool_id} not found",
        )

    return tool


@router.patch("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: uuid.UUID,
    data: ToolUpdate,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """Update a tool."""
    service = ToolService(session)

    try:
        tool = await service.update_tool(
            tool_id=tool_id,
            name=data.name,
            description=data.description,
            tool_schema=data.tool_schema,
            config=data.config,
            is_enabled=data.is_enabled,
        )
        await session.commit()
        return tool
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {str(e)}",
        )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: uuid.UUID,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    """Delete a tool."""
    service = ToolService(session)

    try:
        await service.delete_tool(tool_id)
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {str(e)}",
        )
