"""Métricas de la plataforma para Prometheus (/internal/metrics, docs/OBSERVABILIDAD.md):
llamadas activas por modo, canales de Anura en uso y p95 por turno de las llamadas que terminaron en los
últimos 15 min (incluye loadtest: es carga real del server). Formato de texto de Prometheus."""
import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import CallRow
from ..models.calls import ACTIVE_CALL_STATUSES
from . import quota
from .report_stats import _percentile

LATENCY_WINDOW = datetime.timedelta(minutes=15)


def render(s: Session) -> str:
    now = utcnow()
    stale = now - datetime.timedelta(seconds=settings.call_max_duration_seconds + quota.STALE_MARGIN_SECONDS)
    lines = ["# HELP atentina_calls_active Llamadas activas por modo",
             "# TYPE atentina_calls_active gauge"]
    by_mode = dict(s.execute(select(CallRow.mode, func.count()).where(
        CallRow.status.in_(ACTIVE_CALL_STATUSES), CallRow.created_at >= stale).group_by(CallRow.mode)).all())
    for mode in sorted(set(by_mode) | {"entrante", "saliente"}):
        lines.append(f'atentina_calls_active{{mode="{mode}"}} {by_mode.get(mode, 0)}')
    lines += ["# HELP atentina_anura_channels_busy Canales de Anura ocupados (llamadas y tramos de derivación)",
              "# TYPE atentina_anura_channels_busy gauge",
              f"atentina_anura_channels_busy {quota.busy_channels(s, now)}",
              "# HELP atentina_anura_channels_total Canales de la cuenta de Anura (ANURA_CHANNELS)",
              "# TYPE atentina_anura_channels_total gauge",
              f"atentina_anura_channels_total {settings.anura_channels}"]
    totals = []
    for (latency,) in s.execute(select(CallRow.latency).where(
            CallRow.latency.is_not(None), CallRow.ended_at >= now - LATENCY_WINDOW)):
        totals += [float(t["total"]) for t in (latency or {}).get("turns") or []
                   if isinstance(t.get("total"), (int, float))]
    p95 = _percentile(totals, 0.95)
    if p95 is not None:
        lines += ["# HELP atentina_turn_latency_p95_seconds p95 por turno, llamadas terminadas en 15 min",
                  "# TYPE atentina_turn_latency_p95_seconds gauge",
                  f"atentina_turn_latency_p95_seconds {p95:.3f}"]
    return "\n".join(lines) + "\n"
