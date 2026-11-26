"""Avisos (no errores) de la conexion y el modelo de una definicion de agente (docs/features/LLM_CONEXIONES.md).

Se piden al validar y al guardar y no bloquean nada: OpenRouter puede no responder, el catalogo publico puede no
listar un slug que si enruta, y el circuito es por conexion + modelo (app/llm/resolver.py), asi que un modelo mal
puesto ya no tumba a los demas agentes.
"""
import asyncio
from collections.abc import Callable

from sqlalchemy.orm import Session

from ..llm.openrouter import model_status
from ..models import LlmConnection

FREE_SUFFIX = ":free"


def _warning(path: str, code: str, message: str) -> dict:
    return {"path": path, "code": code, "message": message}


def llm_warnings(s: Session, definition: dict, allowed: Callable[[str], bool]) -> list[dict]:
    """Los avisos de `definition["llm"]`: `{path, code, message}` por etapa.

    - `connection_test_failed` (todos los kinds): la conexion tiene la ultima prueba fallida, con su detalle.
    - Solo `kind == "openrouter"`, con el modelo de la etapa: `model_missing`, `free_model` (tope por minuto de
      OpenRouter y datos compartidos), `model_not_found`, `model_no_endpoints` o `invalid_model`. Sin catalogo
      (`unknown`), no hay aviso.

    `allowed(client_id)` filtra las conexiones que puede ver quien pregunta (en validate, `p.can_access`; al
    guardar, el cliente del agente): la de otro cliente no da aviso ni detalle. `openai_compatible` y `anthropic`
    no tienen catalogo publico y preguntar con la clave del cliente en cada validacion seria pegarle a su endpoint
    en cada tecla. Las rutas son `def` (threadpool): la consulta async va con `asyncio.run`, como
    `llm_connections.models`.
    """
    warnings: list[dict] = []
    statuses: dict[str, str] = {}
    for i, stage in enumerate((definition.get("llm") or {}).get("stages") or []):
        connection_id = stage.get("connection")
        if not connection_id:
            continue
        row = s.get(LlmConnection, connection_id)
        if row is None or row.revoked_at is not None or not allowed(row.client_id):
            continue
        if row.last_test_ok is False:
            detail = f": {row.last_test_detail}" if row.last_test_detail else ""
            warnings.append(_warning(f"llm.stages.{i}.connection", "connection_test_failed",
                                     f"La última prueba de la conexión falló{detail}"))
        if row.kind != "openrouter":
            continue
        model = (stage.get("model") or "").strip()
        path = f"llm.stages.{i}.model"
        if not model:
            warnings.append(_warning(path, "model_missing", "Falta el modelo de la conexión"))
            continue
        if model.lower().endswith(FREE_SUFFIX):
            warnings.append(_warning(path, "free_model",
                                     "El modelo :free tiene un tope de pedidos por minuto en OpenRouter (429 con "
                                     "dos turnos a la vez) y suele exigir compartir los datos"))
        key = model.lower()
        if key not in statuses:
            statuses[key] = asyncio.run(model_status(model))
        status = statuses[key]
        if status == "not_found":
            warnings.append(_warning(path, "model_not_found", "El modelo no existe en OpenRouter"))
        elif status == "no_endpoints":
            warnings.append(_warning(path, "model_no_endpoints", "OpenRouter no lista proveedores para el modelo"))
        elif status == "invalid":
            warnings.append(_warning(path, "invalid_model", "Nombre de modelo inválido: autor/nombre, en minúsculas"))
    return warnings
