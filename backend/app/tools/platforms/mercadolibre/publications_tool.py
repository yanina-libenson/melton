"""Mercado Libre Publications Management Tool."""

import asyncio
import logging
from typing import Any

from app.models.integration import Integration
from app.tools.platforms.base_platform_tool import BasePlatformTool
from app.tools.platforms.mercadolibre import config as ml_config

logger = logging.getLogger(__name__)


class MercadoLibrePublicationsTool(BasePlatformTool):
    """Tool for managing Mercado Libre product publications."""

    def __init__(self, tool_id: str, tool_config: dict[str, Any], integration: Integration):
        """
        Initialize Publications tool.

        Args:
            tool_id: Tool identifier
            tool_config: Tool configuration
            integration: Integration record with credentials
        """
        super().__init__(tool_id, tool_config, integration)
        self.name = "mercadolibre_publications"
        self.description = "Create, update, delete, and list product publications"

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute publications management action.

        Args:
            input_data: Action and parameters

        Returns:
            Action result
        """
        action = input_data.get("action")

        try:
            if action == "create":
                return await self._create_item(input_data)
            elif action == "update":
                return await self._update_item(input_data)
            elif action == "delete":
                return await self._delete_item(input_data)
            elif action == "get":
                return await self._get_item(input_data)
            elif action == "list":
                return await self._list_items(input_data)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            # Error sanitization is handled in base class
            logger.error(f"Publications tool error for action '{action}': {e}")
            return {"success": False, "error": str(e)}

    async def _create_item(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new item/publication.

        Args:
            input_data: Item data (title, price, category_id, etc.)

        Returns:
            Created item with ID and permalink
        """
        # Build item payload
        item_data = {
            "category_id": input_data.get("category_id"),
            "price": input_data.get("price"),
            "currency_id": input_data.get("currency_id", "ARS"),
            "available_quantity": input_data.get("available_quantity", 1),
            "buying_mode": input_data.get("buying_mode", ml_config.BUYING_MODE_BUY_IT_NOW),
            "condition": input_data.get("condition", ml_config.CONDITION_NEW),
            "listing_type_id": input_data.get("listing_type_id", ml_config.LISTING_TYPE_FREE),
        }

        # Add title (required field)
        title = input_data.get("title")
        if not title:
            return {"success": False, "error": "title is required"}
        item_data["title"] = title

        # Add optional fields
        if description := input_data.get("description"):
            item_data["description"] = description

        if pictures := input_data.get("pictures"):
            item_data["pictures"] = [{"source": url} for url in pictures]

        # Build attributes array (required + any additional attribute-based fields)
        attributes = input_data.get("attributes", [])

        # SIZE_GRID_ID is an attribute, not a root-level field
        # Move it from additional_fields to attributes if present
        if additional_fields := input_data.get("additional_fields"):
            if isinstance(additional_fields, dict):
                if size_grid_id := additional_fields.get("SIZE_GRID_ID"):
                    # Add SIZE_GRID_ID as an attribute
                    attributes.append({"id": "SIZE_GRID_ID", "value_id": size_grid_id})
                    # Add any other root-level fields
                    remaining_fields = {k: v for k, v in additional_fields.items() if k != "SIZE_GRID_ID"}
                    if remaining_fields:
                        item_data.update(remaining_fields)
                else:
                    # No SIZE_GRID_ID, just add all fields to root
                    item_data.update(additional_fields)

        if attributes:
            item_data["attributes"] = attributes

        # Make API request
        response = await self._make_authenticated_request(
            method="POST",
            endpoint=ml_config.ITEMS_ENDPOINT,
            json=item_data,
        )

        return {
            "success": True,
            "item_id": response.get("id"),
            "permalink": response.get("permalink"),
            "status": response.get("status"),
        }

    async def _update_item(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing item.

        Note: Some fields cannot be updated if item has sales.

        Args:
            input_data: item_id and fields to update

        Returns:
            Updated item data
        """
        item_id = input_data.get("item_id")
        if not item_id:
            return {"success": False, "error": "item_id is required"}

        # Build update payload (only include fields that are being updated)
        update_data = {}

        updatable_fields = [
            "title",
            "price",
            "available_quantity",
            "description",
            "pictures",
            "attributes",
            "status",
        ]

        for field in updatable_fields:
            if field in input_data and field != "item_id" and field != "action":
                update_data[field] = input_data[field]

        if not update_data:
            return {"success": False, "error": "No fields to update"}

        # Make API request
        response = await self._make_authenticated_request(
            method="PUT",
            endpoint=f"{ml_config.ITEMS_ENDPOINT}/{item_id}",
            json=update_data,
        )

        return {
            "success": True,
            "item_id": response.get("id"),
            "status": response.get("status"),
            "updated_fields": list(update_data.keys()),
        }

    async def _delete_item(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Delete an item (must pause first, then delete).

        Args:
            input_data: item_id to delete

        Returns:
            Deletion result
        """
        item_id = input_data.get("item_id")
        if not item_id:
            return {"success": False, "error": "item_id is required"}

        # Step 1: Pause the item
        await self._make_authenticated_request(
            method="PUT",
            endpoint=f"{ml_config.ITEMS_ENDPOINT}/{item_id}",
            json={"status": ml_config.STATUS_PAUSED},
        )

        # Step 2: Delete the item
        await self._make_authenticated_request(
            method="DELETE",
            endpoint=f"{ml_config.ITEMS_ENDPOINT}/{item_id}",
        )

        return {"success": True, "item_id": item_id, "status": "deleted"}

    async def _get_item(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Get item details.

        Args:
            input_data: item_id

        Returns:
            Item details
        """
        item_id = input_data.get("item_id")
        if not item_id:
            return {"success": False, "error": "item_id is required"}

        response = await self._make_authenticated_request(
            method="GET",
            endpoint=f"{ml_config.ITEMS_ENDPOINT}/{item_id}",
        )

        return {
            "success": True,
            "item": {
                "id": response.get("id"),
                "title": response.get("title"),
                "price": response.get("price"),
                "currency_id": response.get("currency_id"),
                "available_quantity": response.get("available_quantity"),
                "sold_quantity": response.get("sold_quantity"),
                "status": response.get("status"),
                "condition": response.get("condition"),
                "permalink": response.get("permalink"),
                "thumbnail": response.get("thumbnail"),
            },
        }

    async def _list_items(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        List user's items with parallel fetching for better performance.

        Args:
            input_data: user_id (optional), limit, offset

        Returns:
            List of items
        """
        # Get user_id from integration config or input
        user_id = input_data.get("user_id") or self.integration.config.get("user_id")
        logger.debug(f"Listing items for user_id: {user_id}")

        if not user_id:
            return {
                "success": False,
                "error": "user_id is required and not found in integration config",
            }

        # Build query parameters
        params = {
            "limit": input_data.get("limit", 50),
            "offset": input_data.get("offset", 0),
        }

        # Add optional status filter
        if status := input_data.get("status"):
            params["status"] = status

        logger.info(f"Fetching items list for user {user_id} with params: {params}")

        response = await self._make_authenticated_request(
            method="GET",
            endpoint=f"{ml_config.USERS_ENDPOINT}/{user_id}/items/search",
            params=params,
        )

        # The API returns just item IDs, so we need to fetch details for each
        item_ids = response.get("results", [])
        logger.info(f"Found {len(item_ids)} items, fetching details in parallel...")

        # Fetch details for all items in parallel
        async def fetch_item_details(item_id: str) -> dict[str, Any]:
            """Fetch details for a single item."""
            try:
                item_response = await self._make_authenticated_request(
                    method="GET",
                    endpoint=f"{ml_config.ITEMS_ENDPOINT}/{item_id}",
                )
                return {
                    "id": item_response.get("id"),
                    "title": item_response.get("title"),
                    "price": item_response.get("price"),
                    "available_quantity": item_response.get("available_quantity"),
                    "sold_quantity": item_response.get("sold_quantity"),
                    "status": item_response.get("status"),
                    "permalink": item_response.get("permalink"),
                }
            except Exception as e:
                logger.warning(f"Failed to fetch details for item {item_id}: {e}")
                return {"id": item_id, "error": str(e)}

        # Fetch all items in parallel
        items = await asyncio.gather(*[fetch_item_details(item_id) for item_id in item_ids])

        return {
            "success": True,
            "items": list(items),
            "total": response.get("paging", {}).get("total", len(items)),
            "limit": response.get("paging", {}).get("limit", params["limit"]),
            "offset": response.get("paging", {}).get("offset", params["offset"]),
        }

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
                        "enum": ["create", "update", "delete", "get", "list"],
                        "description": "Action to perform. For 'create': requires title, category_id from mercadolibre_categories predict, attributes from mercadolibre_categories get_attributes, and size_grid_id from mercadolibre_sizegrids for fashion items.",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Item ID (required for update, delete, get)",
                    },
                    "price": {
                        "type": "number",
                        "description": "Item price (required for create)",
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Mercado Libre category ID (required for create)",
                    },
                    "currency_id": {
                        "type": "string",
                        "description": "Currency code (default: ARS for Argentina)",
                    },
                    "available_quantity": {
                        "type": "integer",
                        "description": "Available quantity (default: 1)",
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["new", "used", "refurbished"],
                        "description": "Item condition (default: new)",
                    },
                    "buying_mode": {
                        "type": "string",
                        "enum": ["buy_it_now", "auction"],
                        "description": "Buying mode (default: buy_it_now)",
                    },
                    "listing_type_id": {
                        "type": "string",
                        "enum": ["free", "bronze", "silver", "gold", "gold_special", "gold_premium"],
                        "description": "Listing type - free has no cost but less visibility (default: free). IMPORTANT: pictures are REQUIRED for free listings.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Item description in SPANISH",
                    },
                    "pictures": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of image URLs (REQUIRED for create with listing_type_id='free'). Example: ['https://http2.mlstatic.com/D_NQ_NP_123456-MLA12345678901_012023-O.jpg']",
                    },
                    "title": {
                        "type": "string",
                        "description": "Product title in SPANISH (REQUIRED for create). This is the main product name that buyers will see. Must be clear and descriptive. Example: 'Cartera de cuero negra para mujer'. Max length varies by category but typically 60-70 characters.",
                    },
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "value_name": {"type": "string"},
                                "value_id": {"type": "string"}
                            }
                        },
                        "description": "Product attributes (REQUIRED for create). Get these from mercadolibre_categories get_attributes action. CRITICAL: Attribute IDs are ALWAYS UPPERCASE_WITH_UNDERSCORES (e.g., BRAND, GENDER, SLEEVE_TYPE, GARMENT_TYPE). Only include attributes marked as 'required: true' in the category's required_attributes list. Use value_name for custom text values or value_id when selecting from predefined options. IMPORTANT FOR FASHION ITEMS: After creating a size chart with mercadolibre_sizegrids, add SIZE_GRID_ID to this attributes array: {\"id\": \"SIZE_GRID_ID\", \"value_id\": \"4320172\"}. Do NOT include optional attributes unless specifically needed - optional attributes often have hidden dependencies that will cause validation errors. If you get validation errors mentioning attributes you've never seen before, it usually means you included an optional attribute that triggered additional requirements. Read error messages carefully - they tell you exactly which attributes are problematic. When in doubt, create publications with ONLY the required attributes first, then add SIZE_GRID_ID if it's a fashion item.",
                    },
                    "additional_fields": {
                        "type": "object",
                        "description": "DEPRECATED: Use the attributes array instead. This field is kept for backwards compatibility with non-attribute root-level fields, but SIZE_GRID_ID should be added to attributes array, not here. If you put SIZE_GRID_ID here, the tool will automatically move it to attributes.",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID for listing items (optional, uses integration config)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "paused", "closed"],
                        "description": "Item status filter for listing",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default: 50)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination (default: 0)",
                    },
                },
                "required": ["action"],
            },
        }
