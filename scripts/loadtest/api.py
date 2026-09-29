"""Acceso a la API de la app (/api/v1) desde el loadtest, el test de capacidad y el
monitor: autenticacion con API key y agentes por slug.

Autenticacion: VAAS_API_KEY (en .env o el entorno), una API key del cliente con
los agentes a probar. Para el cliente interno (sin limites, creado por `make migrate`):
    make api-key CLIENT=interno NAME=loadtest   -> copiar la clave a VAAS_API_KEY
Los perfiles y --workflow nombran al agente por su slug (el de la plantilla).
"""
import os

import httpx

API = "/api/v1"


def headers() -> dict[str, str]:
    key = os.getenv("VAAS_API_KEY", "").strip()
    if not key:
        raise SystemExit("falta VAAS_API_KEY (API key del cliente de prueba): make api-key CLIENT=interno NAME=loadtest")
    return {"Authorization": f"Bearer {key}"}


def client(**kwargs) -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=headers(), **kwargs)


def agents(base_url: str) -> dict[str, dict]:
    """Agentes del cliente de la API key, por slug."""
    r = httpx.get(f"{base_url}{API}/agents", headers=headers(), timeout=10).raise_for_status()
    return {a["slug"]: a for a in r.json()}


_ids: dict[str, str] = {}


async def agent_id(http: httpx.AsyncClient, base_url: str, slug: str) -> str:
    """id del agente `slug`, cacheado por proceso (el loadtest reparte callers en procesos)."""
    if slug not in _ids:
        r = (await http.get(f"{base_url}{API}/agents")).raise_for_status()
        _ids.update({a["slug"]: a["id"] for a in r.json()})
    if slug not in _ids:
        raise SystemExit(f"agente {slug!r} inexistente para esta API key")
    return _ids[slug]
