"""Cliente chico de la Graph API de Meta para WhatsApp Cloud API.

Solo lo que usa el plan (docs/WHATSAPP_PLAN.md): enviar texto/plantillas/audio,
marcar leido, bajar y subir media, registrar un numero (request_code,
verify_code, register) y, para Embedded Signup (fase 2), cambiar el codigo por el
token del cliente, suscribir la app a su WABA, leer sus numeros y sus plantillas.
El token va solo en el header Authorization: no se loguea ni entra en
str(GraphError). Tampoco el app secret ni el codigo del intercambio.
"""

from __future__ import annotations

import json as json_module
import logging
import re

import httpx

DEFAULT_BASE_URL = "https://graph.facebook.com"
# Conexion corta; lectura holgada (Meta suele responder en < 2 s).
TIMEOUT = httpx.Timeout(15.0, connect=5.0)
# Bajar o subir un audio (hasta WA_AUDIO_MAX_BYTES): mas holgado.
MEDIA_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
# Dominios de Meta a los que se manda el token para bajar un media (ademas del host de
# base_url). La url de get_media es de lookaside.fbsbx.com segun los ejemplos de Meta;
# los demas, por las dudas. Una url de otro host da GraphError (se loguea el host).
MEDIA_HOSTS = ("fbsbx.com", "facebook.com", "fbcdn.net", "whatsapp.net", "whatsapp.com")
# Redirecciones que se siguen al bajar un media, cada una re-validada (https y host de Meta):
# el Bearer no sale nunca a otro host.
MAX_REDIRECTS = 3
# Lo que se lee de una respuesta de error de la descarga (Meta manda un JSON chico).
MAX_ERROR_BYTES = 64 * 1024


_SECRET_QUERY_RE = re.compile(r"((?:client_secret|code|access_token)=)[^&\s\"']*")


class RedactSecrets(logging.Filter):
    """httpx loguea la URL completa en INFO: tapa client_secret y code del intercambio."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(_SECRET_QUERY_RE.sub(r"\1***", str(a)) if isinstance(a, (str, httpx.URL)) else a
                                for a in record.args)
        return True


if not any(isinstance(f, RedactSecrets) for f in logging.getLogger("httpx").filters):
    logging.getLogger("httpx").addFilter(RedactSecrets())


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

    @property
    def is_auth_error(self) -> bool:
        """Token vencido, invalido o revocado: la cuenta queda desconectada. El 10
        (permiso no otorgado) no cuenta: mientras el App Review no este aprobado daria
        falsos positivos."""
        return self.code == 190 or self.status == 401


class MediaTooLarge(GraphError):
    """El media pesa mas que el tope (WA_AUDIO_MAX_BYTES): no se baja entero."""


def _json_or_error(resp: httpx.Response) -> dict:
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


async def _read_capped(resp: httpx.Response, limit: int) -> bytes:
    buf = bytearray()
    async for chunk in resp.aiter_bytes():
        buf += chunk
        if len(buf) >= limit:
            break
    return bytes(buf[:limit])


def _stream_error(resp: httpx.Response, raw: bytes) -> GraphError:
    """GraphError de una respuesta de error leida en parte (stream)."""
    try:
        data = json_module.loads(raw)
    except ValueError:
        data = None
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        err = data["error"]
        return GraphError(str(err.get("message", ""))[:500], err.get("code"), err.get("error_subcode"),
                          resp.status_code)
    return GraphError("respuesta inesperada de Meta", status=resp.status_code)


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

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=TIMEOUT)
            self._owns_http = True
        return self._http

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def _url(self, *parts: str) -> str:
        return "/".join([self.base_url, self.version, *parts])

    async def _request(self, method: str, url: str, *, json: dict | None = None, data: dict | None = None,
                       files: dict | None = None, params: dict | None = None,
                       timeout: httpx.Timeout = TIMEOUT) -> dict:
        """Pedido a la Graph API que devuelve JSON. El error no lleva el token."""
        what = url.rsplit("/", 1)[-1]
        try:
            resp = await self._client().request(method, url, json=json, data=data, files=files,
                                                params=params, timeout=timeout, headers=self._auth())
        except httpx.HTTPError as e:
            # No se re-lanza el original: su repr podria incluir headers.
            raise GraphError(f"fallo de red en /{what}: {type(e).__name__}") from None
        return _json_or_error(resp)

    async def _post(self, phone_number_id: str, path: str, payload: dict) -> dict:
        return await self._request("POST", f"{self.base_url}/{self.version}/{phone_number_id}/{path}",
                                   json=payload)

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

    # --- Media (audios). La url de get_media vence a los 5 min y se baja con el mismo
    # Bearer (developers.facebook.com/docs/whatsapp/cloud-api/reference/media). ---

    async def get_media(self, media_id: str, phone_number_id: str | None = None) -> dict:
        """{url, mime_type, sha256, file_size, id} de un media entrante."""
        params = {"phone_number_id": phone_number_id} if phone_number_id else None
        return await self._request("GET", f"{self.base_url}/{self.version}/{media_id}", params=params)

    async def download_media(self, url: str, max_bytes: int) -> bytes:
        """Bytes del media (url de get_media). MediaTooLarge si pasa max_bytes: corta la
        descarga ahi, sin bajarlo entero. Solo https y a un host de Meta (MEDIA_HOSTS): la
        descarga lleva el Bearer. Las redirecciones se siguen a mano, validando cada salto."""
        try:
            for _ in range(MAX_REDIRECTS + 1):
                self._check_media_url(url)
                async with self._client().stream("GET", url, headers=self._auth(), timeout=MEDIA_TIMEOUT,
                                                 follow_redirects=False) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location")
                        if not location:
                            raise GraphError("redireccion sin destino", status=resp.status_code)
                        url = str(resp.url.join(location))
                        continue
                    if resp.status_code >= 400:
                        raise _stream_error(resp, await _read_capped(resp, MAX_ERROR_BYTES))
                    size = resp.headers.get("content-length")
                    if size and size.isdigit() and int(size) > max_bytes:
                        raise MediaTooLarge(f"media de {size} bytes, tope {max_bytes}", status=resp.status_code)
                    buf = bytearray()
                    async for chunk in resp.aiter_bytes():
                        buf += chunk
                        if len(buf) > max_bytes:
                            raise MediaTooLarge(f"media de mas de {max_bytes} bytes", status=resp.status_code)
                    return bytes(buf)
            raise GraphError(f"media con mas de {MAX_REDIRECTS} redirecciones")
        except httpx.HTTPError as e:
            raise GraphError(f"fallo de red en /media: {type(e).__name__}") from None

    def _check_media_url(self, url: str) -> None:
        try:
            parsed = httpx.URL(url)
        except (httpx.InvalidURL, TypeError):
            raise GraphError("url de media invalida") from None
        host = (parsed.host or "").lower()
        meta = host == httpx.URL(self.base_url).host or any(
            host == d or host.endswith("." + d) for d in MEDIA_HOSTS)
        if parsed.scheme != "https" or not meta:
            raise GraphError(f"url de media fuera de Meta: {parsed.scheme}://{host}")

    async def upload_media(self, phone_number_id: str, data: bytes, mime_type: str = "audio/ogg",
                           filename: str = "respuesta.ogg") -> str:
        """Sube un archivo y devuelve su media id (para send_audio)."""
        resp = await self._request(
            "POST", f"{self.base_url}/{self.version}/{phone_number_id}/media",
            data={"messaging_product": "whatsapp", "type": mime_type},
            files={"file": (filename, data, mime_type)}, timeout=MEDIA_TIMEOUT)
        media_id = resp.get("id")
        if not media_id:
            raise GraphError("subida de media sin id")
        return str(media_id)

    async def send_audio(self, phone_number_id: str, to: str, media_id: str, voice: bool = True) -> dict:
        """voice=True: nota de voz (Meta: "Voice messages must be Ogg files encoded with
        the OPUS codec"); con menos de 512 KB se muestra con play, si no con descarga."""
        audio: dict = {"id": media_id}
        if voice:
            audio["voice"] = True
        return await self._post(phone_number_id, "messages", {
            "messaging_product": "whatsapp", "to": to, "type": "audio", "audio": audio,
        })

    # --- Embedded Signup y administracion de la WABA del cliente (fase 2). Ver
    # docs/WHATSAPP_PLAN.md 3.3: lo confirmado y lo no confirmado de cada respuesta. ---

    async def exchange_code(self, app_id: str, app_secret: str, code: str) -> str:
        """Codigo del popup (vence a los 30 s) -> business token del cliente. Sin token
        propio: el cliente se crea con GraphClient(""). El secret no va al log (RedactSecrets)
        ni al error."""
        data = await self._request("GET", self._url("oauth", "access_token"),
                                   params={"client_id": app_id, "client_secret": app_secret, "code": code})
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            raise GraphError("intercambio sin access_token")
        return token

    async def subscribe_app(self, waba_id: str) -> dict:
        """Suscribe nuestra app a los webhooks de la WABA: sin esto no llega ningun mensaje."""
        return await self._request("POST", self._url(waba_id, "subscribed_apps"))

    async def smb_app_data(self, phone_number_id: str, sync_type: str) -> dict:
        """Coexistencia: pide la sincronizacion de contactos (smb_app_state_sync) o del
        historial (history) de la app de WhatsApp Business. Meta da 24 h desde el alta."""
        return await self._post(phone_number_id, "smb_app_data",
                                {"messaging_product": "whatsapp", "sync_type": sync_type})

    async def list_phone_numbers(self, waba_id: str) -> list[dict]:
        data = await self._request("GET", self._url(waba_id, "phone_numbers"),
                                   params={"fields": "id,display_phone_number,verified_name,quality_rating"})
        return [n for n in data.get("data") or [] if isinstance(n, dict)]

    async def get_phone_number(self, phone_number_id: str,
                               fields: str = "id,display_phone_number,verified_name,quality_rating") -> dict:
        return await self._request("GET", self._url(phone_number_id), params={"fields": fields})

    async def list_templates(self, waba_id: str, limit: int = 100) -> list[dict]:
        data = await self._request("GET", self._url(waba_id, "message_templates"), params={
            "fields": "id,name,language,category,status,rejected_reason,components", "limit": limit})
        return [t for t in data.get("data") or [] if isinstance(t, dict)]

    async def create_template(self, waba_id: str, payload: dict) -> dict:
        """{id, status, category}. Meta la revisa: queda PENDING y avisa por
        message_template_status_update."""
        return await self._request("POST", self._url(waba_id, "message_templates"), json=payload)
