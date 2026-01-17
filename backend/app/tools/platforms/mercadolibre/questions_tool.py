"""Mercado Libre Questions Management Tool."""

import logging
from typing import Any

from app.models.integration import Integration
from app.tools.platforms.base_platform_tool import BasePlatformTool
from app.tools.platforms.mercadolibre import config as ml_config

logger = logging.getLogger(__name__)


class MercadoLibreQuestionsTool(BasePlatformTool):
    """Tool for managing Mercado Libre customer questions."""

    def __init__(self, tool_id: str, tool_config: dict[str, Any], integration: Integration):
        """
        Initialize Questions tool.

        Args:
            tool_id: Tool identifier
            tool_config: Tool configuration
            integration: Integration record with credentials
        """
        super().__init__(tool_id, tool_config, integration)
        self.name = "mercadolibre_questions"
        self.description = "Get and answer customer questions on Mercado Libre"

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute questions management action.

        Args:
            input_data: Action and parameters

        Returns:
            Action result
        """
        action = input_data.get("action")

        try:
            if action == "get":
                return await self._get_questions(input_data)
            elif action == "answer":
                return await self._answer_question(input_data)
            elif action == "delete":
                return await self._delete_question(input_data)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            # Error sanitization is handled in base class
            logger.error(f"Questions tool error for action '{action}': {e}")
            return {"success": False, "error": str(e)}

    async def _get_questions(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Get questions for an item or a specific question.

        Args:
            input_data: item_id or question_id, optional filters

        Returns:
            Questions list or single question
        """
        question_id = input_data.get("question_id")

        # If question_id provided, get single question
        if question_id:
            response = await self._make_authenticated_request(
                method="GET",
                endpoint=f"{ml_config.QUESTIONS_ENDPOINT}/{question_id}",
            )

            return {
                "success": True,
                "question": {
                    "id": response.get("id"),
                    "text": response.get("text"),
                    "status": response.get("status"),
                    "answer": response.get("answer"),
                    "date_created": response.get("date_created"),
                    "item_id": response.get("item_id"),
                    "from": {
                        "id": response.get("from", {}).get("id"),
                        "name": response.get("from", {}).get("name"),
                    },
                },
            }

        # Get questions for an item
        item_id = input_data.get("item_id")
        if not item_id:
            return {"success": False, "error": "Either item_id or question_id is required"}

        # Build query parameters
        params = {
            "item": item_id,
            "limit": input_data.get("limit", 50),
            "offset": input_data.get("offset", 0),
        }

        # Add optional status filter
        if status := input_data.get("status"):
            params["status"] = status

        # Add sort parameter
        if sort := input_data.get("sort"):
            params["sort"] = sort  # date_asc, date_desc

        response = await self._make_authenticated_request(
            method="GET",
            endpoint=ml_config.QUESTIONS_ENDPOINT,
            params=params,
        )

        questions = []
        for q in response.get("questions", []):
            questions.append({
                "id": q.get("id"),
                "text": q.get("text"),
                "status": q.get("status"),
                "answer": q.get("answer"),
                "date_created": q.get("date_created"),
                "from": {
                    "id": q.get("from", {}).get("id"),
                    "name": q.get("from", {}).get("name"),
                },
            })

        return {
            "success": True,
            "questions": questions,
            "total": response.get("total", len(questions)),
        }

    async def _answer_question(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Answer a customer question.

        Args:
            input_data: question_id and answer_text

        Returns:
            Answer result
        """
        question_id = input_data.get("question_id")
        answer_text = input_data.get("answer_text")

        if not question_id:
            return {"success": False, "error": "question_id is required"}
        if not answer_text:
            return {"success": False, "error": "answer_text is required"}

        # Build answer payload
        answer_data = {
            "question_id": question_id,
            "text": answer_text,
        }

        response = await self._make_authenticated_request(
            method="POST",
            endpoint=ml_config.ANSWERS_ENDPOINT,
            json=answer_data,
        )

        return {
            "success": True,
            "answer_id": response.get("id"),
            "question_id": response.get("question_id"),
            "status": response.get("status"),
            "date_created": response.get("date_created"),
        }

    async def _delete_question(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Delete a question.

        Args:
            input_data: question_id

        Returns:
            Deletion result
        """
        question_id = input_data.get("question_id")
        if not question_id:
            return {"success": False, "error": "question_id is required"}

        await self._make_authenticated_request(
            method="DELETE",
            endpoint=f"{ml_config.QUESTIONS_ENDPOINT}/{question_id}",
        )

        return {"success": True, "question_id": question_id, "status": "deleted"}

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema for LLM.

        Returns:
            Tool schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get", "answer", "delete"],
                        "description": "Action to perform with questions",
                    },
                    "question_id": {
                        "type": "string",
                        "description": "Question ID (required for get single, answer, delete)",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Item ID to get questions for (required for get list)",
                    },
                    "answer_text": {
                        "type": "string",
                        "description": "Answer text (required for answer action)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["UNANSWERED", "ANSWERED"],
                        "description": "Filter questions by status",
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["date_asc", "date_desc"],
                        "description": "Sort order for questions",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of questions to return (default: 50)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination (default: 0)",
                    },
                },
                "required": ["action"],
            },
        }
