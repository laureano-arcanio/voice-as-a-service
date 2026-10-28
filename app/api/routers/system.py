"""Estado del hardware y del servicio (docs/OBSERVABILIDAD.md): solo admin, leído de
Prometheus (services/system_status.py). Sin el monitoreo levantado, 503 monitoring_off/monitoring_down."""
from typing import Literal

from fastapi import APIRouter, Query

from ...services import system_status as service
from ..deps import AdminPrincipal
from ..schemas import SystemEventOut, SystemHistoryOut, SystemNowOut, SystemPeakOut

router = APIRouter(prefix="/system", tags=["system"])

Window = Literal["1h", "6h", "24h", "7d"]


def _run(fn, *args):
    prom = service.client()
    try:
        return fn(prom, *args)
    finally:
        prom.close()


@router.get("/now", response_model=SystemNowOut)
def system_now(_: AdminPrincipal):
    """Foto actual de cada host: CPU, RAM, discos, red, GPUs, servicios, sondas, saturación y alertas activas."""
    return _run(service.now)


@router.get("/history", response_model=SystemHistoryOut)
def system_history(_: AdminPrincipal, window: Window = "24h"):
    """Series de la ventana para los gráficos (lo que tiene picos, con el máximo de cada paso)."""
    return _run(service.history, window)


@router.get("/events", response_model=list[SystemEventOut])
def system_events(_: AdminPrincipal, window: Window = "24h"):
    """Alertas que estuvieron disparadas en la ventana, con su inicio y fin."""
    return _run(service.events, window)


@router.get("/peaks", response_model=list[SystemPeakOut])
def system_peaks(_: AdminPrincipal, days: int = Query(default=7, ge=1, le=30)):
    """Máximo de cada día (CPU, RAM, potencia y temperatura de GPU, KV cache, llamadas, alertas críticas)."""
    return _run(service.peaks, days)
