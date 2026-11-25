"""Equipo del cliente, areas de derivacion y eventos (docs/features/EQUIPO_TELEFONIA.md). El cliente ve y carga
lo suyo; un admin indica `client_id`. La escritura es de un Admin del cliente; dar acceso, rol o invitación y
borrar a una persona con usuario, solo con la sesión del panel (ni API key ni OAuth)."""
import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from ...config import settings
from ...mail import notify
from ...models import Client, HandoffArea, User
from ...services import events as events_service
from ...services import handoff, team_access
from ...services.errors import Forbidden, Invalid, NotFound
from ...services.ratelimit import Limit, RateLimited
from ...services.security import Principal
from ..deps import DB, ClientAdminPrincipal, CurrentPrincipal, api_limiter, scoped_client_id
from ..schemas import (
    EventOut,
    HandoffAreaIn,
    HandoffAreaOut,
    HandoffAreaPatch,
    HandoffDefaultsOut,
    HoldMusicOut,
    InviteOut,
    TeamMemberCreatedOut,
    TeamMemberIn,
    TeamMemberOut,
    TeamMemberPatch,
)

router = APIRouter(tags=["handoff"])
HOUR = 3600


def _client(db, p: Principal, client_id: str | None) -> Client:
    cid = scoped_client_id(p, client_id)
    if cid is None:
        raise Invalid("Indicá client_id")
    client = db.get(Client, cid)
    if client is None:
        raise NotFound("Cliente inexistente")
    return client


def _require_panel(p: Principal) -> None:
    """Dar acceso, rol o invitación y borrar a una persona con usuario: solo desde el panel."""
    if p.kind != "user" or p.oauth:
        raise Forbidden("Esta acción se hace desde el panel, con la sesión de un Admin", "panel_user_required")


def _invite_limit(client_id: str) -> None:
    try:
        api_limiter.consume(f"team_invites:{client_id}", [Limit(settings.team_invites_per_hour, HOUR)],
                            "Mandaste muchas invitaciones. Probá de nuevo en un rato.")
    except RateLimited as e:
        e.code = "too_many_invites"
        raise


def _out(db, member) -> TeamMemberOut:
    user = db.get(User, member.user_id) if member.user_id else None
    return TeamMemberOut.model_validate(member).model_copy(update={
        "email": user.email if user else None,
        "role": user.client_role if user else None,
        "panel_access": bool(user and user.active),
        "last_login_at": user.last_login_at if user else None,
    })


def _area_out(db, area: HandoffArea) -> HandoffAreaOut:
    return HandoffAreaOut.model_validate({
        **{c: getattr(area, c) for c in HandoffAreaOut.model_fields if hasattr(area, c)},
        "member_ids": handoff.area_member_ids(db, area.id),
        "schedule_text": handoff.describe_schedule(area.schedule),
        "open_now": handoff.is_open(area.schedule),
        "messages": area.messages or {},
    })


# ---------- equipo ----------

@router.get("/team", response_model=list[TeamMemberOut])
def list_team(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    return [_out(db, m) for m in handoff.list_members(db, scoped_client_id(p, client_id))]


@router.post("/team", response_model=TeamMemberCreatedOut, status_code=201)
def create_member(body: TeamMemberIn, p: ClientAdminPrincipal, db: DB, client_id: str | None = None):
    """Suma una persona al equipo. El teléfono (Argentina) sirve para transferirle llamadas y, con
    `whatsapp_notify`, para avisarle por WhatsApp. Cuenta para el tope del plan (`max_team_members`).
    Con `email` le da acceso al panel (rol `user` por defecto) y le manda la invitación."""
    client = _client(db, p, client_id)
    if body.email or body.role:
        _require_panel(p)
    if body.role and not body.email:
        raise Invalid("Para darle un rol a una persona, dale acceso al panel con su email", "access_required")
    if body.email:
        _invite_limit(client.id)
    member = handoff.create_member(db, client, name=body.name, phone=body.phone, active=body.active,
                                   whatsapp_notify=body.whatsapp_notify, with_access=bool(body.email))
    user = team_access.give_access(db, member, str(body.email), body.role) if body.email else None
    db.commit()
    invite = None
    if user is not None:
        result = notify.invite(user, client)
        invite = InviteOut(email=user.email, status=result.status, error=result.error)
    return TeamMemberCreatedOut(**_out(db, member).model_dump(), invite=invite)


@router.patch("/team/{member_id}", response_model=TeamMemberCreatedOut)
def update_member(member_id: str, body: TeamMemberPatch, p: ClientAdminPrincipal, db: DB):
    member = handoff.get_member(db, scoped_client_id(p, None), member_id)
    changes = body.model_dump(exclude_unset=True)
    email = changes.pop("email", None)
    role = changes.pop("role", None)
    panel_access = changes.pop("panel_access", None)
    user = db.get(User, member.user_id) if member.user_id else None
    touched_access = email is not None or role is not None or panel_access is not None
    if touched_access:
        _require_panel(p)
    if email is not None and user is not None:
        raise Invalid("Esta persona ya tiene acceso al panel: el email lo cambia en Perfil con un código",
                      "email_readonly")
    if panel_access is False and user is None:
        raise Invalid("Esa persona no tiene acceso al panel", "no_panel_access")
    if role is not None and user is None and email is None:
        raise Invalid("Para darle un rol a una persona, dale acceso al panel con su email", "access_required")
    if user is not None and user.id == p.id:
        if panel_access is False:
            raise Invalid("No podés quitarte tu propio acceso al panel", "own_access")
    new_user = None
    if email is not None:
        if panel_access is False:
            raise Invalid("No se puede dar acceso y quitarlo en el mismo pedido", "invalid_access")
        _invite_limit(member.client_id)
        new_user = team_access.give_access(db, member, str(email), role)
        user = new_user
    if user is not None:
        final_role = role if role is not None else user.client_role
        if panel_access is True and not user.active:
            user.active = True
        if panel_access is False and user.active:
            team_access.check_keeps_admin(db, user, client_role=final_role, active=False)
            user.active = False
            user.session_version += 1
        if role is not None and role != user.client_role:
            team_access.check_keeps_admin(db, user, client_role=role, active=user.active)
            user.client_role = role
    handoff.update_member(db, member, **changes)
    db.commit()
    invite = None
    if new_user is not None:
        result = notify.invite(new_user, db.get(Client, member.client_id))
        invite = InviteOut(email=new_user.email, status=result.status, error=result.error)
    return TeamMemberCreatedOut(**_out(db, member).model_dump(), invite=invite)


@router.post("/team/{member_id}/invite", response_model=InviteOut)
def invite_member(member_id: str, p: ClientAdminPrincipal, db: DB):
    """Reenvía la invitación para crear la clave (usuario activo del panel)."""
    _require_panel(p)
    member = handoff.get_member(db, scoped_client_id(p, None), member_id)
    user = db.get(User, member.user_id) if member.user_id else None
    if user is None or not user.active:
        raise Invalid("Solo se invita a una persona con acceso al panel activo", "invalid_user")
    _invite_limit(member.client_id)
    result = notify.invite(user, db.get(Client, member.client_id))
    return InviteOut(email=user.email, status=result.status, error=result.error)


@router.delete("/team/{member_id}", status_code=204)
def delete_member(member_id: str, p: ClientAdminPrincipal, db: DB):
    """Saca a la persona. Si tiene usuario, borra también su acceso (las llamadas viejas quedan sin usuario);
    para conservarlo, quitale el acceso con `panel_access: false`."""
    member = handoff.get_member(db, scoped_client_id(p, None), member_id)
    user = db.get(User, member.user_id) if member.user_id else None
    if user is not None:
        _require_panel(p)
        if user.id == p.id:
            raise Invalid("No podés borrarte a vos mismo del equipo", "own_member")
        team_access.check_keeps_admin(db, user, client_role=None, active=False)
        handoff.delete_member_and_user(db, member)
    else:
        handoff.delete_member(db, member)
    db.commit()


# ---------- areas ----------

@router.get("/handoff-areas/defaults", response_model=HandoffDefaultsOut)
def area_defaults(p: CurrentPrincipal):
    """Los mensajes por defecto de un área y las variables que aceptan. También aceptan las variables que trae
    la herramienta de «Antes de la conversación» del agente, por su nombre (`{{nota_operador}}`)."""
    return HandoffDefaultsOut(messages=handoff.DEFAULT_MESSAGES,
                              variables=["area", "persona", "cliente", "resumen", "horario", "nombre"],
                              pre_accept_messages=list(handoff.PRE_ACCEPT_MESSAGES),
                              pre_accept_variables=list(handoff.PRE_ACCEPT_VARIABLES))


@router.get("/hold-music", response_model=HoldMusicOut)
def hold_music(p: CurrentPrincipal):
    """Temas de música de espera para la derivación (`handoff.hold_music.track` del agente)."""
    return HoldMusicOut(tracks=handoff.hold_tracks())


@router.get("/handoff-areas", response_model=list[HandoffAreaOut])
def list_areas(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    return [_area_out(db, a) for a in handoff.list_areas(db, scoped_client_id(p, client_id))]


@router.post("/handoff-areas", response_model=HandoffAreaOut, status_code=201)
def create_area(body: HandoffAreaIn, p: ClientAdminPrincipal, db: DB, client_id: str | None = None):
    """Crea un área de derivación: a quién se llama, en qué orden y horario, qué dice el agente, a qué área
    pasa fuera de horario o si nadie acepta (otra área o una persona), y si solo avisa por WhatsApp (`delivery`)."""
    data = body.model_dump(mode="json")
    area = handoff.create_area(db, _client(db, p, client_id).id, **data)
    db.commit()
    return _area_out(db, area)


@router.get("/handoff-areas/{area_id}", response_model=HandoffAreaOut)
def get_area(area_id: str, p: CurrentPrincipal, db: DB):
    return _area_out(db, handoff.get_area(db, scoped_client_id(p, None), area_id))


@router.patch("/handoff-areas/{area_id}", response_model=HandoffAreaOut)
def update_area(area_id: str, body: HandoffAreaPatch, p: ClientAdminPrincipal, db: DB):
    """Cambia un área. `schedule: null` la deja atendiendo siempre; `member_ids` reemplaza la lista;
    `after_hours_area_id`, `no_answer_area_id`, `no_answer_member_id` y `whatsapp` en null quitan la ruta, la
    persona de «si nadie atiende» o las plantillas. `no_answer_area_id` y `no_answer_member_id` son excluyentes."""
    area = handoff.get_area(db, scoped_client_id(p, None), area_id)
    handoff.update_area(db, area, **body.model_dump(mode="json", exclude_unset=True))
    db.commit()
    return _area_out(db, area)


@router.delete("/handoff-areas/{area_id}", status_code=204)
def delete_area(area_id: str, p: ClientAdminPrincipal, db: DB):
    handoff.delete_area(db, handoff.get_area(db, scoped_client_id(p, None), area_id))
    db.commit()


# ---------- eventos ----------

@router.get("/events", response_model=list[EventOut])
def list_events(p: CurrentPrincipal, db: DB, client_id: str | None = None, conversation_id: str | None = None,
                type: Annotated[list[str] | None, Query(description='Tipos exactos o prefijos ("handoff.")')] = None,
                since: datetime.datetime | None = None, until: datetime.datetime | None = None,
                after_id: Annotated[int | None, Query(description="Cursor: el último id leído")] = None,
                limit: Annotated[int, Query(ge=1, le=1000)] = 100):
    """Eventos en orden de llegada: llamadas (timbre, atención, fin), derivaciones y esperas. Para leer
    lo nuevo, repetir con `after_id` = el último id recibido."""
    def naive(d: datetime.datetime | None):
        return d.astimezone(datetime.UTC).replace(tzinfo=None) if d and d.tzinfo else d
    return events_service.list_events(db, scoped_client_id(p, client_id), conversation_id=conversation_id,
                                      types=type, since=naive(since), until=naive(until), after_id=after_id,
                                      limit=limit)
