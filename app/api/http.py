"""Middlewares ASGI de seguridad para la app publicada (app.atentina.com.ar, sin Access).

- BodyLimitMiddleware: tope de cuerpo en /api (413), por Content-Length y por stream.
- CsrfMiddleware: un pedido no seguro con la cookie de sesion y sin Authorization tiene
  que venir del mismo Host o de APP_ORIGINS. SameSite=Strict no alcanza: la landing y los
  otros subdominios de atentina.com.ar son "same-site" con app.
- HttpsRedirectMiddleware: por el tunel, un pedido por http:// va a https:// (308). Sin
  esto, si la zona no tiene "Always Use HTTPS", el login viajaria en claro hasta Cloudflare.
- SecurityHeadersMiddleware: HSTS (solo por HTTPS), CSP con el hash de los <script>
  inline de index.html, COOP, Referrer-Policy, Permissions-Policy, nosniff y XFO.
"""
import base64
import hashlib
import json
import re
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ..config import settings
from .deps import SESSION_COOKIE, _peer_is_trusted, request_is_https

UNSAFE_METHODS_EXEMPT = {"GET", "HEAD", "OPTIONS"}
# El unico pedido de /api que sube archivos: audio para transcribir (el multipart agrega algo al tamaño).
UPLOAD_PATH = "/api/v1/inference/audio/transcriptions"
UPLOAD_OVERHEAD_BYTES = 64 * 1024


def _is_api(scope: Scope) -> bool:
    return scope["type"] == "http" and scope["path"].startswith("/api/")


async def _send_json(send: Send, status: int, body: dict) -> None:
    data = json.dumps(body, ensure_ascii=False).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(data)).encode())]})
    await send({"type": "http.response.body", "body": data})


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not _is_api(scope):
            return await self.app(scope, receive, send)
        limit = settings.api_max_body_bytes
        if scope["path"] == UPLOAD_PATH:
            limit = settings.inference_stt_max_bytes + UPLOAD_OVERHEAD_BYTES   # audio de la API de STT
        too_big = {"detail": "Pedido demasiado grande", "code": "payload_too_large", "errors": []}
        length = dict(scope["headers"]).get(b"content-length")
        if length is not None:
            try:
                declared = int(length)
            except ValueError:
                return await _send_json(send, 400, {"detail": "Content-Length invalido", "code": "bad_request",
                                                    "errors": []})
            if declared > limit:
                return await _send_json(send, 413, too_big)
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # FastAPI deja pasar el HTTPException que salta al leer el cuerpo.
                    raise HTTPException(413, too_big["detail"])
            return message

        await self.app(scope, limited_receive, send)


def _origin_ok(request: Request, origin: str) -> bool:
    origin = origin.rstrip("/").lower()
    host = request.headers.get("host", "").lower()
    allowed = {o.strip().rstrip("/").lower() for o in settings.app_origins.split(",") if o.strip()}
    if host:
        allowed.add(f"https://{host}")
        allowed.add(f"{'https' if request_is_https(request) else 'http'}://{host}")
    return origin in allowed


class CsrfMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not _is_api(scope) or scope["method"] in UNSAFE_METHODS_EXEMPT:
            return await self.app(scope, receive, send)
        request = Request(scope)
        # Solo importa si el navegador manda la cookie sola: con Authorization (API key o
        # token) no hay CSRF posible.
        if "authorization" in request.headers or not _has_session_cookie(request):
            return await self.app(scope, receive, send)
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site", "").lower()
        if origin is not None:
            ok = _origin_ok(request, origin)
        else:
            # Sin Origin: un navegador viejo o algo que no es un navegador (curl, scripts).
            ok = fetch_site not in ("cross-site", "same-site")
        if not ok:
            return await _send_json(send, 403, {"detail": "Origen no permitido", "code": "csrf", "errors": []})
        await self.app(scope, receive, send)


def _has_session_cookie(request: Request) -> bool:
    # El mismo parser que lee la cookie en get_principal: si aca no esta, alla tampoco.
    return SESSION_COOKIE in request.cookies


_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
_csp_cache: dict = {}


def inline_script_hashes(index: Path) -> list[str]:
    """'sha256-...' de cada <script> inline de index.html (se recalcula si cambia el build)."""
    try:
        mtime = index.stat().st_mtime_ns
    except OSError:
        return []
    cached = _csp_cache.get(index)
    if cached and cached[0] == mtime:
        return cached[1]
    html = index.read_text(encoding="utf-8")
    hashes = [f"'sha256-{base64.b64encode(hashlib.sha256(m.encode()).digest()).decode()}'"
              for m in _INLINE_SCRIPT.findall(html) if m.strip()]
    _csp_cache[index] = (mtime, hashes)
    return hashes


# Pago con tarjeta (Card Payment Brick de Mercado Pago): solo en las paginas que lo cargan, que se abren
# con navegacion completa (la CSP es la del documento). Los campos de la tarjeta son iframes de MP.
MP_PAGES = ("/plan/pagar",)
MP_SCRIPTS = "https://sdk.mercadopago.com https://http2.mlstatic.com"
# mercadolivre.com: la huella del dispositivo (antifraude) que carga el SDK de MP.
MP_HOSTS = ("https://*.mercadopago.com https://*.mercadopago.com.ar https://*.mercadolibre.com "
            "https://*.mercadolibre.com.ar https://*.mercadolivre.com https://*.mlstatic.com")


def content_security_policy(mercadopago: bool = False) -> str:
    """CSP de la UI: sus assets, los scripts inline de index.html (por hash; hoy no tiene) y el SDK de Facebook
    (Embedded Signup de WhatsApp: script en connect.facebook.net, popup e iframes en facebook.com). Con
    `mercadopago`, ademas el SDK y los iframes de MP (MP_PAGES)."""
    mp_hosts = f" {MP_HOSTS}" if mercadopago else ""
    scripts = " ".join(["'self'", *inline_script_hashes(settings.web_dist_dir / "index.html"),
                        "https://connect.facebook.net", *([MP_SCRIPTS] if mercadopago else [])])
    return "; ".join([
        "default-src 'self'",
        f"script-src {scripts}",
        f"style-src 'self' 'unsafe-inline'{mp_hosts}",   # Mantine pone estilos inline
        f"img-src 'self' data: blob: https://*.facebook.com https://*.fbcdn.net https://*.fbsbx.com{mp_hosts}",
        f"font-src 'self' data:{mp_hosts}",
        f"connect-src 'self' https://*.facebook.com https://*.facebook.net{mp_hosts}",
        f"frame-src https://*.facebook.com https://*.facebook.net{mp_hosts}",
        "media-src 'self' blob:",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])


class HttpsRedirectMiddleware:
    """Solo con X-Forwarded-Proto: http de un proxy de confianza (Cloudflare). El acceso
    directo (http://localhost:8011, la LAN) no trae ese header y no cambia."""
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = Request(scope)
        host = request.headers.get("host", "")
        if (request.headers.get("x-forwarded-proto", "").lower() != "http" or not host
                or not _peer_is_trusted(request)):
            return await self.app(scope, receive, send)
        query = scope.get("query_string", b"").decode("latin-1")
        location = f"https://{host}{scope.get('raw_path', scope['path'].encode()).decode('latin-1')}"
        location += f"?{query}" if query else ""
        await send({"type": "http.response.start", "status": 308,
                    "headers": [(b"location", location.encode("latin-1")), (b"content-length", b"0")]})
        await send({"type": "http.response.body", "body": b""})


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        https = request_is_https(Request(scope))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}

                def add(name: str, value: str) -> None:
                    if name.encode() not in present:
                        headers.append((name.encode(), value.encode()))

                add("x-content-type-options", "nosniff")
                add("x-frame-options", "DENY")
                # Con origen al ir a otro sitio (facebook.com), nada de paths.
                add("referrer-policy", "strict-origin-when-cross-origin")
                # same-origin cortaria el postMessage del popup de Embedded Signup.
                add("cross-origin-opener-policy", "same-origin-allow-popups")
                add("permissions-policy", "camera=(), microphone=(), geolocation=(), payment=()")
                if b"content-security-policy" not in present and b"content-security-policy-report-only" not in present:
                    name = "content-security-policy-report-only" if settings.csp_report_only \
                        else "content-security-policy"
                    add(name, content_security_policy(mercadopago=scope["path"].startswith(MP_PAGES)))
                if https:
                    add("strict-transport-security", "max-age=31536000; includeSubDomains")
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
