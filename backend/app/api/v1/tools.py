"""Tool API endpoints."""

import time
import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.dependencies import get_current_user
from app.schemas.tool import ToolCreate, ToolResponse, ToolTestRequest, ToolTestResponse, ToolUpdate
from app.services.tool_service import ToolService
from app.utils.output_transformer import OutputTransformer

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


@router.post("/test", response_model=ToolTestResponse)
async def test_tool(
    data: ToolTestRequest,
    current_user: Annotated[dict[str, uuid.UUID], Depends(get_current_user)],
):
    """
    Test an API tool configuration without saving it.

    This endpoint allows users to:
    1. Test API calls with authentication
    2. See the raw API response
    3. Test field extraction mappings
    4. Verify tool configuration before saving
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Test tool request: endpoint={data.endpoint}, method={data.method}, auth={data.authentication}")

    start_time = time.time()

    try:
        # Build URL with template substitution
        url = data.endpoint
        for key, value in data.test_input.items():
            url = url.replace(f"{{{key}}}", str(value))

        # Build headers with authentication
        headers = {"Content-Type": "application/json"}

        if data.authentication == "api-key":
            header_name = data.auth_config.get("apiKeyHeader", "X-API-Key")
            api_key = data.auth_config.get("apiKeyValue")
            if api_key:
                headers[header_name] = api_key

        elif data.authentication == "bearer":
            token = data.auth_config.get("bearerToken")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif data.authentication == "basic":
            import base64
            username = data.auth_config.get("username", "")
            password = data.auth_config.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        # Make API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            if data.method == "GET":
                response = await client.get(url, headers=headers)
            elif data.method == "POST":
                response = await client.post(url, headers=headers, json=data.test_input)
            elif data.method == "PUT":
                response = await client.put(url, headers=headers, json=data.test_input)
            elif data.method == "DELETE":
                response = await client.delete(url, headers=headers)
            elif data.method == "PATCH":
                response = await client.patch(url, headers=headers, json=data.test_input)
            else:
                return ToolTestResponse(
                    success=False,
                    output=None,
                    error=f"Unsupported HTTP method: {data.method}"
                )

            response.raise_for_status()
            api_response = response.json() if response.content else {}

        # Transform output based on mode
        if data.output_mode == "full":
            output = api_response
        elif data.output_mode == "extract":
            output = OutputTransformer.transform(
                api_response,
                output_mode="extract",
                output_mapping=data.output_mapping
            )
        else:  # llm mode
            # For test endpoint, we don't execute LLM transformation
            # Just return the raw response
            output = api_response

        execution_time = time.time() - start_time

        result = ToolTestResponse(
            success=True,
            output=output,
            debug_info={
                "execution_time_ms": round(execution_time * 1000, 2),
                "status_code": response.status_code,
                "url_called": url,
                "raw_response": api_response if data.output_mode == "extract" else None
            }
        )
        logger.info(f"Test succeeded: {url}, status={response.status_code}, time={execution_time*1000:.2f}ms")
        return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        logger.error(f"HTTP error during test: {error_msg}")
        return ToolTestResponse(
            success=False,
            output=None,
            error=error_msg
        )
    except httpx.TimeoutException:
        error_msg = "Request timed out after 30 seconds"
        logger.error(f"Timeout during test: {data.endpoint}")
        return ToolTestResponse(
            success=False,
            output=None,
            error=error_msg
        )
    except Exception as e:
        logger.error(f"Error during test: {type(e).__name__}: {str(e)}", exc_info=True)
        return ToolTestResponse(
            success=False,
            output=None,
            error=str(e)
        )
