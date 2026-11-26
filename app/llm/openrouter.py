"""Enrutado a proveedores especificos de OpenRouter (docs/features/LLM_CONEXIONES.md, "Modelo de datos").

Una etapa del agente (LlmStage, app/conversation/models.py) fija que proveedores de OpenRouter
pueden atenderla: `only` son los tags, `allow_fallbacks` deja que OpenRouter elija otros si los
fijados fallan y `require_parameters` exige proveedores con todo lo que pide el pedido. Exclusivo
de conexiones `kind=openrouter`: al guardar un agente, cualquier otra conexion se rechaza
(app/services/agents.py, _check_llm). `provider_body` arma el dict que viaja en cada pedido.

Modulo hoja: no importa resolver ni conversation.models (ellos lo importan a el).
"""
import re
import time
from typing import Literal

import httpx
from pydantic import BaseModel, Field, field_validator

from ..services.errors import Invalid

# Tag de proveedor: minusculas, numeros y guiones, 0 a 3 barras
# (baseten, openai/flex, deepinfra/fp8/priority, google-vertex/global/priority).
TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}(/[a-z0-9][a-z0-9-]{0,63}){0,3}$")

# URL publica de los endpoints de un modelo: el catalogo de proveedores de la UI (GET /llm/openrouter-providers).
ENDPOINTS_URL = "https://openrouter.ai/api/v1/models/{model}/endpoints"

# Slug de modelo (autor/nombre): minusculas, numeros, . - _ y : en el nombre (los :free, :extended).
# Validarlo antes de armar la URL cierra el path traversal (el host es fijo y no lleva query).
MODEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}/[a-z0-9][a-z0-9._:-]{0,127}$")

CATALOG_TTL = 300.0
CATALOG_TIMEOUT = 5.0
_catalog: dict[str, tuple[float, list[dict]]] = {}
# 404 por modelo, con el mismo TTL: validar pega en cada tecla y un slug mal puesto no se aprende solo.
_missing: dict[str, float] = {}


class OpenRouterProvider(BaseModel):
    """Proveedores de OpenRouter que atienden una etapa del agente. Solo vale en una etapa con
    conexion kind=openrouter (services/agents._check_llm lo exige al guardar); con otro proveedor,
    el campo no existe y el pedido no lo lleva."""
    # Tags de proveedores; vacio = sin enrutado (LlmStage lo normaliza a None).
    only: list[str] = Field(default_factory=list, max_length=10)
    # Si los fijados fallan, OpenRouter puede elegir otros.
    allow_fallbacks: bool = True
    # Solo proveedores con todo lo que pide el pedido (json_schema, tools).
    require_parameters: bool = True

    @field_validator("only")
    @classmethod
    def _tags(cls, tags: list[str]) -> list[str]:
        out: list[str] = []
        for raw in tags:
            tag = raw.strip().lower()
            if not TAG_PATTERN.fullmatch(tag):
                raise ValueError(f"{raw!r} no es un tag de proveedor de OpenRouter")
            if tag not in out:
                out.append(tag)
        return out


def provider_body(provider: OpenRouterProvider | None) -> dict | None:
    """El `provider` que va en extra_body del pedido: None si no hay o no fija tags (el default)."""
    if provider is None or not provider.only:
        return None
    return {"only": provider.only, "allow_fallbacks": provider.allow_fallbacks,
            "require_parameters": provider.require_parameters}


async def provider_catalog(model: str) -> list[dict]:
    """Los proveedores de OpenRouter que atienden un modelo, para el editor del agente
    (GET /api/v1/llm/openrouter-providers): [{tag, provider_name, quantization, supports_json_schema,
    supports_tools}], deduplicado por tag y ordenado por proveedor. `tag` es lo que va en provider.only;
    supports_json_schema mira structured_outputs (no response_format, que tambien cubre json_object)
    y supports_tools, tools. Se pide a la URL publica sin la clave del cliente y con cache de
    CATALOG_TTL por modelo (los 404 incluidos: la validacion del editor pega en cada tecla). Modelo
    invalido, de red caido o inexistente -> Invalid: la UI deja escribir el tag a mano y OpenRouter
    termina de validarlo en el pedido."""
    model = model.strip().lower()
    if not MODEL_PATTERN.fullmatch(model):
        raise Invalid("model: nombre de modelo de OpenRouter (autor/nombre, p. ej. "
                      "deepseek/deepseek-v4.1-flash-1017)", "invalid_model")
    hit = _catalog.get(model)
    if hit and time.monotonic() - hit[0] < CATALOG_TTL:
        return hit[1]
    miss = _missing.get(model)
    if miss and time.monotonic() - miss < CATALOG_TTL:
        raise Invalid(f"El modelo {model!r} no existe en OpenRouter", "model_not_found")
    try:
        async with httpx.AsyncClient(timeout=CATALOG_TIMEOUT) as client:
            r = await client.get(ENDPOINTS_URL.format(model=model))
    except httpx.HTTPError as e:
        raise Invalid(f"No se pudo leer el catalogo de OpenRouter: {type(e).__name__}",
                      "catalog_unreachable") from None
    if r.status_code == 404:
        _missing[model] = time.monotonic()
        raise Invalid(f"El modelo {model!r} no existe en OpenRouter", "model_not_found")
    if r.status_code != 200:
        raise Invalid(f"No se pudo leer el catalogo de OpenRouter (HTTP {r.status_code})",
                      "catalog_unreachable")
    try:
        endpoints = (r.json().get("data") or {}).get("endpoints") or []
    except ValueError:
        raise Invalid("El catalogo de OpenRouter no respondio JSON", "catalog_unreachable") from None
    rows: dict[str, dict] = {}
    for ep in endpoints if isinstance(endpoints, list) else []:
        tag = ep.get("tag") if isinstance(ep, dict) else None
        if not isinstance(tag, str) or not tag:
            continue
        params = ep.get("supported_parameters") or []
        # Deduplicado por tag: varios endpoints del mismo proveedor (tiers) no agregan filas.
        rows.setdefault(tag, {"tag": tag, "provider_name": ep.get("provider_name") or tag,
                               "quantization": ep.get("quantization"),
                               "supports_json_schema": "structured_outputs" in params,
                               "supports_tools": "tools" in params})
    catalog = sorted(rows.values(), key=lambda p: (p["provider_name"], p["tag"]))
    _catalog[model] = (time.monotonic(), catalog)
    return catalog


async def model_status(model: str) -> Literal["ok", "not_found", "no_endpoints", "invalid", "unknown"]:
    """Si un modelo de OpenRouter existe y tiene proveedores, sin la clave del cliente (avisos del editor,
    app/services/llm_warnings.py): "ok", "not_found", "no_endpoints" (el catalogo responde una lista vacia),
    "invalid" (no cumple MODEL_PATTERN) o "unknown" (catalogo caido: sin aviso). Con un sufijo (:free, :nitro,
    :batch) prueba el slug base antes de decir que no existe o que no tiene proveedores."""
    slug = model.strip().lower()
    rows: list[dict] | None = None
    try:
        rows = await provider_catalog(slug)
    except Invalid as e:
        if e.code == "invalid_model":
            return "invalid"
        if e.code != "model_not_found":
            return "unknown"
    if (rows is None or not rows) and ":" in slug:
        # Un :free/:nitro/:batch se sirve con los endpoints del slug base (el sufijo da 404 o una lista vacia).
        try:
            rows = await provider_catalog(slug.split(":", 1)[0])
        except Invalid as retry:
            return "unknown" if retry.code == "catalog_unreachable" else "not_found"
    if rows is None:
        return "not_found"
    return "ok" if rows else "no_endpoints"
