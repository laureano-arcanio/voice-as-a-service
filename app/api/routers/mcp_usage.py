"""Uso del servidor MCP por herramienta (services/mcp_usage.py): el cliente ve el suyo y el admin el de un
cliente o el de toda la plataforma."""
from fastapi import APIRouter, Query

from ...services import mcp_usage as service
from ..deps import DB, CurrentPrincipal, scoped_client_id
from ..schemas import McpUsageOut

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/usage", response_model=McpUsageOut)
def mcp_usage(p: CurrentPrincipal, db: DB, client_id: str | None = None,
              days: int = Query(default=30, ge=1, le=365)):
    """Cuántas veces se usó cada herramienta del MCP en los últimos `days` días, con errores y tiempo medio."""
    return service.summary(db, scoped_client_id(p, client_id), days)
