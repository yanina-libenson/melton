"""Mercado Libre Categories Management Tool."""

import logging
from typing import Any

from app.models.integration import Integration
from app.tools.platforms.base_platform_tool import BasePlatformTool
from app.tools.platforms.mercadolibre import config as ml_config

logger = logging.getLogger(__name__)


class MercadoLibreCategoriesTool(BasePlatformTool):
    """Tool for getting category information and required attributes."""

    def __init__(self, tool_id: str, tool_config: dict[str, Any], integration: Integration):
        """
        Initialize Categories tool.

        Args:
            tool_id: Tool identifier
            tool_config: Tool configuration
            integration: Integration record with credentials
        """
        super().__init__(tool_id, tool_config, integration)
        self.name = "mercadolibre_categories"
        self.description = "Find the right category for products and get required attributes"

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute categories management action.

        Args:
            input_data: Action and parameters

        Returns:
            Action result
        """
        action = input_data.get("action")

        try:
            if action == "predict":
                return await self._predict_category(input_data)
            elif action == "get_attributes":
                return await self._get_category_attributes(input_data)
            elif action == "get_details":
                return await self._get_category_details(input_data)
            else:
                return {"success": False, "error": f"Unknown action: {action}. Available: predict, get_attributes, get_details"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _predict_category(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Predict the best category for a product based on its title.

        Args:
            input_data: title

        Returns:
            Predicted category with ID and name
        """
        title = input_data.get("title")
        if not title:
            return {"success": False, "error": "title is required"}

        try:
            # Use domain discovery endpoint (modern API)
            response = await self._make_authenticated_request(
                method="GET",
                endpoint=f"{ml_config.SITES_ENDPOINT}/{self.get_site_id()}/domain_discovery/search",
                params={"q": title, "limit": 1},
            )

            # Get the first domain result
            domains = response if isinstance(response, list) else []
            if not domains:
                return {
                    "success": False,
                    "error": "No category found for this product",
                    "suggestion": "Try using a more descriptive product title in Spanish"
                }

            domain = domains[0]
            category_id = domain.get("category_id")

            # Get full category details
            cat_response = await self._make_authenticated_request(
                method="GET",
                endpoint=f"{ml_config.CATEGORIES_ENDPOINT}/{category_id}",
            )

            return {
                "success": True,
                "predicted_category": {
                    "id": category_id,
                    "name": cat_response.get("name"),
                    "domain_id": domain.get("domain_id"),
                    "domain_name": domain.get("domain_name"),
                },
                "path_from_root": [
                    {"id": cat.get("id"), "name": cat.get("name")}
                    for cat in cat_response.get("path_from_root", [])
                ],
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Category prediction failed: {str(e)}",
                "suggestion": "Try using a more descriptive product title in Spanish (e.g., 'Cartera de cuero para mujer' instead of 'handbag')"
            }

    async def _get_category_attributes(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Get required and optional attributes for a category with caching.

        Args:
            input_data: category_id

        Returns:
            Category attributes information
        """
        category_id = input_data.get("category_id")
        if not category_id:
            return {"success": False, "error": "category_id is required"}

        # Check cache first
        cache_key = f"ml:category_attrs:{self.get_site_id()}:{category_id}"
        cached_result = await self._get_cached(cache_key, ttl=86400)  # Cache for 24 hours
        if cached_result:
            logger.info(f"Retrieved category attributes from cache for {category_id}")
            return cached_result

        # Get category details
        category_response = await self._make_authenticated_request(
            method="GET",
            endpoint=f"{ml_config.CATEGORIES_ENDPOINT}/{category_id}",
        )

        # Get category attributes
        attributes_response = await self._make_authenticated_request(
            method="GET",
            endpoint=f"{ml_config.CATEGORIES_ENDPOINT}/{category_id}/attributes",
        )

        # Parse required and optional attributes
        required_attrs = []
        optional_attrs = []

        for attr in attributes_response:
            attr_info = {
                "id": attr.get("id"),
                "name": attr.get("name"),
                "value_type": attr.get("value_type"),
                "values": [
                    {"id": v.get("id"), "name": v.get("name")}
                    for v in attr.get("values", [])
                ][:10],  # Limit to first 10 values
                "tags": attr.get("tags", {}),
            }

            if attr.get("tags", {}).get("required"):
                required_attrs.append(attr_info)
            else:
                optional_attrs.append(attr_info)

        result = {
            "success": True,
            "category": {
                "id": category_response.get("id"),
                "name": category_response.get("name"),
                "picture": category_response.get("picture"),
            },
            "required_attributes": required_attrs,
            "optional_attributes": optional_attrs[:5],  # Limit optional to 5
        }

        # Cache the result
        await self._set_cache(cache_key, result, ttl=86400)
        logger.info(f"Cached category attributes for {category_id}")

        return result

    async def _get_category_details(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Get category details including children with caching.

        Args:
            input_data: category_id

        Returns:
            Category details with children
        """
        category_id = input_data.get("category_id")
        if not category_id:
            return {"success": False, "error": "category_id is required"}

        # Check cache first
        cache_key = f"ml:category_details:{self.get_site_id()}:{category_id}"
        cached_result = await self._get_cached(cache_key, ttl=86400)  # Cache for 24 hours
        if cached_result:
            logger.info(f"Retrieved category details from cache for {category_id}")
            return cached_result

        response = await self._make_authenticated_request(
            method="GET",
            endpoint=f"{ml_config.CATEGORIES_ENDPOINT}/{category_id}",
        )

        children = [
            {"id": cat.get("id"), "name": cat.get("name")}
            for cat in response.get("children_categories", [])
        ]

        result = {
            "success": True,
            "category": {
                "id": response.get("id"),
                "name": response.get("name"),
                "picture": response.get("picture"),
            },
            "children": children,
            "total_items": response.get("total_items_in_this_category", 0),
            "path_from_root": [
                {"id": cat.get("id"), "name": cat.get("name")}
                for cat in response.get("path_from_root", [])
            ],
        }

        # Cache the result
        await self._set_cache(cache_key, result, ttl=86400)
        logger.info(f"Cached category details for {category_id}")

        return result

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
                        "enum": ["predict", "get_attributes", "get_details"],
                        "description": "WORKFLOW: (1) predict - Find category using Spanish product title. Returns category_id AND domain_id. SAVE THE DOMAIN_ID! (2) get_attributes - Get all required attributes for that category_id. CRITICAL: ALL attribute IDs returned are UPPERCASE_WITH_UNDERSCORES (e.g., BRAND, COLOR, SLEEVE_TYPE) - use them exactly as returned. (3) For fashion items: Use the domain_id from step 1 with mercadolibre_sizegrids to create/get a size chart for THAT SPECIFIC domain. (4) Use mercadolibre_publications to create, providing ALL attributes marked with 'required: true'. get_details: Get category info and child categories.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Product title in SPANISH (required for predict action). Example: 'Cartera de cuero negra para mujer' NOT 'black leather handbag'.",
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Mercado Libre category ID (required for get_attributes and get_details actions).",
                    },
                },
                "required": ["action"],
            },
        }
