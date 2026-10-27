"""Reportes del panel (docs/REPORTES_PLAN.md, 9.2): agregados por cliente, agente, canal, linea y periodo.

El cliente ve solo lo suyo; el admin elige el cliente o ve todos (client_id vacio). Resultados, Mensajes,
Transferencias y Campañas piden el plan con `advanced_reports`; Tecnico y Plataforma son del admin."""
import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query

from ...config import settings
from ...models import Client
from ...services import limits as limits_service
from ...services import report_stats as service
from ...services.errors import Forbidden, Invalid
from ...services.report_stats import ReportFilter
from ..deps import DB, AdminPrincipal, CurrentPrincipal, scoped_client_id
from ..schemas import (
    ReportCallsOut,
    ReportCampaignsOut,
    ReportMessagesOut,
    ReportOutcomesOut,
    ReportPlatformOut,
    ReportSummaryOut,
    ReportTechnicalOut,
    ReportTransfersOut,
)

router = APIRouter(prefix="/reports", tags=["reports"])

PLAN_ERROR = {403: {"description": "El plan no incluye los reportes completos (advanced_reports_not_in_plan)"}}


def report_filter(
    p: CurrentPrincipal,
    client_id: Annotated[str | None, Query(description="Admin: un cliente (vacío = todos). Cliente: el suyo")] = None,
    agent_id: Annotated[str | None, Query(description="Solo las conversaciones de ese agente")] = None,
    channel: Annotated[Literal["voice", "whatsapp", "web"] | None,
                       Query(description="voice (teléfono), whatsapp o web (link para llamar)")] = None,
    phone_number_id: Annotated[str | None, Query(description="Solo las llamadas de esa línea")] = None,
    date_from: Annotated[datetime.date | None, Query(description="Día local, inclusive; default: hace 29 días")] = None,
    date_to: Annotated[datetime.date | None, Query(description="Día local, inclusive; default: hoy. Hasta 366 días")]
    = None,
    tz: Annotated[str | None, Query(description="Zona IANA de los días y horas; default BILLING_TIMEZONE")] = None,
    include_tests: Annotated[bool, Query(description="Con las llamadas de prueba y las conversaciones por API "
                                                     "(el loadtest nunca)")] = False,
) -> ReportFilter:
    try:
        zone = ZoneInfo(tz or settings.billing_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise Invalid(f"Zona horaria inexistente: {tz}") from None
    return ReportFilter(client_id=scoped_client_id(p, client_id), agent_id=agent_id, channel=channel,
                        phone_number_id=phone_number_id, date_from=date_from, date_to=date_to, tz=zone,
                        include_tests=include_tests).with_defaults()


Filter = Annotated[ReportFilter, Depends(report_filter)]


def _advanced(p, db) -> None:
    """Resultados, Mensajes, Transferencias y Campañas: el plan del cliente tiene que incluirlos."""
    if p.is_admin:
        return
    client = db.get(Client, p.client_id)
    if client is None or not limits_service.effective_limits(db, client).advanced_reports:
        raise Forbidden("Tu plan no incluye los reportes completos (resultados, mensajes, transferencias y "
                        "campañas).", "advanced_reports_not_in_plan")


@router.get("/summary", response_model=ReportSummaryOut)
def summary(flt: Filter, db: DB):
    """Resumen: consultas por día y canal con las transferencias, KPIs contra el período anterior
    (conversaciones, % de conversión y de objetivo, derivadas, minutos, duración media, rechazadas por el
    plan, mensajes de WhatsApp) y consumo del plan del mes con su proyección. Todos los planes."""
    return service.summary(db, flt)


@router.get("/calls", response_model=ReportCallsOut)
def calls(flt: Filter, db: DB):
    """Llamadas: por día y modo, mapa de calor por día de la semana y hora, por línea y por agente,
    duración, cómo terminan, cortes tempranos y quién llama (nuevos, que vuelven, los que más vuelven).
    Todos los planes."""
    return service.calls(db, flt)


@router.get("/outcomes", response_model=ReportOutcomesOut, responses=PLAN_ERROR)
def outcomes(flt: Filter, p: CurrentPrincipal, db: DB):
    """Resultados: conversión (completa, parcial, sin datos) por día y agente, resultados por agente,
    embudo, datos obligatorios capturados y comparación por versión del agente. Plan con reportes completos."""
    _advanced(p, db)
    return service.outcomes(db, flt)


@router.get("/messages", response_model=ReportMessagesOut, responses=PLAN_ERROR)
def messages(flt: Filter, p: CurrentPrincipal, db: DB):
    """Mensajes de WhatsApp: entrantes y salientes (texto y audio) por día, mapa de calor, entrega,
    fallas, mensajes por conversación, conversión y estado de las cuentas. Plan con reportes completos."""
    _advanced(p, db)
    return service.messages(db, flt)


@router.get("/transfers", response_model=ReportTransfersOut, responses=PLAN_ERROR)
def transfers(flt: Filter, p: CurrentPrincipal, db: DB):
    """Transferencias a personas: pedidas, atendidas, no atendidas y sin disponibilidad, por día, área y
    persona (tiempo hasta atender, minutos), y el puente de WhatsApp. Plan con reportes completos."""
    _advanced(p, db)
    return service.transfers(db, flt)


@router.get("/campaigns", response_model=ReportCampaignsOut, responses=PLAN_ERROR)
def campaigns(flt: Filter, p: CurrentPrincipal, db: DB):
    """Campañas que corrieron en el período: contactos, intentos, alcanzados, conversión, bajas y minutos;
    motivos de no contacto y mejores horarios. Plan con reportes completos."""
    _advanced(p, db)
    return service.campaigns(db, flt)


@router.get("/technical", response_model=ReportTechnicalOut)
def technical(flt: Filter, _: AdminPrincipal, db: DB):
    """Técnico (admin): latencia p50/p95 por día y por etapa, turnos por proveedor del LLM, herramientas
    (usos, errores, tiempos), errores de llamadas, mails de resumen fallidos y tokens."""
    return service.technical(db, flt)


@router.get("/platform", response_model=ReportPlatformOut)
def platform(flt: Filter, _: AdminPrincipal, db: DB):
    """Plataforma (admin, todos los clientes): tabla por cliente con alertas (cerca del cupo, inactivo),
    negocio (planes, altas, ingresos) y operación (pico de llamadas simultáneas, fallas, rechazos)."""
    if flt.client_id:
        raise Invalid("El reporte de plataforma es de todos los clientes: sin client_id")
    return service.platform(db, flt)
