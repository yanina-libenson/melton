"""Generic per-user persistent memory tools, auto-included on every agent run
for an authenticated operator.

These are NOT payment-specific: they let the agent remember and recall labeled
records grouped into named collections (e.g. "contactos" for payees, but also
preferences, notes, etc.). Each tool carries the operator's user_id + the
agent_id so the store is scoped to (user, agent, collection) and persists across
conversations. Tools open their own DB session (like platform/builtin tools).
"""

import uuid
from typing import Any

from app.tools.base_tool import BaseTool

# One spec per tool. The LLM sees `name`/`description`/`input_schema`; descriptions
# are in Spanish to match the platform's audience.
MEMORY_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "operation": "remember",
        "name": "remember",
        "description": (
            "Guardá un dato en la memoria persistente del usuario para reusarlo en "
            "futuras conversaciones (no se pierde al terminar el chat). Ejemplo: "
            "agendar un destinatario de pago. 'collection' agrupa datos del mismo "
            "tipo (ej. 'contactos'); 'label' es el nombre para referenciarlo (ej. "
            "'juan perez'); 'data' es un objeto con los campos (ej. {\"alias\": "
            "\"juan.perez\", \"cuit\": \"20XXXXXXXXX\"}). Si el label ya existe en esa "
            "colección, se actualiza."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Colección donde agrupar el dato, ej. 'contactos'.",
                },
                "label": {
                    "type": "string",
                    "description": "Nombre legible para referenciar el dato, ej. 'juan perez'.",
                },
                "data": {
                    "type": "object",
                    "description": "Objeto con los campos a guardar, ej. {\"alias\": \"juan.perez\", \"cuit\": \"20XXXXXXXXX\"}.",
                },
            },
            "required": ["collection", "label", "data"],
        },
    },
    {
        "operation": "recall",
        "name": "recall",
        "description": (
            "Buscá datos que el usuario guardó antes (ej. destinatarios agendados), "
            "por nombre aproximado. IMPORTANTE: siempre que el usuario se refiera a "
            "alguien o algo por un NOMBRE en vez de por sus datos completos —por "
            "ejemplo 'transferí 1 peso a juan'— tu PRIMER paso, sin avisar ni "
            "preguntar, debe ser llamar recall(collection='contactos', query='juan') "
            "para ver si está agendado. Recién pedile los datos al usuario (alias/CVU/"
            "CUIT) si recall NO devuelve resultados. Devuelve los registros que "
            "coinciden (label + data)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Colección donde buscar, ej. 'contactos'.",
                },
                "query": {
                    "type": "string",
                    "description": "Nombre o texto aproximado a buscar, ej. 'juan'.",
                },
            },
            "required": ["collection", "query"],
        },
    },
    {
        "operation": "list_memory",
        "name": "list_memory",
        "description": (
            "Listá todos los datos guardados en una colección (ej. todos los "
            "'contactos' agendados del usuario)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Colección a listar, ej. 'contactos'.",
                },
            },
            "required": ["collection"],
        },
    },
    {
        "operation": "forget",
        "name": "forget",
        "description": "Borrá un dato guardado por su 'label' en una colección.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Colección donde está el dato, ej. 'contactos'.",
                },
                "label": {
                    "type": "string",
                    "description": "Nombre del dato a borrar, ej. 'juan perez'.",
                },
            },
            "required": ["collection", "label"],
        },
    },
]


def _record_view(record) -> dict[str, Any]:
    return {"label": record.label, "data": record.data}


class MemoryTool(BaseTool):
    """One persistent-memory operation, scoped to a (user, agent) at construction."""

    def __init__(
        self,
        *,
        operation: str,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        agent_id: uuid.UUID | None,
    ):
        super().__init__(tool_id=f"memory_{operation}", config={"name": name, "description": description})
        self.operation = operation
        self._input_schema = input_schema
        self.user_id = user_id
        self.organization_id = organization_id
        self.agent_id = agent_id

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self._input_schema,
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from app.database import async_session_maker
        from app.services.memory_service import MemoryService

        collection = (input_data.get("collection") or "").strip()
        if not collection:
            return {"success": False, "error": "Falta 'collection'."}

        scope = {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "agent_id": self.agent_id,
            "collection": collection,
        }

        try:
            async with async_session_maker() as session:
                svc = MemoryService(session)

                if self.operation == "remember":
                    label = (input_data.get("label") or "").strip()
                    data = input_data.get("data") or {}
                    if not label:
                        return {"success": False, "error": "Falta 'label'."}
                    if not isinstance(data, dict):
                        return {"success": False, "error": "'data' debe ser un objeto."}
                    record = await svc.remember(label=label, data=data, **scope)
                    await session.commit()
                    return {
                        "success": True,
                        "message": f"Guardé «{label}» en {collection}.",
                        "record": _record_view(record),
                    }

                if self.operation == "recall":
                    query = input_data.get("query") or ""
                    rows = await svc.recall(query=query, **scope)
                    return {
                        "success": True,
                        "count": len(rows),
                        "results": [_record_view(r) for r in rows],
                    }

                if self.operation == "list_memory":
                    rows = await svc.list_all(**scope)
                    return {
                        "success": True,
                        "count": len(rows),
                        "results": [_record_view(r) for r in rows],
                    }

                if self.operation == "forget":
                    label = (input_data.get("label") or "").strip()
                    if not label:
                        return {"success": False, "error": "Falta 'label'."}
                    removed = await svc.forget(label=label, **scope)
                    await session.commit()
                    if removed:
                        return {"success": True, "message": f"Borré «{label}» de {collection}."}
                    return {"success": False, "error": f"No encontré «{label}» en {collection}."}

                return {"success": False, "error": f"Operación desconocida: {self.operation}"}
        except Exception as e:  # noqa: BLE001 — surface as tool error, never crash the loop
            return {"success": False, "error": str(e)}


def build_memory_tools(
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    agent_id: uuid.UUID | None,
) -> list[MemoryTool]:
    """Instantiate the memory tools bound to a (user, agent) scope."""
    return [
        MemoryTool(
            operation=spec["operation"],
            name=spec["name"],
            description=spec["description"],
            input_schema=spec["input_schema"],
            user_id=user_id,
            organization_id=organization_id,
            agent_id=agent_id,
        )
        for spec in MEMORY_TOOL_SPECS
    ]


def memory_tool_schemas() -> list[dict[str, Any]]:
    """LLM-facing schemas for the memory tools (used to build the prompt)."""
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": spec["input_schema"],
        }
        for spec in MEMORY_TOOL_SPECS
    ]
