"""Plantillas de WhatsApp al equipo del cliente: aviso de un area, rotacion y complemento de una llamada.

Se usa desde `agent` y desde `app`. Nada de esto lanza: quien deriva sigue con la cadena aunque el aviso falle, y
cada resultado queda en wa_messages (type team_notice) y en eventos (handoff.whatsapp_sent o handoff.whatsapp_failed).
Sin telefonos ni textos en los logs ni en los eventos.
"""
import asyncio
import datetime
import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import utcnow
from ..models import Client, HandoffArea, TeamMember, WaAccount, WaMessage
from ..services import events, handoff, limits, wa_routing
from ..services.errors import QuotaExceeded
from . import store
from .crypto import TokenKeyMissing
from .graph import GraphClient, GraphError

logger = logging.getLogger(__name__)

TEAM_TYPES = ("team_notice", "team_relay")
# Un telefono real tiene al menos 8 digitos; lo demas es un caller oculto o un identificador.
MIN_PHONE_DIGITS = 8
# No dependen de la persona: probar con la siguiente solo repetiria la falla.
ACCOUNT_REASONS = frozenset({"no_template", "account_missing", "account_other_client", "account_inactive",
                             "account_disconnected", "client_inactive", "whatsapp_not_in_plan", "token_key_missing",
                             "token_rejected"})

# Tope total de un envio (graph.py da 15 s por operacion mas 5 de conexion): tiene que ser menor al lease de la rotacion,
# para que un paso vencido signifique que el proceso murio y no que el envio sigue en curso. Sin medir.
SEND_DEADLINE = 20.0

GraphFactory = Callable[[str], GraphClient]
Result = tuple[bool, str | None, dict | None]
# Antes de cada persona de un aviso. False: este camino ya no es dueño del paso y no envia nada mas.
BeforeSend = Callable[[], bool]


class _Refused(Exception):
    """No se puede enviar: la comprobacion previa no paso."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Notice:
    """Resultado de notify_area."""
    ok: bool
    member_id: str | None = None
    wamid: str | None = None
    error: dict | None = None


def _clean(value) -> str:
    """Meta rechaza saltos de linea, tabs y varios espacios seguidos en un parametro, y tambien uno vacio."""
    return " ".join(str(value).split()) or "-" if value is not None else "-"


def _params(template_cfg: dict, values: dict) -> list[str]:
    """Los parametros de la plantilla, por posicion."""
    out = []
    for name in template_cfg.get("params") or []:
        value = values.get(name)
        if name == "cliente" and len(wa_routing.digits(str(value or ""))) < MIN_PHONE_DIGITS:
            value = None
        out.append(_clean(value))
    return out


def _check_account(s: Session, client_id: str, area: HandoffArea, member: TeamMember,
                   template_cfg: dict | None) -> WaAccount:
    """La cuenta por la que se envia, siempre del cliente de la derivacion. _Refused si no se puede."""
    if area.client_id != client_id or member.client_id != client_id:
        raise _Refused("other_client")
    if not template_cfg or not template_cfg.get("name"):
        raise _Refused("no_template")
    account_id = (area.whatsapp or {}).get("account_id")
    account = s.get(WaAccount, account_id) if account_id else None
    if account is None:
        raise _Refused("account_missing")
    if account.client_id != client_id:
        raise _Refused("account_other_client")
    if not account.active:
        raise _Refused("account_inactive")
    if account.status != "connected":
        raise _Refused("account_disconnected")
    client = s.get(Client, client_id)
    if client is None or not client.active:
        raise _Refused("client_inactive")
    try:
        limits.check_whatsapp(s, client_id)
    except QuotaExceeded:
        raise _Refused("whatsapp_not_in_plan") from None
    if not member.whatsapp_notify:
        raise _Refused("member_not_notified")
    if not wa_routing.digits(member.phone):
        raise _Refused("member_without_phone")
    return account


def _record_failure(sessions: sessionmaker[Session], client_id: str, area_id: str | None, member_id: str | None,
                    conversation_id: str | None, error: dict, template: str | None = None,
                    account_id: str | None = None, wa_id: str | None = None, disconnect: bool = False) -> None:
    """La falla queda en eventos y, si llego a Meta, en wa_messages. Si la base tambien falla, solo el log."""
    try:
        with sessions() as s:
            if account_id and wa_id:
                store.record_outbound(s, wamid=None, account_id=account_id, conversation_id=conversation_id,
                                      wa_id=wa_id, type="team_notice", status="failed",
                                      error={k: error.get(k) for k in ("code", "subcode", "message")})
            if disconnect:
                account = s.get(WaAccount, account_id)
                if account is not None and account.status != "disconnected":
                    store.mark_status(s, account, "disconnected", f"token_invalid code={error.get('code')}")
            events.record(s, client_id, "handoff.whatsapp_failed", conversation_id=conversation_id, area_id=area_id,
                          team_member_id=member_id, reason=error.get("reason"), code=error.get("code"),
                          subcode=error.get("subcode"), template=template)
            s.commit()
    except Exception:
        logger.exception("wa: no se pudo registrar la falla de un aviso client=%s area=%s", client_id, area_id)


async def send(sessions: sessionmaker[Session], client_id: str, area: HandoffArea, member: TeamMember,
               template_cfg: dict | None, values: dict, conversation_id: str | None,
               *, graph_factory: GraphFactory | None = None) -> Result:
    """Envia una plantilla a una persona del area, por la cuenta del area. (ok, wamid, error); error es
    {"reason", "code", "subcode", "message"}. area y member: filas ya leidas, pueden venir de una sesion cerrada.
    Si sale, handoff.whatsapp_sent; si no, handoff.whatsapp_failed. Nunca lanza."""
    area_id = member_id = None
    try:
        # Aca y no arriba: service.py usa este modulo.
        from .service import recipient

        area_id, member_id = area.id, member.id
        with sessions() as s:
            account = _check_account(s, client_id, area, member, template_cfg)
            token = store.token_for(account)
            account_id, pnid, own_token = account.id, account.phone_number_id, store.has_own_token(account)
        names = {**values, "area": area.name, "persona": member.name}
        if "horario" in (template_cfg.get("params") or []) and not names.get("horario"):
            names["horario"] = handoff.describe_schedule(area.schedule)
        params = _params(template_cfg, names)
        wa_id = wa_routing.digits(member.phone)
        to = recipient(wa_id)
    except _Refused as e:
        error = {"reason": e.reason}
    except TokenKeyMissing:
        logger.error("wa: no se puede descifrar el token de la cuenta (WA_TOKEN_KEY) client=%s", client_id)
        error = {"reason": "token_key_missing"}
    except Exception:
        logger.exception("wa: fallo al preparar un aviso client=%s area=%s", client_id, area_id)
        error = {"reason": "internal"}
    else:
        return await _deliver(sessions, client_id, area_id, member_id, template_cfg, params, conversation_id,
                              account_id, pnid, token, own_token, wa_id, to, graph_factory)
    _record_failure(sessions, client_id, area_id, member_id, conversation_id, error,
                    template=(template_cfg or {}).get("name"))
    return False, None, error


async def _deliver(sessions: sessionmaker[Session], client_id: str, area_id: str, member_id: str, template_cfg: dict,
                   params: list[str], conversation_id: str | None, account_id: str, pnid: str, token: str,
                   own_token: bool, wa_id: str, to: str, graph_factory: GraphFactory | None) -> Result:
    name = template_cfg["name"]
    graph = None
    try:
        graph = graph_factory(token) if graph_factory else GraphClient(token, version=settings.wa_graph_version)
        async with asyncio.timeout(SEND_DEADLINE):
            data = await graph.send_template(pnid, to, name, template_cfg.get("language") or "es_AR", params)
    except GraphError as e:
        logger.warning("wa: aviso al equipo no enviado pnid=%s code=%s subcode=%s", pnid, e.code, e.subcode)
        error = {"reason": "token_rejected" if e.is_auth_error else "meta_rejected",
                 "code": e.code, "subcode": e.subcode, "message": e.message}
        _record_failure(sessions, client_id, area_id, member_id, conversation_id, error, template=name,
                        account_id=account_id, wa_id=wa_id, disconnect=e.is_auth_error and own_token)
        return False, None, error
    except Exception:
        logger.exception("wa: fallo al enviar un aviso pnid=%s", pnid)
        error = {"reason": "internal"}
        _record_failure(sessions, client_id, area_id, member_id, conversation_id, error, template=name,
                        account_id=account_id, wa_id=wa_id)
        return False, None, error
    finally:
        if graph is not None and graph_factory is None:
            await _close(graph)
    messages = data.get("messages") if isinstance(data, dict) else None
    wamid = messages[0].get("id") if isinstance(messages, list) and messages else None
    # Ya salio: un problema al registrarlo no lo convierte en falla, o el aviso le llegaria a dos.
    failed = False
    try:
        with sessions() as s:
            # Un status failed puede llegar antes que esta respuesta: la fila ya esta y no retrocede. Por eso la falla
            # va sin cuenta: crearia una segunda fila.
            failed = store.record_outbound(s, wamid=wamid, account_id=account_id, conversation_id=conversation_id,
                                           wa_id=wa_id, type="team_notice", status="sent").status == "failed"
            if not failed:
                events.record(s, client_id, "handoff.whatsapp_sent", conversation_id=conversation_id, area_id=area_id,
                              team_member_id=member_id, template=name, wamid=wamid)
            s.commit()
    except Exception:
        logger.exception("wa: no se pudo registrar un aviso enviado pnid=%s", pnid)
    if failed:
        error = {"reason": "meta_failed"}
        _record_failure(sessions, client_id, area_id, member_id, conversation_id, error, template=name)
        return False, None, error
    return True, wamid, None


async def _close(graph: GraphClient) -> None:
    try:
        await graph.aclose()
    except Exception:
        logger.warning("wa: no se pudo cerrar el cliente de Meta", exc_info=True)


async def notify_area(sessions: sessionmaker[Session], client_id: str, area_id: str, values: dict,
                      conversation_id: str | None, *, graph_factory: GraphFactory | None = None,
                      before_send: BeforeSend | None = None) -> Notice:
    """Aviso de un area delivery=whatsapp: una sola persona, la primera de los candidatos con el toggle. Si Meta la
    rechaza, prueba con la siguiente. A quien se fue mientras tanto (inactivo o borrado) se lo saltea: el aviso lleva el
    telefono. Si no se le pudo enviar a nadie por eso, es no_members. Si before_send da False corta sin registrar falla:
    el paso es de otro. Nunca lanza, salvo lo que lance before_send."""
    try:
        with sessions() as s:
            area = s.get(HandoffArea, area_id)
            if area is None or area.client_id != client_id:
                area, members = None, []
            else:
                members = [m for m in handoff.candidates(s, area) if m.whatsapp_notify]
    except Exception:
        logger.exception("wa: fallo al preparar el aviso de un area client=%s area=%s", client_id, area_id)
        error = {"reason": "internal"}
        _record_failure(sessions, client_id, None, None, conversation_id, error)
        return Notice(False, error=error)
    if area is None:
        error = {"reason": "area_missing"}
        _record_failure(sessions, client_id, None, None, conversation_id, error)
        return Notice(False, error=error)
    template_cfg = (area.whatsapp or {}).get("template")
    if not members:
        error = {"reason": "no_members"}
        _record_failure(sessions, client_id, area_id, None, conversation_id, error,
                        template=(template_cfg or {}).get("name"))
        return Notice(False, error=error)
    error = None
    for member in members:
        if before_send is not None and not before_send():
            return Notice(False)
        # Sin await hasta el envio. Si no se puede leer, no sale: es como un envio fallido.
        try:
            with sessions() as s:
                active = s.scalar(select(TeamMember.active).where(TeamMember.id == member.id))
        except Exception:
            logger.exception("wa: fallo al releer a una persona del aviso client=%s area=%s", client_id, area_id)
            error = {"reason": "internal"}
            _record_failure(sessions, client_id, area_id, member.id, conversation_id, error,
                            template=(template_cfg or {}).get("name"))
            continue
        if not active:
            continue
        ok, wamid, error = await send(sessions, client_id, area, member, template_cfg, values, conversation_id,
                                      graph_factory=graph_factory)
        if ok:
            _record_notified(sessions, client_id, area_id, member.id, conversation_id, wamid)
            return Notice(True, member.id, wamid)
        if error and error.get("reason") in ACCOUNT_REASONS:
            break
    if error is None:
        error = {"reason": "no_members"}
        _record_failure(sessions, client_id, area_id, None, conversation_id, error,
                        template=(template_cfg or {}).get("name"))
    return Notice(False, error=error)


def _record_notified(sessions: sessionmaker[Session], client_id: str, area_id: str, member_id: str,
                     conversation_id: str | None, wamid: str | None) -> None:
    try:
        with sessions() as s:
            area = s.get(HandoffArea, area_id)
            if area is not None:
                area.last_member_id = member_id
            events.record(s, client_id, "handoff.notified", conversation_id=conversation_id, area_id=area_id,
                          team_member_id=member_id, wamid=wamid)
            s.commit()
    except Exception:
        logger.exception("wa: no se pudo registrar un aviso enviado client=%s area=%s", client_id, area_id)


def recent_notice(s: Session, account_id: str, wa_id: str, hours: float) -> bool:
    """True si a este numero se le envio algo del equipo por esta cuenta en las ultimas `hours`. Compara en forma
    canonica: el miembro es +549..., el entrante 549... y el destino se manda sin el 9. Un envio fallido no cuenta."""
    since = utcnow() - datetime.timedelta(hours=hours)
    sent = s.scalars(select(WaMessage.wa_id).distinct().where(
        WaMessage.account_id == account_id, WaMessage.direction == "out", WaMessage.type.in_(TEAM_TYPES),
        WaMessage.status != "failed", WaMessage.created_at >= since))
    return any(wa_routing.same_number(number, wa_id) for number in sent)
