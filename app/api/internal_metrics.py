"""/internal/metrics: métricas de la plataforma para Prometheus (services/platform_metrics.py).

Con `Authorization: Bearer $MONITORING_TOKEN`; sin token configurado, 404. No se sirve a lo que llega por
Cloudflare (el túnel de app.atentina.com.ar trae CF-Connecting-IP): solo a Prometheus, por la red de compose.
"""
import hmac

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response

from ..config import settings
from ..services import platform_metrics
from .deps import DB

router = APIRouter(include_in_schema=False)


@router.get("/internal/metrics")
def internal_metrics(request: Request, db: DB):
    token = settings.monitoring_token
    auth = request.headers.get("authorization", "")
    if (not token or "cf-connecting-ip" in request.headers
            or not hmac.compare_digest(auth.encode(), f"Bearer {token}".encode())):
        return Response(status_code=404)
    return PlainTextResponse(platform_metrics.render(db), media_type="text/plain; version=0.0.4")
