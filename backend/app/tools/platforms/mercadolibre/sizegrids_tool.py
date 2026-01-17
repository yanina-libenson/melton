"""Mercado Libre Size Grids (Size Charts) Management Tool."""

import logging
import re
from typing import Any

from app.models.integration import Integration
from app.tools.platforms.base_platform_tool import BasePlatformTool
from app.tools.platforms.mercadolibre import config as ml_config

logger = logging.getLogger(__name__)


def normalize_domain_id(domain_id: str, site_id: str = ml_config.DEFAULT_SITE_ID) -> str:
    """
    Normalize domain_id to consistent format (with site prefix).

    Args:
        domain_id: Domain ID (e.g., "MLA-T_SHIRTS", "T_SHIRTS", "MLA-TSHIRTS")
        site_id: Site ID to use if domain_id has no prefix (default: MLA)

    Returns:
        Normalized domain ID with site prefix (e.g., "MLA-T_SHIRTS")
    """
    # Remove any spaces
    domain_id = domain_id.strip()

    # If already has site prefix, validate format
    if "-" in domain_id:
        parts = domain_id.split("-", 1)
        site_id = parts[0].upper()
        domain_name = parts[1].upper().replace(" ", "_")
        return f"{site_id}-{domain_name}"

    # No prefix, add provided site_id
    domain_name = domain_id.upper().replace(" ", "_")
    return f"{site_id}-{domain_name}"


def validate_domain_id(domain_id: str) -> bool:
    """
    Validate domain_id format.

    Args:
        domain_id: Domain ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Expected format: SITE-DOMAIN_NAME (e.g., MLA-T_SHIRTS)
    pattern = r"^[A-Z]{3}-[A-Z_]+$"
    return bool(re.match(pattern, domain_id))


class MercadoLibreSizeGridsTool(BasePlatformTool):
    """Tool for managing Mercado Libre size grids (size charts)."""

    def __init__(self, tool_id: str, tool_config: dict[str, Any], integration: Integration):
        """
        Initialize Size Grids tool.

        Args:
            tool_id: Tool identifier
            tool_config: Tool configuration
            integration: Integration record with credentials
        """
        super().__init__(tool_id, tool_config, integration)
        self.name = "mercadolibre_sizegrids"
        self.description = "Manage size grids (size charts) for fashion/clothing items. Size charts are required when creating publications for items like remeras, pantalones, zapatillas, etc. Charts can be reused across multiple items in the same domain."

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute size grids management action.

        Args:
            input_data: Action and parameters

        Returns:
            Action result
        """
        action = input_data.get("action")

        try:
            if action == "list_saved":
                return await self._list_saved_charts(input_data)
            elif action == "test_search":
                return await self._test_search_endpoint(input_data)
            elif action == "get":
                return await self._get_size_grid(input_data)
            elif action == "get_tech_specs":
                return await self._get_tech_specs(input_data)
            elif action == "create":
                return await self._create_size_grid(input_data)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}. Available: list_saved, test_search, get, get_tech_specs, create",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _list_saved_charts(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        List saved size charts from integration config.

        Args:
            input_data: verify (optional) - whether to verify charts still exist

        Returns:
            List of saved charts
        """
        # Get saved charts from config
        size_charts = self.integration.config.get("size_charts", {})

        if not size_charts:
            return {
                "success": True,
                "charts": [],
                "message": "No saved size charts found. When you get the domain_id from mercadolibre_categories predict, create a size chart for that specific domain with action='create'.",
            }

        # Optionally verify charts still exist
        verify = input_data.get("verify", False)
        charts = []

        for domain_id, chart_id in size_charts.items():
            chart_info = {"domain_id": domain_id, "chart_id": chart_id}

            if verify:
                try:
                    # Try to fetch chart details
                    response = await self._make_authenticated_request(
                        method="GET",
                        endpoint=f"{ml_config.SIZE_CHARTS_ENDPOINT}/{chart_id}",
                    )
                    chart_info["name"] = response.get("names", {}).get(self.get_site_id())
                    chart_info["exists"] = True
                except Exception:
                    chart_info["exists"] = False

            charts.append(chart_info)

        return {
            "success": True,
            "charts": charts,
            "total": len(charts),
            "message": f"Found {len(charts)} saved size chart(s). Check if your product's domain_id matches any of these. Each domain needs its own chart - you cannot reuse a chart from MLA-T_SHIRTS for MLA-JEANS.",
        }

    async def _test_search_endpoint(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Test the undocumented POST /catalog/charts/search endpoint.

        Args:
            input_data: domain_id (optional)

        Returns:
            Test results
        """
        # Get user_id from integration config
        user_id = self.integration.config.get("user_id")
        if not user_id:
            return {"success": False, "error": "user_id not found in integration config"}

        domain_id = input_data.get("domain_id", "MLA-T_SHIRTS")

        # Try different payload variations
        results = []

        # Variation 1: With seller_id as int
        payload1 = {
            "domain_id": domain_id,
            "site_id": self.get_site_id(),
            "seller_id": int(user_id),
        }

        try:
            logger.info(f"[Test 1] Payload: {payload1}")
            response = await self._make_authenticated_request(
                method="POST",
                endpoint=f"{ml_config.SIZE_CHARTS_ENDPOINT}/search",
                json=payload1,
            )
            results.append({
                "test": "Payload with seller_id (int)",
                "success": True,
                "payload": payload1,
                "response": response,
            })
        except Exception as e:
            results.append({
                "test": "Payload with seller_id (int)",
                "success": False,
                "payload": payload1,
                "error": str(e),
            })

        # Variation 2: Without seller_id
        payload2 = {
            "domain_id": domain_id,
            "site_id": self.get_site_id(),
        }

        try:
            logger.info(f"[Test 2] Payload: {payload2}")
            response = await self._make_authenticated_request(
                method="POST",
                endpoint=f"{ml_config.SIZE_CHARTS_ENDPOINT}/search",
                json=payload2,
            )
            results.append({
                "test": "Payload without seller_id",
                "success": True,
                "payload": payload2,
                "response": response,
            })
        except Exception as e:
            results.append({
                "test": "Payload without seller_id",
                "success": False,
                "payload": payload2,
                "error": str(e),
            })

        # Test 3: Get active domains
        try:
            response = await self._make_authenticated_request(
                method="GET",
                endpoint=f"{ml_config.SIZE_CHARTS_ENDPOINT}/{self.get_site_id()}/configurations/active_domains",
            )
            results.append({
                "test": "Get active domains",
                "success": True,
                "response": response,
            })
        except Exception as e:
            results.append({
                "test": "Get active domains",
                "success": False,
                "error": str(e),
            })

        return {
            "success": True,
            "note": "Testing undocumented endpoints - see results",
            "results": results,
        }

    async def _get_tech_specs(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Get technical specifications for a domain to see required size chart attributes.

        Args:
            input_data: domain_id

        Returns:
            Technical specs including required attributes for size charts
        """
        domain_id = input_data.get("domain_id")
        if not domain_id:
            return {"success": False, "error": "domain_id is required"}

        # Remove site prefix if present (MLA-T_SHIRTS -> T_SHIRTS)
        clean_domain_id = domain_id.split("-", 1)[-1] if "-" in domain_id else domain_id

        # Fetch technical specs
        try:
            response = await self._make_authenticated_request(
                method="GET",
                endpoint=f"domains/{clean_domain_id}/technical_specs",
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch technical specs: {str(e)}",
            }

        # Validate response is a dict
        if not isinstance(response, dict):
            return {
                "success": False,
                "error": f"Invalid response type: expected dict, got {type(response).__name__}",
                "response": str(response)[:200],
            }

        # Extract grid-related attributes from nested structure
        grid_attributes = []
        measurement_attributes = []

        # Navigate through input -> groups -> components -> attributes
        input_section = response.get("input", {})
        groups = input_section.get("groups", [])

        for group in groups:
            components = group.get("components", [])
            for component in components:
                attributes = component.get("attributes", [])
                for attr in attributes:
                    attr_id = attr.get("id", "")
                    value_type = attr.get("value_type", "")
                    tags = attr.get("tags", [])

                    # Look for grid_id and grid_row_id attributes
                    if value_type in ["grid_id", "grid_row_id"]:
                        grid_attributes.append({
                            "id": attr_id,
                            "name": attr.get("name"),
                            "value_type": value_type,
                            "required": "required" in tags,
                            "grid_filter": "grid_filter" in tags,
                            "grid_template_required": "grid_template_required" in tags,
                        })

                    # Also collect measurement-related attributes (for size charts)
                    # These are attributes with IDs containing CIRCUMFERENCE, WIDTH, LENGTH, HEIGHT
                    if any(keyword in attr_id for keyword in ["CIRCUMFERENCE", "WIDTH", "LENGTH", "HEIGHT", "SIZE"]):
                        measurement_attributes.append({
                            "id": attr_id,
                            "name": attr.get("name"),
                            "value_type": value_type,
                            "required": "required" in tags,
                            "tags": tags,
                        })

        # If no grid attributes found, return measurement attributes as alternatives
        if not grid_attributes and not measurement_attributes:
            return {
                "success": True,
                "domain_id": domain_id,
                "raw_response": response,
                "message": "Could not find grid or measurement attributes in response. Full response returned for inspection.",
            }

        result = {
            "success": True,
            "domain_id": domain_id,
            "grid_attributes": grid_attributes,
        }

        if measurement_attributes:
            result["measurement_attributes"] = measurement_attributes
            result["message"] = f"Found {len(grid_attributes)} grid attributes and {len(measurement_attributes)} measurement attributes. For size charts, use measurement attributes like CHEST_CIRCUMFERENCE_FROM, CHEST_CIRCUMFERENCE_TO, etc."
        else:
            result["message"] = f"Found {len(grid_attributes)} grid-related attributes for {clean_domain_id}. Attributes with 'required': true MUST be included in size chart rows."

        return result

    async def _get_size_grid(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Get details of a specific size grid.

        Args:
            input_data: chart_id

        Returns:
            Size grid details
        """
        chart_id = input_data.get("chart_id")
        if not chart_id:
            return {"success": False, "error": "chart_id is required"}

        response = await self._make_authenticated_request(
            method="GET",
            endpoint=f"{ml_config.SIZE_CHARTS_ENDPOINT}/{chart_id}",
        )

        return {
            "success": True,
            "chart": {
                "id": response.get("id"),
                "name": response.get("names", {}).get(self.get_site_id()),
                "domain_id": response.get("domain_id"),
                "chart_type": response.get("chart_type"),
                "site_id": response.get("site_id"),
                "main_attribute": response.get("main_attribute"),
                "attributes": response.get("attributes", []),
                "rows": [
                    {
                        "id": row.get("id"),
                        "attributes": row.get("attributes", []),
                    }
                    for row in response.get("rows", [])
                ],
            },
        }

    async def _create_size_grid(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new size grid with domain normalization.

        Args:
            input_data: chart_name, domain_id, main_attribute_id, attributes, rows

        Returns:
            Created size grid
        """
        chart_name = input_data.get("chart_name")
        if not chart_name:
            return {"success": False, "error": "chart_name is required"}

        raw_domain_id = input_data.get("domain_id")
        if not raw_domain_id:
            return {"success": False, "error": "domain_id is required"}

        # Normalize domain_id to consistent format with site_id from config
        domain_id = normalize_domain_id(raw_domain_id, self.get_site_id())

        # Validate domain_id format
        if not validate_domain_id(domain_id):
            return {
                "success": False,
                "error": f"Invalid domain_id format: '{domain_id}'. Expected format: SITE-DOMAIN_NAME (e.g., MLA-T_SHIRTS)",
            }

        main_attribute_id = input_data.get("main_attribute_id")
        if not main_attribute_id:
            return {"success": False, "error": "main_attribute_id is required (e.g., 'SIZE')"}

        rows = input_data.get("rows")
        if not rows or not isinstance(rows, list):
            return {"success": False, "error": "rows is required and must be an array"}

        # MercadoLibre requires at least 2 sizes for a valid size chart
        if len(rows) < 2:
            return {
                "success": False,
                "error": "Size chart must have at least 2 sizes to be valid. Single-size charts are rejected by MercadoLibre. For t-shirts, create sizes like: S, M, L, XL. For each size, provide SIZE, FILTRABLE_SIZE (same as SIZE), and measurements like CHEST_CIRCUMFERENCE_FROM.",
            }

        # Check if chart already exists for this domain (with normalized domain_id)
        size_charts = self.integration.config.get("size_charts", {})
        logger.debug(f"Checking for existing size charts. Current: {size_charts}")
        logger.debug(f"Looking for normalized domain_id: {domain_id}")

        if domain_id in size_charts:
            existing_chart_id = size_charts[domain_id]
            logger.info(f"Found existing chart {existing_chart_id} for {domain_id}")
            return {
                "success": False,
                "error": f"A size chart already exists for domain {domain_id}. Reuse it instead of creating a new one. Add this to publication attributes: {{\"id\": \"SIZE_GRID_ID\", \"value_id\": \"{existing_chart_id}\"}}",
                "existing_chart_id": existing_chart_id,
                "domain_id": domain_id,
                "instruction": "Use this chart_id in your publication. Do NOT create a new chart.",
            }

        logger.info(f"No existing chart found for {domain_id}, proceeding with creation")

        # Validate GENDER attribute (required for fashion items)
        attributes = input_data.get("attributes", [])
        has_gender = any(attr.get("id") == "GENDER" for attr in attributes)
        if not has_gender:
            return {
                "success": False,
                "error": "GENDER attribute is required for size charts. Common GENDER value_ids: 339666 (Hombre), 339665 (Mujer), 339667 (Niños), 339668 (Niñas).",
            }

        # Validate common attribute IDs to catch typos
        common_tshirt_attrs = {
            "SIZE", "FILTRABLE_SIZE", "CHEST_CIRCUMFERENCE_FROM", "CHEST_CIRCUMFERENCE_TO",
            "WAIST_CIRCUMFERENCE_FROM", "WAIST_CIRCUMFERENCE_TO", "HIP_CIRCUMFERENCE_FROM",
            "HIP_CIRCUMFERENCE_TO", "SHOULDER_WIDTH", "SLEEVE_LENGTH"
        }

        # Check all attribute IDs in rows for typos
        for row_idx, row in enumerate(rows):
            for attr in row.get("attributes", []):
                attr_id = attr.get("id", "").upper()
                # Check for common typos
                # Only flag RCUMFERENCE as typo if CIRCUMFERENCE is not present
                # (since CIRCUMFERENCE contains RCUMFERENCE as substring)
                if "RCUMFERENCE" in attr_id and "CIRCUMFERENCE" not in attr_id:
                    return {
                        "success": False,
                        "error": f"Typo in attribute ID '{attr_id}' in row {row_idx + 1}. Did you mean 'CIRCUMFERENCE' instead of 'RCUMFERENCE'?",
                    }
                if "_FM" in attr_id and "_FROM" not in attr_id:
                    return {
                        "success": False,
                        "error": f"Typo in attribute ID '{attr_id}' in row {row_idx + 1}. Did you mean '_FROM' instead of '_FM'?",
                    }
                # Check if attribute looks like it should be in common set but has typo
                if attr_id not in common_tshirt_attrs:
                    # Check for similar attributes (potential typo)
                    for valid_attr in common_tshirt_attrs:
                        if len(attr_id) > 5 and len(valid_attr) > 5:
                            # Simple similarity check - if 80% of characters match in order
                            matches = sum(c1 == c2 for c1, c2 in zip(attr_id, valid_attr))
                            similarity = matches / max(len(attr_id), len(valid_attr))
                            if similarity > 0.8:
                                return {
                                    "success": False,
                                    "error": f"Possible typo in attribute ID '{attr_id}' in row {row_idx + 1}. Did you mean '{valid_attr}'?",
                                }

        # Transform rows to correct API format
        # API expects: {"id": "SIZE", "values": [{"name": "S"}]}
        # Users might send: {"id": "SIZE", "value_name": "S"} OR {"id": "SIZE", "value": "10 cm"}
        transformed_rows = []
        for row in rows:
            transformed_row = {"attributes": []}
            for attr in row.get("attributes", []):
                # Check if already in correct format
                if "values" in attr:
                    transformed_row["attributes"].append(attr)
                else:
                    # Transform from simplified format
                    attr_obj = {"id": attr["id"], "values": []}

                    # Handle different value field names
                    if "value_name" in attr:
                        attr_obj["values"].append({"name": attr["value_name"]})
                    elif "value" in attr:
                        attr_obj["values"].append({"name": attr["value"]})
                    elif "name" in attr:
                        attr_obj["values"].append({"name": attr["name"]})

                    transformed_row["attributes"].append(attr_obj)

            transformed_rows.append(transformed_row)

        # Remove site prefix from domain_id if present (MLA-T_SHIRTS -> T_SHIRTS)
        # The API expects just the domain name, not the prefixed version
        clean_domain_id = domain_id.split("-", 1)[-1] if "-" in domain_id else domain_id

        # Build size chart payload
        site_id = self.get_site_id()
        chart_data = {
            "names": {site_id: chart_name},
            "domain_id": clean_domain_id,
            "site_id": site_id,
            "main_attribute": {
                "attributes": [{"site_id": site_id, "id": main_attribute_id}]
            },
            "rows": transformed_rows,
        }

        # Add optional measure_type (only if provided, as it may not be required)
        if measure_type := input_data.get("measure_type"):
            chart_data["measure_type"] = measure_type

        # Add optional filter attributes (like GENDER)
        if attributes := input_data.get("attributes"):
            chart_data["attributes"] = attributes

        # Debug logging
        logger.info(f"Creating size chart for domain {domain_id}")
        logger.debug(f"Size chart payload: {chart_data}")

        # Create size chart
        try:
            response = await self._make_authenticated_request(
                method="POST",
                endpoint=ml_config.SIZE_CHARTS_ENDPOINT,
                json=chart_data,
            )
        except Exception as e:
            # Error details are sanitized in base class
            logger.error(f"Size chart creation failed for domain {domain_id}: {e}")

            error_str = str(e)
            # If chart name is unavailable, suggest adding timestamp
            if "chart_name_unavailable" in error_str or "name" in error_str.lower() and "already in use" in error_str.lower():
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
                return {
                    "success": False,
                    "error": f"{error_str}\n\nSuggestion: Try a unique chart name like 'Talles remeras hombre {timestamp}' or 'Talles {clean_domain_id} {timestamp}'",
                }

            return {
                "success": False,
                "error": error_str,
            }

        chart_id = response.get("id")

        # Save chart_id to integration config for reuse
        size_charts = self.integration.config.get("size_charts", {})
        size_charts[domain_id] = chart_id
        await self._update_integration_config({"size_charts": size_charts})

        return {
            "success": True,
            "chart_id": chart_id,
            "name": response.get("names", {}).get(self.get_site_id()),
            "domain_id": response.get("domain_id"),
            "message": f"Size chart created successfully. Chart ID: {chart_id}. Add this to the attributes array when creating publication: {{\"id\": \"SIZE_GRID_ID\", \"value_id\": \"{chart_id}\"}}",
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
                        "enum": ["list_saved", "get_tech_specs", "test_search", "get", "create"],
                        "description": "Action to perform. list_saved: List size charts saved in integration config by domain_id (reusable chart_ids). CRITICAL: Each domain needs its own size chart - a chart for MLA-T_SHIRTS cannot be used for MLA-JEANS. ALWAYS check list_saved BEFORE creating to see if a chart exists for YOUR SPECIFIC domain_id! get_tech_specs: Get technical specifications for a domain - returns measurement_attributes array showing EXACT attribute IDs you MUST use in size chart rows (e.g., CHEST_CIRCUMFERENCE_FROM, CHEST_CIRCUMFERENCE_TO, WAIST_CIRCUMFERENCE_FROM). MANDATORY to call this BEFORE create! test_search: TEST ONLY - Tests undocumented search endpoint. get: Get details of a specific size chart by ID. create: Create a new size chart for a specific domain and save it to config for reuse. WORKFLOW: list_saved (check if chart exists for this domain_id) → (if none for this domain) → get_tech_specs (get valid attribute IDs) → create (use exact attribute IDs from get_tech_specs).",
                    },
                    "verify": {
                        "type": "boolean",
                        "description": "For list_saved action: whether to verify each chart still exists via API call (slower but confirms validity). Default: false.",
                    },
                    "domain_id": {
                        "type": "string",
                        "description": "Domain ID from mercadolibre_categories predict action (required for create). Use the FULL domain_id with site prefix as returned by predict (e.g., MLA-T_SHIRTS, MLA-JEANS, MLA-SNEAKERS). The tool automatically removes the prefix when calling the API. Each domain needs its own size chart.",
                    },
                    "chart_id": {
                        "type": "string",
                        "description": "Size grid ID (required for get action). This is the SIZE_GRID_ID to use in publications.",
                    },
                    "chart_name": {
                        "type": "string",
                        "description": "Name for the new size chart in SPANISH (required for create). Example: 'Tabla de talles para remeras'",
                    },
                    "main_attribute_id": {
                        "type": "string",
                        "description": "Main size attribute ID (required for create). Usually 'SIZE'. This is the primary dimension buyers will see.",
                    },
                    "measure_type": {
                        "type": "string",
                        "enum": ["BODY_MEASURE", "CLOTHING_MEASURE"],
                        "description": "Type of measurement (optional for create). BODY_MEASURE: measurements of the person's body. CLOTHING_MEASURE: measurements of the garment itself. Default: BODY_MEASURE.",
                    },
                    "attributes": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Filter attributes at chart level (required for create). GENDER attribute is required. CRITICAL: Attribute IDs are UPPERCASE_WITH_UNDERSCORES (use GENDER, not gender). Each attribute should have 'id' and 'values' array with 'id' and 'name'. Common GENDER value_ids: 339666 (Hombre), 339665 (Mujer), 339667 (Niños), 339668 (Niñas).",
                    },
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "attributes": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                }
                            },
                        },
                        "description": "Size chart rows (required for create). MUST HAVE AT LEAST 2 SIZES - single-size charts are invalid. Each row represents one size with attributes array. CRITICAL: ALL attribute IDs are UPPERCASE_WITH_UNDERSCORES (e.g., SIZE, FILTRABLE_SIZE, CHEST_CIRCUMFERENCE_FROM). Measurement values must include units (e.g., '90 cm', not '90'). Example for t-shirts: Create 4 rows for S, M, L, XL with attributes SIZE, FILTRABLE_SIZE (same as SIZE), CHEST_CIRCUMFERENCE_FROM. Use get_tech_specs action to see required attributes for other domains.",
                    },
                },
                "required": ["action"],
            },
        }
