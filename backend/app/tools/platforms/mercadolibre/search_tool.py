"""Mercado Libre Search Tool."""

import logging
from typing import Any

from app.models.integration import Integration
from app.tools.platforms.base_platform_tool import BasePlatformTool
from app.tools.platforms.mercadolibre import config as ml_config

logger = logging.getLogger(__name__)


class MercadoLibreSearchTool(BasePlatformTool):
    """Tool for searching products on Mercado Libre marketplace."""

    def __init__(self, tool_id: str, tool_config: dict[str, Any], integration: Integration):
        """
        Initialize Search tool.

        Args:
            tool_id: Tool identifier
            tool_config: Tool configuration
            integration: Integration record with credentials
        """
        super().__init__(tool_id, tool_config, integration)
        self.name = "mercadolibre_search"
        self.description = "Search for products on Mercado Libre marketplace to find items, compare prices, and get product details"

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute search action.

        Args:
            input_data: Search parameters

        Returns:
            Search results with product details
        """
        try:
            return await self._search_products(input_data)
        except Exception as e:
            logger.error(f"Search tool error: {e}")
            return {"success": False, "error": str(e)}

    async def _search_products(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Search for products on Mercado Libre.

        Args:
            input_data: Search parameters (query, category, condition, etc.)

        Returns:
            Search results with product information
        """
        query = input_data.get("query")
        if not query:
            return {"success": False, "error": "query is required"}

        # Get site ID (default to Argentina)
        site_id = input_data.get("site_id", ml_config.DEFAULT_SITE_ID)

        # Build search parameters
        params = {
            "q": query,
            "limit": input_data.get("limit", 50),
            "offset": input_data.get("offset", 0),
        }

        # Add optional filters
        if category_id := input_data.get("category_id"):
            params["category"] = category_id

        if condition := input_data.get("condition"):
            params["condition"] = condition

        if min_price := input_data.get("min_price"):
            params["price"] = str(min_price)

        if max_price := input_data.get("max_price"):
            if "price" in params:
                params["price"] = f"{min_price}-{max_price}"
            else:
                params["price"] = f"0-{max_price}"

        # Sort options: relevance, price_asc, price_desc
        if sort := input_data.get("sort"):
            params["sort"] = sort

        # Make API request (public endpoint - no authentication required)
        response = await self._make_public_request(
            method="GET",
            endpoint=f"{ml_config.SITES_ENDPOINT}/{site_id}/search",
            params=params,
        )

        # Extract relevant information from results
        results = []
        for item in response.get("results", []):
            result = {
                "id": item.get("id"),
                "title": item.get("title"),
                "price": item.get("price"),
                "currency_id": item.get("currency_id"),
                "condition": item.get("condition"),
                "thumbnail": item.get("thumbnail"),
                "permalink": item.get("permalink"),
                "available_quantity": item.get("available_quantity"),
                "sold_quantity": item.get("sold_quantity"),
            }

            # Add seller information if available
            if seller := item.get("seller"):
                result["seller"] = {
                    "id": seller.get("id"),
                    "nickname": seller.get("nickname"),
                }

            # Add shipping info if available
            if shipping := item.get("shipping"):
                result["free_shipping"] = shipping.get("free_shipping", False)

            results.append(result)

        # Calculate price statistics if requested
        stats = None
        if input_data.get("include_stats", False) and results:
            prices = [r["price"] for r in results if r.get("price")]
            if prices:
                stats = {
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "avg_price": sum(prices) / len(prices),
                    "median_price": sorted(prices)[len(prices) // 2],
                    "total_results": len(results),
                }

                # Calculate stats by condition if available
                conditions = {}
                for result in results:
                    cond = result.get("condition", "unknown")
                    if cond not in conditions:
                        conditions[cond] = []
                    if result.get("price"):
                        conditions[cond].append(result["price"])

                stats["by_condition"] = {}
                for cond, prices_list in conditions.items():
                    if prices_list:
                        stats["by_condition"][cond] = {
                            "count": len(prices_list),
                            "min_price": min(prices_list),
                            "max_price": max(prices_list),
                            "avg_price": sum(prices_list) / len(prices_list),
                        }

        return {
            "success": True,
            "results": results,
            "total": response.get("paging", {}).get("total", len(results)),
            "limit": response.get("paging", {}).get("limit", params["limit"]),
            "offset": response.get("paging", {}).get("offset", params["offset"]),
            "stats": stats,
        }

    async def _make_public_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make a public API request (no authentication required).

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json: JSON payload

        Returns:
            API response
        """
        import httpx

        url = f"{self.integration.api_base_url}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

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
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'libro usado harry potter', 'iPhone 13', 'zapatillas nike'). Use SPANISH for better results.",
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Filter by category ID (optional). Use mercadolibre_categories tool to find category IDs.",
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["new", "used", "refurbished"],
                        "description": "Filter by item condition (optional)",
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price filter (optional)",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price filter (optional)",
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["relevance", "price_asc", "price_desc"],
                        "description": "Sort order (default: relevance). Use price_asc to find cheapest first, price_desc for most expensive first.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default: 50, max: 50)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination (default: 0)",
                    },
                    "site_id": {
                        "type": "string",
                        "description": "Site ID (default: MLA for Argentina). Other options: MLB (Brazil), MLM (Mexico), etc.",
                    },
                    "include_stats": {
                        "type": "boolean",
                        "description": "Include price statistics (min, max, avg, median) in the response (default: false). Useful for price analysis and comparison.",
                    },
                },
                "required": ["query"],
            },
        }
