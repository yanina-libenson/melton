"""TelePagos money-transfer tool (curated platform integration).

Sends ARS to an alias or CVU/CBU. IRREVERSIBLE -> requires_confirmation=True,
so the execution loop suspends for the user's approval before this ever runs.
Credentials (username/password/env) live encrypted on the integration, entered
in the panel — never in code or .env.
"""

import asyncio
import logging
import uuid
from typing import Any

from app.models.integration import Integration
from app.tools.platforms.base_platform_tool import BasePlatformTool
from app.tools.platforms.telepagos.client import TelePagos, TelePagosError

logger = logging.getLogger(__name__)

# Safety ceiling per transfer. Above this we refuse (defensive default; could be
# made per-integration configurable later).
MAX_AMOUNT_ARS = 50_000


def _mask_cuit(cuit: str) -> str:
    """Show only the last 3 digits of a CUIT in summaries/traces."""
    digits = "".join(ch for ch in str(cuit) if ch.isdigit())
    if len(digits) <= 3:
        return "***"
    return "*" * (len(digits) - 3) + digits[-3:]


def _suggest_for_error(message: str) -> str:
    m = (message or "").lower()
    if "valid cuit" in m:
        return "El CUIT tiene el dígito verificador mal. Pedile al usuario el CUIT correcto del titular del destino."
    if "another holder" in m or "belongs to" in m:
        return "El CUIT no coincide con el titular del alias/CVU. Verificá que sea el CUIT del dueño real del destino."
    if "wrong credentials" in m or "credentials" in m:
        return "Las credenciales de TelePagos son inválidas. Revisá usuario y contraseña en la configuración de la integración."
    return "Revisá los datos del destino (alias/CVU y CUIT) y volvé a intentar."


class TelePagosTransferTool(BasePlatformTool):
    """Transfer ARS via TelePagos. Requires explicit user confirmation."""

    requires_confirmation = True

    # Overridable for tests (inject a fake client class).
    client_factory = TelePagos

    def __init__(self, tool_id: str, tool_config: dict[str, Any], integration: Integration):
        super().__init__(tool_id, tool_config, integration)
        self.name = "transfer_money"
        self.description = (
            "Transferir pesos argentinos (ARS) a un alias o CVU/CBU. "
            "Acción IRREVERSIBLE: el usuario debe confirmar antes de ejecutarse."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": "transfer_money",
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Monto en pesos argentinos (ARS), mayor a 0.",
                    },
                    "alias": {
                        "type": "string",
                        "description": "Alias de CBU/CVU del destinatario (texto con puntos, ej. 'yani.mp'). Usá alias O cvu, exactamente uno.",
                    },
                    "cvu": {
                        "type": "string",
                        "description": "CVU/CBU de 22 dígitos del destinatario. Usá alias O cvu, exactamente uno.",
                    },
                    "cuit": {
                        "type": "string",
                        "description": "CUIT/CUIL del titular del destino, 11 dígitos sin guiones. Obligatorio.",
                    },
                    "concept": {
                        "type": "string",
                        "description": "Concepto de la operación: VAR (varios, default), ALQ (alquiler), HON (honorarios), FAC (factura), etc.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detalle opcional de la transferencia.",
                    },
                },
                "required": ["amount", "cuit"],
            },
        }

    def confirmation_summary(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "accion": "Transferencia de dinero (ARS)",
            "monto": input_data.get("amount"),
            "destino": input_data.get("alias") or input_data.get("cvu"),
            "cuit": _mask_cuit(input_data.get("cuit", "")),
            "concepto": input_data.get("concept") or "VAR",
            "irreversible": True,
        }

    async def _get_credentials(self) -> dict | None:
        """Read the encrypted {username, password, env} for this integration."""
        from app.database import get_database_session
        from app.services.credential_service import CredentialService

        async for session in get_database_session():
            return await CredentialService(session).get_credentials_dict(self.integration.id)
        return None

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        amount = input_data.get("amount")
        alias = input_data.get("alias") or None
        cvu = input_data.get("cvu") or None
        cuit = input_data.get("cuit")
        concept = input_data.get("concept") or "VAR"
        description = input_data.get("description") or ""
        # reference_id is injected by the confirmation gate for idempotency.
        reference_id = input_data.get("reference_id") or uuid.uuid4().hex

        # --- validation (mirror the client's rules so the agent self-corrects) ---
        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"success": False, "error": "El monto debe ser un número mayor a 0."}
        if bool(alias) == bool(cvu):
            return {
                "success": False,
                "error": "Especificá alias O cvu (exactamente uno), no ambos ni ninguno.",
                "suggestion": "Pedile al usuario el alias o el CVU del destino.",
            }
        if not cuit:
            return {
                "success": False,
                "error": "Falta el CUIT del titular del destino (11 dígitos).",
            }
        if amount > MAX_AMOUNT_ARS:
            return {
                "success": False,
                "error": f"El monto ${amount} supera el tope de seguridad de ${MAX_AMOUNT_ARS} ARS por transferencia.",
            }

        creds = await self._get_credentials()
        if not creds or not creds.get("username") or not creds.get("password"):
            return {
                "success": False,
                "error": "No hay credenciales de TelePagos configuradas para esta integración.",
                "suggestion": "Cargá usuario y contraseña en la configuración de la integración.",
            }

        def _do_transfer() -> dict:
            client = self.client_factory(
                username=creds["username"],
                password=creds["password"],
                env=creds.get("env", "prod"),
            )
            try:
                tid = client.cashout(
                    amount=amount,
                    cuit=cuit,
                    reference_id=reference_id,
                    concept=concept,
                    description=description,
                    cvu=cvu,
                    alias=alias,
                )
                balance_after = None
                try:
                    balance_after = client.balance()
                except Exception:  # balance is best-effort, never fail the transfer on it
                    pass
                return {"ok": True, "id": tid, "balance_after": balance_after}
            except TelePagosError as e:
                return {"ok": False, "error": str(e)}
            finally:
                try:
                    client.close()
                except Exception:
                    pass

        try:
            result = await asyncio.to_thread(_do_transfer)
        except Exception as e:  # network / unexpected
            logger.error("TelePagos transfer failed (network/unexpected): %s", e)
            return {"success": False, "error": f"Error al transferir: {e}"}

        if not result["ok"]:
            return {
                "success": False,
                "error": result["error"],
                "suggestion": _suggest_for_error(result["error"]),
            }

        destino = alias or cvu
        msg = f"✅ Transferí ${amount} ARS a {destino}. ID de operación: {result['id']}."
        if result.get("balance_after") is not None:
            msg += f" Saldo actual: ${result['balance_after']}."
        return {
            "success": True,
            "message": msg,
            "id": result["id"],
            "reference_id": reference_id,
            "balance_after": result.get("balance_after"),
        }
