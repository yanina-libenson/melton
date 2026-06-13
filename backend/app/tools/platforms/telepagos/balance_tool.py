"""TelePagos balance tool (curated platform integration).

Read-only: returns the available account balance in ARS. No confirmation needed
(it moves no money). Credentials live encrypted on the integration, same as the
transfer tool.
"""

import asyncio
import logging
from typing import Any

from app.models.integration import Integration
from app.tools.platforms.base_platform_tool import BasePlatformTool
from app.tools.platforms.telepagos.client import TelePagos, TelePagosError
from app.utils.money import format_ars

logger = logging.getLogger(__name__)


class TelePagosBalanceTool(BasePlatformTool):
    """Consultar el saldo disponible de la cuenta de TelePagos."""

    # Overridable for tests (inject a fake client class).
    client_factory = TelePagos

    def __init__(self, tool_id: str, tool_config: dict[str, Any], integration: Integration):
        super().__init__(tool_id, tool_config, integration)
        self.name = "get_balance"
        self.description = "Consultar el saldo disponible de la cuenta de TelePagos (en pesos ARS)."

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "get_balance",
            "description": self.description,
            "input_schema": {"type": "object", "properties": {}, "required": []},
        }

    async def _get_credentials(self) -> dict | None:
        """Read the encrypted {username, password, env} for this integration."""
        from app.database import get_database_session
        from app.services.credential_service import CredentialService

        async for session in get_database_session():
            return await CredentialService(session).get_credentials_dict(self.integration.id)
        return None

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        creds = await self._get_credentials()
        if not creds or not creds.get("username") or not creds.get("password"):
            return {
                "success": False,
                "error": "No hay credenciales de TelePagos configuradas para esta integración.",
                "suggestion": "Cargá usuario y contraseña en la configuración de la integración.",
            }

        def _do_balance() -> dict:
            client = self.client_factory(
                username=creds["username"],
                password=creds["password"],
                env=creds.get("env", "prod"),
            )
            try:
                return {"ok": True, "balance": client.balance()}
            except TelePagosError as e:
                return {"ok": False, "error": str(e)}
            finally:
                try:
                    client.close()
                except Exception:
                    pass

        try:
            result = await asyncio.to_thread(_do_balance)
        except Exception as e:  # network / unexpected
            logger.error("TelePagos balance failed (network/unexpected): %s", e)
            return {"success": False, "error": f"Error al consultar el saldo: {e}"}

        if not result["ok"]:
            return {"success": False, "error": result["error"]}

        balance = result["balance"]
        return {
            "success": True,
            "message": f"Saldo disponible: {format_ars(balance)}.",
            "balance": balance,
        }
