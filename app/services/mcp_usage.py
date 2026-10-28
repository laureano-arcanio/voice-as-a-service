"""Uso del servidor MCP por herramienta (docs/features/MCP.md): una fila por día, cliente y herramienta
en mcp_tool_usage. Lo anota app/mcp/server.py después de cada tools/call; lo leen el panel (Agentes de IA)
y la herramienta admin_get_mcp_usage. Sin argumentos ni respuestas: solo cuántas, errores y tiempo."""
import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import McpToolUsage
from .api_usage import today


def record(s: Session, client_id: str | None, tool: str, error: bool, ms: int) -> None:
    day = today()
    row = s.scalar(select(McpToolUsage).where(McpToolUsage.day == day, McpToolUsage.tool == tool,
                                              McpToolUsage.client_id.is_(None) if client_id is None
                                              else McpToolUsage.client_id == client_id))
    if row is None:
        row = McpToolUsage(day=day, client_id=client_id, tool=tool, calls=0, errors=0, total_ms=0)
        s.add(row)
    row.calls += 1
    row.errors += int(error)
    row.total_ms += max(ms, 0)
    s.commit()


def summary(s: Session, client_id: str | None, days: int = 30) -> dict:
    """Los últimos `days` días, por herramienta (la más usada primero). client_id None: toda la plataforma."""
    since = today() - datetime.timedelta(days=days - 1)
    q = (select(McpToolUsage.tool, func.sum(McpToolUsage.calls), func.sum(McpToolUsage.errors),
                func.sum(McpToolUsage.total_ms), func.max(McpToolUsage.day))
         .where(McpToolUsage.day >= since).group_by(McpToolUsage.tool))
    if client_id is not None:
        q = q.where(McpToolUsage.client_id == client_id)
    tools = [{"tool": tool, "calls": int(calls), "errors": int(errors),
              "avg_ms": round(total / calls) if calls else 0, "last_day": last}
             for tool, calls, errors, total, last in s.execute(q)]
    tools.sort(key=lambda t: (-t["calls"], t["tool"]))
    return {"since": since, "days": days, "calls": sum(t["calls"] for t in tools),
            "errors": sum(t["errors"] for t in tools), "tools": tools}
