"""API falsa para probar las herramientas del cliente (tests y `make e2e-tools`, docs/features/HERRAMIENTAS.md).

Un negocio de turnos y cobranzas: exige auth en cada ruta, verifica la firma X-Atentina-Signature
cuando viene, y guarda cada pedido recibido en `RECEIVED` (y en GET /_received) para comprobar que
llego lo que el agente pidio.

    python scripts/tools/mock_api.py --port 8765

Credenciales (las mismas en los tests y en el e2e):
    Bearer:   MOCK_TOKEN
    API key:  MOCK_KEY (header X-API-Key o ?key=)
    Basic:    atentina / MOCK_PASSWORD
    OAuth2:   client_id mock-client, secret MOCK_CLIENT_SECRET -> token dinamico
    Firma:    MOCK_SIGNING_SECRET
"""
import argparse
import asyncio
import base64
import hashlib
import hmac
import secrets
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

TOKEN = "mock-token-7f3a9c21d4"
API_KEY = "mock-key-5b8e2f61aa"
USER, PASSWORD = "atentina", "mock-password-9d1c"
CLIENT_ID, CLIENT_SECRET = "mock-client", "mock-client-secret-c0ffee42"
SIGNING_SECRET = "mock-signing-secret-1a2b3c4d"

RECEIVED: list[dict] = []
_oauth_tokens: set[str] = set()
_fails: dict[str, int] = {}

TURNOS = {
    "centro": {"nombre": "Sucursal Centro", "libres": {"2026-11-05": ["10:00", "11:30", "16:00"],
                                                        "2026-11-06": ["09:00"]}},
    "norte": {"nombre": "Sucursal Norte", "libres": {"2026-11-05": ["15:00"]}},
}
DEUDORES = {"30111222": {"id": 71, "nombre": "Ana Gómez", "saldo": 15400.5, "vencimiento": "2026-11-10"},
            "27999888": {"id": 72, "nombre": "Luis Pérez", "saldo": 0, "vencimiento": None}}

app = FastAPI(title="mock-api")


async def _record(request: Request) -> dict:
    body = await request.body()
    entry = {"method": request.method, "path": request.url.path, "query": dict(request.query_params),
             "headers": {k.lower(): v for k, v in request.headers.items()}, "body": body.decode(errors="replace"),
             "signature_ok": None}
    if sig := request.headers.get("x-atentina-signature"):
        parts = dict(p.split("=", 1) for p in sig.split(",") if "=" in p)
        expected = hmac.new(SIGNING_SECRET.encode(), f"{parts.get('t')}.".encode() + body, hashlib.sha256).hexdigest()
        entry["signature_ok"] = hmac.compare_digest(expected, parts.get("v1", "")) and \
            abs(time.time() - int(parts.get("t", 0))) < 300
    RECEIVED.append(entry)
    return entry


def _bearer(request: Request, valid: set[str]) -> None:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] not in valid:
        raise HTTPException(401, "token invalido")


@app.get("/_received")
def received():
    return RECEIVED


@app.delete("/_received")
def clear():
    RECEIVED.clear()
    return {"ok": True}


@app.get("/sucursales/{sucursal}/turnos")
async def turnos(sucursal: str, request: Request, fecha: str | None = None):
    await _record(request)
    _bearer(request, {TOKEN})
    if sucursal not in TURNOS:
        raise HTTPException(404, f"No existe la sucursal {sucursal}")
    s = TURNOS[sucursal]
    libres = s["libres"].get(fecha, []) if fecha else s["libres"]
    return {"sucursal": {"id": sucursal, "nombre": s["nombre"]}, "fecha": fecha, "turnos": libres}


@app.post("/reservas")
async def reservar(request: Request):
    entry = await _record(request)
    _bearer(request, {TOKEN})
    if entry["signature_ok"] is False:
        raise HTTPException(401, "firma invalida")
    data = await request.json()
    for key in ("sucursal", "fecha", "hora", "nombre"):
        if not data.get(key):
            raise HTTPException(422, f"falta {key}")
    if data["hora"] not in TURNOS.get(data["sucursal"], {}).get("libres", {}).get(data["fecha"], []):
        raise HTTPException(409, "Ese horario no está libre")
    return {"reserva": {"id": "R-" + secrets.token_hex(3).upper(), **data}, "estado": "confirmada"}


@app.get("/deudores")
async def deudores(request: Request, dni: str):
    await _record(request)
    if request.headers.get("x-api-key") != API_KEY and request.query_params.get("key") != API_KEY:
        raise HTTPException(401, "key invalida")
    if dni not in DEUDORES:
        return {"encontrado": False}
    return {"encontrado": True, "cliente": DEUDORES[dni]}


PEDIDOS = {"123": {"estado": "en camino", "llega": "2026-11-04"}, "456": {"estado": "entregado", "llega": None}}


@app.get("/pedidos/{pedido}")
async def pedido(pedido: str, request: Request):
    await _record(request)
    _bearer(request, {TOKEN})
    if pedido not in PEDIDOS:
        raise HTTPException(404, f"No existe el pedido {pedido}")
    return {"pedido": pedido, **PEDIDOS[pedido]}


@app.get("/basic")
async def basic(request: Request):
    await _record(request)
    expected = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
    if request.headers.get("authorization") != expected:
        raise HTTPException(401, "basic invalido")
    return {"ok": True, "usuario": USER}


@app.post("/oauth/token")
async def oauth_token(request: Request):
    await _record(request)
    form = dict(await request.form())
    client_id, client_secret = form.get("client_id"), form.get("client_secret")
    if auth := request.headers.get("authorization"):
        client_id, _, client_secret = base64.b64decode(auth[6:]).decode().partition(":")
    if form.get("grant_type") != "client_credentials" or (client_id, client_secret) != (CLIENT_ID, CLIENT_SECRET):
        return JSONResponse({"error": "invalid_client"}, 401)
    token = "oauth-" + secrets.token_hex(8)
    _oauth_tokens.add(token)
    return {"access_token": token, "token_type": "Bearer", "expires_in": 3600}


@app.get("/oauth/recurso")
async def oauth_resource(request: Request):
    await _record(request)
    _bearer(request, _oauth_tokens)
    return {"ok": True, "recurso": "protegido"}


@app.post("/form")
async def form(request: Request):
    await _record(request)
    _bearer(request, {TOKEN})
    return {"recibido": dict(await request.form())}


@app.get("/lento")
async def lento(request: Request, segundos: float = 2):
    await _record(request)
    await asyncio.sleep(segundos)
    return {"ok": True}


@app.get("/falla")
async def falla(request: Request, veces: int = 1, clave: str = "x"):
    await _record(request)
    _fails[clave] = _fails.get(clave, 0) + 1
    if _fails[clave] <= veces:
        return JSONResponse({"error": "temporal"}, 503)
    return {"ok": True, "intentos": _fails[clave]}


@app.get("/redirige")
async def redirige(request: Request):
    await _record(request)
    return RedirectResponse("https://example.com/", 302)


@app.get("/eco")
async def eco(request: Request):
    """Devuelve los headers que recibio: para ver que los secretos se tachan en la respuesta."""
    await _record(request)
    return {"headers": {k: v for k, v in request.headers.items() if k.startswith("x-") or k == "authorization"}}


def main() -> None:
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
