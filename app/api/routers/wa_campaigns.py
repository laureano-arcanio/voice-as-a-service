"""Campañas salientes de WhatsApp y bajas (app/whatsapp/campaigns.py; el envio, sender.py).

- Ver: quien puede ver el cliente (admin, usuario o API key del cliente).
- Crear, editar, sumar contactos e iniciar: en un numero que el cliente administra, como
  las plantillas: el admin en cualquiera; el cliente solo en los suyos (token propio). Los
  de alta manual usan la WABA de nuestro portafolio (403).
- Pausar y cancelar: cualquiera que la vea (frenar siempre se puede).
- Bajas: por cliente; un contacto dado de baja no recibe ninguna campaña.
"""
from fastapi import APIRouter, Query

from ...config import settings
from ...models import Agent, Client, WaAccount, WaCampaign
from ...services.errors import Invalid, NotFound
from ...services.security import Principal
from ...whatsapp import campaigns
from ..deps import (
    DB,
    CurrentPrincipal,
    ensure_access,
    ensure_client_active,
    scoped_client_id,
)
from ..schemas import (
    WaCampaignCreated,
    WaCampaignIn,
    WaCampaignOut,
    WaCampaignPatch,
    WaCampaignStats,
    WaOptoutIn,
    WaOptoutOut,
    WaRecipientOut,
    WaRecipientPage,
    WaRecipientsAdded,
    WaRecipientsIn,
    WaRecipientSkipped,
)
from .whatsapp import _get_managed

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _out(db, c: WaCampaign, stats: dict | None = None) -> WaCampaignOut:
    account = db.get(WaAccount, c.account_id)
    client = db.get(Client, c.client_id)
    agent = db.get(Agent, c.agent_id or (account.agent_id if account else ""))
    if stats is None:
        stats = campaigns.stats(db, [c.id])[c.id]
    return WaCampaignOut(
        id=c.id, client_id=c.client_id, client_name=client.name if client else None, account_id=c.account_id,
        display_phone_number=account.display_phone_number if account else None, agent_id=c.agent_id,
        agent_name=agent.name if agent else None, name=c.name, template_name=c.template_name,
        template_language=c.template_language, template_category=c.template_category,
        template_body=c.template_body, template_params=c.template_params, status=c.status,
        status_reason=c.status_reason, rate_per_minute=c.rate_per_minute, window_start=c.window_start,
        window_end=c.window_end, timezone=settings.billing_timezone, stats=WaCampaignStats(**stats),
        started_at=c.started_at, finished_at=c.finished_at, created_at=c.created_at, updated_at=c.updated_at)


def _get(db, campaign_id: str, p: Principal) -> WaCampaign:
    c = db.get(WaCampaign, campaign_id)
    if c is None or not p.can_access(c.client_id):
        raise NotFound("Campaña inexistente")
    return c


def _get_editable(db, campaign_id: str, p: Principal) -> tuple[WaCampaign, WaAccount]:
    c = _get(db, campaign_id, p)
    return c, _get_managed(db, c.account_id, p)


def _rows(body: WaRecipientsIn) -> list[campaigns.Row]:
    rows = [campaigns.Row(phone=r.phone, name=r.name, params=list(r.params)) for r in body.recipients]
    if body.csv:
        rows += campaigns.parse_csv(body.csv)
    return rows


def _added(added: int, skipped: list[campaigns.Skipped]) -> dict:
    return {"added": added, "skipped": [WaRecipientSkipped(phone=x.phone, reason=x.reason, line=x.line)
                                        for x in skipped]}


@router.get("/campaigns", response_model=list[WaCampaignOut])
def list_campaigns(p: CurrentPrincipal, db: DB, client_id: str | None = None, account_id: str | None = None):
    rows = campaigns.list_campaigns(db, scoped_client_id(p, client_id), account_id)
    stats = campaigns.stats(db, [c.id for c in rows])
    return [_out(db, c, stats[c.id]) for c in rows]


@router.post("/campaigns", response_model=WaCampaignCreated, status_code=201)
async def create_campaign(body: WaCampaignIn, p: CurrentPrincipal, db: DB):
    """Crea la campaña en borrador con sus contactos. Lee la plantilla de Meta: tiene que
    estar aprobada (422 si no). Los contactos invalidos, repetidos o dados de baja vuelven
    en `skipped`. Se envia con /start."""
    account = _get_managed(db, body.account_id, p)
    ensure_client_active(db, account.client_id)
    rows = _rows(body)
    template = await campaigns.fetch_template(db, account, body.template_name, body.template_language)
    c = campaigns.create(db, account=account, name=body.name, template=template, agent_id=body.agent_id,
                         rate_per_minute=body.rate_per_minute, window_start=body.window_start,
                         window_end=body.window_end, created_by=p.id if p.kind == "user" else None)
    added, skipped = campaigns.add_recipients(db, c, rows)
    db.commit()
    return WaCampaignCreated(campaign=_out(db, c), **_added(added, skipped))


@router.get("/campaigns/{campaign_id}", response_model=WaCampaignOut)
def get_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    return _out(db, _get(db, campaign_id, p))


@router.patch("/campaigns/{campaign_id}", response_model=WaCampaignOut)
def update_campaign(campaign_id: str, body: WaCampaignPatch, p: CurrentPrincipal, db: DB):
    c, _ = _get_editable(db, campaign_id, p)
    ensure_client_active(db, c.client_id)     # solo lectura (H12): pausar y cancelar si se puede
    changes = body.model_dump(exclude_unset=True)
    # null es "sin cambio", salvo agent_id (null: el agente del numero).
    changes = {k: v for k, v in changes.items() if v is not None or k == "agent_id"}
    campaigns.update(db, c, **changes)
    db.commit()
    return _out(db, c)


@router.delete("/campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    """Solo en borrador (409 si ya empezo: se cancela)."""
    c, _ = _get_editable(db, campaign_id, p)
    campaigns.delete(db, c)
    db.commit()


@router.post("/campaigns/{campaign_id}/recipients", response_model=WaRecipientsAdded)
def add_recipients(campaign_id: str, body: WaRecipientsIn, p: CurrentPrincipal, db: DB):
    """Suma contactos a una campaña en borrador o pausada."""
    c, _ = _get_editable(db, campaign_id, p)
    ensure_client_active(db, c.client_id)
    added, skipped = campaigns.add_recipients(db, c, _rows(body))
    db.commit()
    return _added(added, skipped)


@router.get("/campaigns/{campaign_id}/recipients", response_model=WaRecipientPage)
def list_recipients(campaign_id: str, p: CurrentPrincipal, db: DB,
                    status: str | None = Query(default=None, description="pending, sent, delivered, read, "
                                                                          "replied, failed o skipped"),
                    offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=500)):
    c = _get(db, campaign_id, p)
    rows, total = campaigns.recipients_page(db, c.id, status, offset, limit)
    items = []
    for r, m in rows:
        failed_later = r.status == "sent" and m is not None and m.status == "failed"
        items.append(WaRecipientOut(
            id=r.id, wa_id=r.wa_id, name=r.name, params=list(r.params or []),
            status=campaigns.shown_status(r.status, m.status if m else None, r.replied_at is not None),
            error=(m.error if failed_later else r.error), sent_at=r.sent_at, replied_at=r.replied_at,
            conversation_id=r.conversation_id))
    return WaRecipientPage(items=items, total=total)


@router.post("/campaigns/{campaign_id}/start", response_model=WaCampaignOut)
async def start_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    """Empieza o retoma el envio. Relee la plantilla en Meta: si la pausaron, la rechazaron
    o le cambiaron las variables, no arranca (422)."""
    c, account = _get_editable(db, campaign_id, p)
    ensure_client_active(db, c.client_id)
    template = await campaigns.fetch_template(db, account, c.template_name, c.template_language)
    if template.params != c.template_params:
        raise Invalid(f"La plantilla ahora tiene {template.params} variables y la campaña se cargó con "
                      f"{c.template_params}: creá otra campaña")
    c.template_body, c.template_category = template.body, template.category
    campaigns.start(db, c, account)
    db.commit()
    return _out(db, c)


@router.post("/campaigns/{campaign_id}/pause", response_model=WaCampaignOut)
def pause_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    c = _get(db, campaign_id, p)
    campaigns.pause(db, c)
    db.commit()
    return _out(db, c)


@router.post("/campaigns/{campaign_id}/cancel", response_model=WaCampaignOut)
def cancel_campaign(campaign_id: str, p: CurrentPrincipal, db: DB):
    """Termina la campaña: los pendientes no se mandan. Las respuestas siguen llegando al agente."""
    c = _get(db, campaign_id, p)
    campaigns.cancel(db, c)
    db.commit()
    return _out(db, c)


# --- Bajas ---

def _optout_out(o) -> WaOptoutOut:
    return WaOptoutOut(client_id=o.client_id, wa_id=o.wa_id, source=o.source, created_at=o.created_at)


@router.get("/optouts", response_model=list[WaOptoutOut])
def list_optouts(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    return [_optout_out(o) for o in campaigns.list_optouts(db, scoped_client_id(p, client_id))]


@router.post("/optouts", response_model=WaOptoutOut, status_code=201)
def add_optout(body: WaOptoutIn, p: CurrentPrincipal, db: DB):
    """Agrega un numero a la lista de bajas del cliente (ninguna campaña le escribe)."""
    client_id = body.client_id if p.is_admin else p.client_id
    if not client_id or db.get(Client, client_id) is None:
        raise NotFound("Cliente inexistente")
    ensure_access(p, client_id)
    try:
        wa_id = campaigns.normalize_phone(body.phone)
    except ValueError as e:
        raise Invalid(f"Teléfono inválido: {e}") from None
    o = campaigns.add_optout(db, client_id, wa_id, "manual")
    db.commit()
    return _optout_out(o)


@router.delete("/optouts/{wa_id}", status_code=204)
def remove_optout(wa_id: str, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Saca un numero de la lista de bajas (por ejemplo, si volvio a pedir que le escriban)."""
    client_id = client_id if p.is_admin else p.client_id
    if not client_id:
        raise NotFound("Falta client_id")
    ensure_access(p, client_id)
    # Sacar una baja habilita envios: no con el cliente inactivo (H12). Agregarla si: protege.
    ensure_client_active(db, client_id)
    campaigns.remove_optout(db, client_id, wa_id)
    db.commit()
