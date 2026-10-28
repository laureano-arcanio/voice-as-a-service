"""Campañas salientes por WhatsApp o voz (docs/features/CAMPANAS.md; la logica comun,
en services/campaigns.py; la de WhatsApp, en app/whatsapp/campaigns.py).

- Ver: quien puede ver al cliente (admin, usuario o API key del cliente).
- Crear, editar, sumar contactos, iniciar y retomar: en WhatsApp, en un numero que el cliente administra
  (como las plantillas; los de la WABA de nuestro portafolio, solo un admin); en voz, quien ve al cliente.
- Pausar y cancelar: cualquiera que la vea (frenar siempre se puede).
- El plan (canales, campañas por mes, contactos por campaña, concurrencia, seguimiento) se valida al
  crear, al sumar contactos y al iniciar. Las de voz las marca el dialer (app/campaigns/dialer.py).
- `purpose`: las comerciales piden `no_call_registry_checked` al iniciar (Registro No Llame).
- `followup` (voz): seguimiento por WhatsApp a quien no atendio. `callback_url`: webhook firmado.
- /whatsapp/campaigns/* sigue funcionando como alias de las de WhatsApp.
"""
import datetime
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import func, select

from ...config import settings
from ...models import Agent, Campaign, CampaignContact, Client, WaAccount, WaMessage
from ...services import (
    campaign_callbacks,
    campaign_reports,
    contacts,
    limits,
)
from ...services import campaigns as common
from ...services.errors import Conflict, Invalid, NotFound
from ...services.security import Principal
from ...whatsapp import campaigns as wa
from ..deps import DB, CurrentPrincipal, Definitions, scoped_client_id
from ..schemas import (
    CampaignContactOut,
    CampaignContactPage,
    CampaignContactsAdded,
    CampaignContactsIn,
    CampaignCreated,
    CampaignIn,
    CampaignOut,
    CampaignPatch,
    CampaignPlanOut,
    CampaignProgress,
    CampaignStartIn,
    CampaignStatsOut,
    ContactRejected,
    FollowupIn,
    VoiceResult,
)
from .whatsapp import _get_managed

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
WA_RESULTS = ("sent", "delivered", "read", "replied")
# Los campos de la edicion donde null es un valor (el resto: null = sin cambio).
NULLABLE = ("agent_id", "from_number_id", "voice", "weekdays", "starts_at", "ends_at", "purpose", "followup",
            "callback_url", "callback_secret")


def _utc(d: datetime.datetime | None) -> datetime.datetime | None:
    """La base guarda UTC sin zona: una fecha con zona se pasa a UTC; sin zona se toma como UTC."""
    if d is not None and d.tzinfo is not None:
        return d.astimezone(datetime.UTC).replace(tzinfo=None)
    return d


def _outs(db, rows: list[Campaign]) -> list[CampaignOut]:
    ids = [c.id for c in rows]
    progress = common.progress(db, ids)
    voice_results = common.voice_results(db, [c.id for c in rows if c.channel == "voice"])
    wa_stats = wa.stats(db, [c.id for c in rows if c.channel == "whatsapp"])
    followups = common.followup_counts(db, [c.id for c in rows if c.channel == "voice" and c.followup])
    outs = []
    for c in rows:
        prog = progress[c.id]
        client = db.get(Client, c.client_id)
        account = db.get(WaAccount, c.account_id) if c.account_id else None
        agent = db.get(Agent, c.agent_id or (account.agent_id if account else ""))
        if c.channel == "voice":
            results, minutes = voice_results[c.id], common.minutes_used(db, c.id)
        else:
            results, minutes = {k: wa_stats[c.id][k] for k in WA_RESULTS}, None
        outs.append(CampaignOut(
            id=c.id, client_id=c.client_id, client_name=client.name if client else None, channel=c.channel,
            name=c.name, agent_id=c.agent_id, agent_name=agent.name if agent else None, status=c.status,
            status_reason=c.status_reason, in_window=common.in_window(c), rate_per_minute=c.rate_per_minute,
            window_start=c.window_start, window_end=c.window_end, weekdays=c.weekdays,
            timezone=settings.billing_timezone, starts_at=c.starts_at, ends_at=c.ends_at, account_id=c.account_id,
            display_phone_number=account.display_phone_number if account else None, template_name=c.template_name,
            template_language=c.template_language, template_category=c.template_category or None,
            template_body=c.template_body or None, template_params=c.template_params if c.account_id else None,
            param_names=c.template_param_names, from_number_id=c.from_number_id, voice=c.voice,
            concurrency=c.concurrency, max_attempts=c.max_attempts, retry_minutes=c.retry_minutes,
            retry_on=c.retry_on, followup_config=c.followup, followup=followups.get(c.id), purpose=c.purpose,
            registry_confirmed=c.no_call_confirmed_at is not None, callback_url=c.callback_url,
            total=sum(prog.values()), percent=common.percent(prog),
            eta_minutes=common.eta_minutes(db, c, prog), progress=CampaignProgress(**prog), results=results,
            minutes_used=minutes, started_at=c.started_at, finished_at=c.finished_at, created_at=c.created_at,
            updated_at=c.updated_at))
    return outs


def _out(db, c: Campaign) -> CampaignOut:
    return _outs(db, [c])[0]


def _get(db, campaign_id: str, p: Principal) -> Campaign:
    c = db.get(Campaign, campaign_id)
    if c is None or not p.can_access(c.client_id):
        raise NotFound("Campaña inexistente")
    return c


def _get_editable(db, campaign_id: str, p: Principal) -> tuple[Campaign, WaAccount | None]:
    c = _get(db, campaign_id, p)
    return c, (_get_managed(db, c.account_id, p) if c.channel == "whatsapp" else None)


def _skipped(items: list[common.Skipped]) -> list[ContactRejected]:
    return [ContactRejected(phone=x.phone, reason=x.reason, line=x.line) for x in items]


def _add(db, c: Campaign, body: CampaignContactsIn) -> tuple[int, list[common.Skipped]]:
    """Suma los contactos de todas las fuentes del pedido, en este orden: recipients (WhatsApp, con
    sus variables), contact_ids, contacts y csv (estos dos se cargan antes en la agenda)."""
    added, skipped = 0, []
    if body.recipients:
        if c.channel != "whatsapp":
            raise Invalid("recipients es solo de WhatsApp: en voz, usá contacts, contact_ids o csv")
        n, sk = wa.add_recipients(db, c, [wa.Row(phone=r.phone, name=r.name, params=list(r.params))
                                          for r in body.recipients])
        added, skipped = added + n, skipped + sk
    candidates: list[common.Candidate] = []
    for item in common.contacts_by_ids(db, c.client_id, body.contact_ids):
        if isinstance(item, common.Skipped):
            skipped.append(item)
        else:
            candidates.append(item)
    for rows, source in (([contacts.ContactRow(**x.model_dump()) for x in body.contacts], "api"),
                         (contacts.parse_csv(body.csv) if body.csv else [], "csv")):
        if rows:
            cands, sk = common.contacts_from_rows(db, c.client_id, rows, source)
            candidates += cands
            skipped += sk
    if candidates:
        n, sk = common.add_contacts(db, c, candidates)
        added, skipped = added + n, skipped + sk
    return added, skipped


async def _followup(db, client_id: str, f: FollowupIn, p: Principal) -> dict:
    """El seguimiento por WhatsApp de una campaña de voz, validado contra el plan, la cuenta y la plantilla de Meta."""
    account = _get_managed(db, f.account_id, p)
    if account.client_id != client_id:
        raise NotFound("Número de WhatsApp inexistente para este cliente")
    template = await wa.fetch_template(db, account, f.template_name, f.template_language)
    return wa.followup_config(db, client_id, account, template, after=f.after, params=f.params, agent_id=f.agent_id)


async def _launch(db, c: Campaign, account: WaAccount | None, registry_checked: bool = False) -> None:
    """Inicia o retoma. En WhatsApp relee la plantilla en Meta: si la pausaron, la rechazaron o le
    cambiaron las variables, no arranca (422). En voz valida el agente y el numero de origen, y el
    seguimiento por WhatsApp (plan, numero y plantilla de nuevo). Una comercial pide la confirmacion
    del Registro No Llame."""
    if c.channel == "whatsapp":
        template = await wa.fetch_template(db, account, c.template_name, c.template_language)
        if template.params != c.template_params:
            raise Invalid(f"La plantilla ahora tiene {template.params} variables y la campaña se cargó con "
                          f"{c.template_params}: creá otra campaña")
        c.template_body, c.template_category = template.body, template.category
        wa.start(db, c, account, registry_checked=registry_checked)
    else:
        common.check_startable(db, c)
        if c.followup:
            f = c.followup
            follow_account = db.get(WaAccount, f.get("account_id") or "")
            if follow_account is None:
                raise Conflict("El número de WhatsApp del seguimiento ya no existe: elegí otro")
            template = await wa.fetch_template(db, follow_account, f["template_name"], f["template_language"])
            c.followup = wa.followup_config(db, c.client_id, follow_account, template, after=f["after"],
                                            params=f["params"], agent_id=f.get("agent_id"))
        common.start(db, c, registry_checked=registry_checked)


@router.get("", response_model=list[CampaignOut])
def list_campaigns(p: CurrentPrincipal, db: DB, client_id: str | None = None,
                   channel: Literal["whatsapp", "voice"] | None = None,
                   status: Literal["draft", "scheduled", "running", "paused", "done", "cancelled"] | None = None,
                   offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
    """Las campañas, las mas nuevas primero, con su avance."""
    q = select(Campaign).order_by(Campaign.created_at.desc(), Campaign.id)
    if (cid := scoped_client_id(p, client_id)) is not None:
        q = q.where(Campaign.client_id == cid)
    if channel:
        q = q.where(Campaign.channel == channel)
    if status:
        q = q.where(Campaign.status == status)
    return _outs(db, list(db.scalars(q.offset(offset).limit(limit))))


@router.post("", response_model=CampaignCreated, status_code=201)
async def create_campaign(body: CampaignIn, p: CurrentPrincipal, db: DB):
    """Crea la campaña en borrador, con sus contactos si vienen. Valida el plan. Con `start` la inicia
    en el mismo pedido (si algo falla, no queda nada). Lo que no entra vuelve en `skipped`."""
    created_by = p.id if p.kind == "user" else None
    if body.callback_url:
        await campaign_callbacks.check_url_async(body.callback_url)      # el DNS, fuera del event loop
    window = {"rate_per_minute": body.rate_per_minute, "window_start": body.window_start,
              "window_end": body.window_end}
    when = {"weekdays": body.weekdays, "starts_at": _utc(body.starts_at), "ends_at": _utc(body.ends_at)}
    account = None
    if body.channel == "whatsapp":
        if not body.account_id or not body.template_name:
            raise Invalid("Una campaña de WhatsApp necesita account_id y template_name")
        if body.followup is not None:
            raise Invalid("followup es solo de las campañas de voz")
        account = _get_managed(db, body.account_id, p)
        common.check_channel(db, account.client_id, "whatsapp")     # antes de ir a Meta
        template = await wa.fetch_template(db, account, body.template_name, body.template_language)
        c = wa.create(db, account=account, name=body.name, template=template, agent_id=body.agent_id,
                      created_by=created_by, param_names=body.param_names, purpose=body.purpose, **window, **when)
    else:
        client_id = scoped_client_id(p, body.client_id)
        if client_id is None:
            raise Invalid("Indicá client_id")
        if db.get(Client, client_id) is None:
            raise NotFound("Cliente inexistente")
        followup = await _followup(db, client_id, body.followup, p) if body.followup is not None else None
        c = common.create_voice(
            db, client_id=client_id, name=body.name, agent_id=body.agent_id, from_number_id=body.from_number_id,
            voice=body.voice, concurrency=body.concurrency, max_attempts=body.max_attempts,
            retry_minutes=body.retry_minutes, retry_on=body.retry_on, created_by=created_by, purpose=body.purpose,
            followup=followup, **window, **when)
    secret = campaign_callbacks.set_webhook(
        c, {"callback_url": body.callback_url, "callback_secret": body.callback_secret}, resolve=False) \
        if body.callback_url else None
    added, skipped = _add(db, c, body)
    if body.start:
        await _launch(db, c, account, body.no_call_registry_checked)
    db.commit()
    out = _out(db, c)
    out.callback_secret = secret     # solo ahora: despues no se vuelve a mostrar
    return CampaignCreated(campaign=out, added=added, skipped=_skipped(skipped))


@router.get("/plan", response_model=CampaignPlanOut)
def campaign_plan(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Lo que el plan del cliente permite en campañas y agenda, con lo que ya usó este mes: la UI
    deshabilita con el motivo lo que no entra. Un admin indica `client_id`."""
    cid = scoped_client_id(p, client_id)
    if cid is None:
        raise Invalid("Indicá client_id")
    lim = common.effective(db, cid)
    return CampaignPlanOut(
        client_id=cid, tier_name=lim.tier_name, channels=list(lim.campaign_channels), followup=lim.campaign_followup,
        max_campaigns_per_month=lim.max_campaigns_per_month, campaigns_started=limits.campaigns_started(db, cid),
        max_campaign_contacts=lim.max_campaign_contacts, max_campaign_concurrency=lim.max_campaign_concurrency,
        max_contacts=lim.max_contacts, contacts_active=limits.active_contacts(db, cid))


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: str, p: CurrentPrincipal, db: DB, definitions: Definitions):
    """El estado y el avance de la campaña, para consultar cada pocos segundos: `progress` (contactos
    por estado), `results`, `percent`, `eta_minutes` y, en voz, `goal` y `minutes_used`."""
    c = _get(db, campaign_id, p)
    out = _out(db, c)
    if c.channel == "voice":     # recorre las conversaciones atendidas: solo en el detalle, no en la lista
        out.goal = campaign_reports.goal_count(db, c, definitions)
    return out


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(campaign_id: str, body: CampaignPatch, p: CurrentPrincipal, db: DB):
    c, _ = _get_editable(db, campaign_id, p)
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k in NULLABLE}
    for key in ("starts_at", "ends_at"):
        if key in changes:
            changes[key] = _utc(changes[key])
    if "followup" in changes:
        if c.channel != "voice":
            raise Invalid("followup es solo de las campañas de voz")
        changes["followup"] = await _followup(db, c.client_id, body.followup, p) if body.followup is not None else None
    webhook = {k: changes.pop(k) for k in ("callback_url", "callback_secret") if k in changes}
    if webhook.get("callback_url"):
        await campaign_callbacks.check_url_async(webhook["callback_url"])
    common.update(db, c, changes)
    secret = campaign_callbacks.set_webhook(c, webhook, resolve=False) if webhook else None
    db.commit()
    out = _out(db, c)
    out.callback_secret = secret
    return out


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    """Solo en borrador (409 si ya empezo: se cancela)."""
    c, _ = _get_editable(db, campaign_id, p)
    common.delete(db, c)
    db.commit()


@router.post("/{campaign_id}/contacts", response_model=CampaignContactsAdded)
def add_contacts(campaign_id: str, body: CampaignContactsIn, p: CurrentPrincipal, db: DB):
    """Suma contactos a una campaña en borrador o pausada: de la agenda (`contact_ids`) o nuevos
    (`contacts`, `csv`: tambien entran en la agenda). Valida los topes del plan."""
    c, _ = _get_editable(db, campaign_id, p)
    added, skipped = _add(db, c, body)
    db.commit()
    return CampaignContactsAdded(added=added, skipped=_skipped(skipped))


@router.get("/{campaign_id}/contacts", response_model=CampaignContactPage)
def list_campaign_contacts(
        campaign_id: str, p: CurrentPrincipal, db: DB,
        status: Literal["pending", "in_progress", "retry", "done", "failed", "skipped"] | None = None,
        result: str | None = Query(default=None, description="Voz: answered, no_answer, busy, voicemail, invalid, "
                                                              "rejected o failed. WhatsApp: sent, delivered, read, "
                                                              "replied o failed (el estado mas avanzado de cada uno)"),
        offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=500)):
    """Los contactos de la campaña, en orden de carga, con el resultado de cada uno y la conversacion."""
    c = _get(db, campaign_id, p)
    r, m = CampaignContact, WaMessage
    q = select(r, m).outerjoin(m, m.wamid == r.wamid).where(r.campaign_id == c.id)
    if status:
        q = q.where(r.status == status)
    if result:
        if c.channel == "whatsapp":
            if result not in (*WA_RESULTS, "failed"):
                raise Invalid(f"Resultado inválido: {result}")
            q = q.where(wa.status_filters()[result])
        elif result not in VoiceResult.__args__:
            raise Invalid(f"Resultado inválido: {result}")
        else:
            q = q.where(r.result == result)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = []
    for row, msg in db.execute(q.order_by(r.created_at, r.id).offset(offset).limit(limit)).all():
        whatsapp = c.channel == "whatsapp"
        failed_later = whatsapp and row.status == "done" and msg is not None and msg.status == "failed"
        items.append(CampaignContactOut(
            id=row.id, contact_id=row.contact_id, phone=row.contact.phone, name=row.contact.name, vars=row.vars,
            status=row.status, result=wa.shown_result(row, msg.status if msg else None) if whatsapp else row.result,
            error=msg.error if failed_later else row.error, conversation_id=row.conversation_id,
            attempts=row.attempts, next_attempt_at=row.next_attempt_at, last_attempt_at=row.last_attempt_at,
            sent_at=row.sent_at, replied_at=row.replied_at))
    return CampaignContactPage(items=items, total=total)


@router.get("/{campaign_id}/stats", response_model=CampaignStatsOut)
def campaign_stats(campaign_id: str, p: CurrentPrincipal, db: DB, definitions: Definitions):
    """Indicadores de la campaña: tasa de contacto (atendidas o respondidas sobre llamadas o envios), tasa
    de objetivo, duracion media, minutos, distribucion de resultados y llamadas por hora del dia."""
    return campaign_reports.stats(db, _get(db, campaign_id, p), definitions)


@router.get("/{campaign_id}/report.csv", response_class=Response, responses={200: {"content": {"text/csv": {}}}})
def campaign_report(campaign_id: str, p: CurrentPrincipal, db: DB, definitions: Definitions):
    """El reporte por contacto en CSV (UTF-8 con BOM): telefono, vars, intentos, resultado,
    duracion, outcome, objetivo, campos capturados, seguimiento y link a la conversacion."""
    c = _get(db, campaign_id, p)
    return Response(campaign_reports.report_csv(db, c, definitions), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="campana-{c.id[:8]}.csv"'})


async def _start(db, campaign_id: str, p: Principal, expected: str, conflict: str,
                 body: CampaignStartIn | None) -> CampaignOut:
    c, account = _get_editable(db, campaign_id, p)
    if c.status != expected:
        raise Conflict(conflict)
    await _launch(db, c, account, bool(body and body.no_call_registry_checked))
    db.commit()
    return _out(db, c)


@router.post("/{campaign_id}/start", response_model=CampaignOut)
async def start_campaign(campaign_id: str, p: CurrentPrincipal, db: DB, body: CampaignStartIn | None = None):
    """Inicia una campaña en borrador: valida el plan, el agente, el numero o la plantilla, y los
    contactos. Con `starts_at` futuro queda `scheduled` y arranca sola. Una campaña comercial pide
    `no_call_registry_checked` (Registro No Llame)."""
    return await _start(db, campaign_id, p, "draft", "Solo se inicia una campaña en borrador", body)


@router.post("/{campaign_id}/resume", response_model=CampaignOut)
async def resume_campaign(campaign_id: str, p: CurrentPrincipal, db: DB, body: CampaignStartIn | None = None):
    """Retoma una campaña pausada (a mano o por un problema), con las mismas validaciones."""
    return await _start(db, campaign_id, p, "paused", "Solo se retoma una campaña pausada", body)


@router.post("/{campaign_id}/pause", response_model=CampaignOut)
def pause_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    c = _get(db, campaign_id, p)
    common.pause(db, c)
    db.commit()
    return _out(db, c)


@router.post("/{campaign_id}/cancel", response_model=CampaignOut)
def cancel_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    """Termina la campaña: los pendientes no se mandan ni se llaman. Las respuestas siguen llegando al agente."""
    c = _get(db, campaign_id, p)
    common.cancel(db, c)
    db.commit()
    return _out(db, c)
