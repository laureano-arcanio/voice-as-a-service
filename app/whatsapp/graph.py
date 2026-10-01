"""Cliente chico de la Graph API de Meta para WhatsApp Cloud API.

Solo lo que usa el plan (docs/WHATSAPP_PLAN.md): enviar texto/plantillas,
marcar leido y registrar un numero (request_code, verify_code, register).
El token va solo en el header Authorization: no se loguea ni entra en
str(GraphError).
"""

from __future__ import annotations

import re

import httpx

DEFAULT_BASE_URL = "https://graph.facebook.com"
# Conexion corta; lectura holgada (Meta suele responder en < 2 s).
TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class GraphError(Exception):
    """Error devuelto por Meta ({"error": {...}}) o respuesta no interpretable."""

    def __init__(self, message: str, code: int | None = None,
                 subcode: int | None = None, status: int = 0):
        super().__init__(message)
        self.message = message
        self.code = code
        self.subcode = subcode
        self.status = status

    def __str__(self) -> str:
        return (f"Graph API error (http={self.status}, code={self.code}, "
                f"subcode={self.subcode}): {self.message}")


class GraphClient:
    def __init__(self, access_token: str, version: str = "v25.0",
                 base_url: str = DEFAULT_BASE_URL,
                 http: httpx.AsyncClient | None = None):
        self._token = access_token
        self.version = version
        self.base_url = base_url.rstrip("/")
        self._http = http
        self._owns_http = http is None

    def __repr__(self) -> str:
        return f"GraphClient(version={self.version!r}, base_url={self.base_url!r})"

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    async def _post(self, phone_number_id: str, path: str, payload: dict) -> dict:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=TIMEOUT)
            self._owns_http = True
        url = f"{self.base_url}/{self.version}/{phone_number_id}/{path}"
        try:
            resp = await self._http.post(
                url, json=payload, timeout=TIMEOUT,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as e:
            # No se re-lanza el original: su repr podria incluir headers.
            raise GraphError(f"fallo de red en /{path}: {type(e).__name__}") from None
        try:
            data = resp.json()
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            err = data["error"]
            raise GraphError(str(err.get("message", "")), err.get("code"),
                             err.get("error_subcode"), resp.status_code)
        if resp.status_code >= 400 or not isinstance(data, dict):
            raise GraphError("respuesta inesperada de Meta", status=resp.status_code)
        return data

    async def send_text(self, phone_number_id: str, to: str, body: str) -> dict:
        return await self._post(phone_number_id, "messages", {
            "messaging_product": "whatsapp", "to": to, "type": "text",
            "text": {"body": body},
        })

    async def send_template(self, phone_number_id: str, to: str, name: str,
                            language: str, params: list[str] | None = None) -> dict:
        template: dict = {"name": name, "language": {"code": language}}
        if params:
            template["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in params],
            }]
        return await self._post(phone_number_id, "messages", {
            "messaging_product": "whatsapp", "to": to, "type": "template",
            "template": template,
        })

    async def mark_read(self, phone_number_id: str, wamid: str) -> dict:
        return await self._post(phone_number_id, "messages", {
            "messaging_product": "whatsapp", "status": "read", "message_id": wamid,
        })

    async def request_code(self, phone_number_id: str, method: str,
                           language: str = "es") -> dict:
        method = method.upper()
        if method not in ("SMS", "VOICE"):
            raise ValueError("method debe ser SMS o VOICE")
        return await self._post(phone_number_id, "request_code",
                                {"code_method": method, "language": language})

    async def verify_code(self, phone_number_id: str, code: str) -> dict:
        return await self._post(phone_number_id, "verify_code", {"code": code})

    async def register(self, phone_number_id: str, pin: str) -> dict:
        if not re.fullmatch(r"\d{6}", str(pin)):
            raise ValueError("el pin debe tener 6 digitos")
        return await self._post(phone_number_id, "register",
                                {"messaging_product": "whatsapp", "pin": str(pin)})
