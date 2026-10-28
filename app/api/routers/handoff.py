"""Equipo del cliente, areas de derivacion y eventos (docs/features/EQUIPO_TELEFONIA.md). El cliente ve y carga
lo suyo; un admin indica `client_id`."""
import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from ...models import Client, HandoffArea
from ...services import events as events_service
from ...services import handoff
from ...services.errors import Invalid, NotFound
from ...services.security import Principal
from ..deps import DB, CurrentPrincipal, scoped_client_id
from ..schemas import (
    EventOut,
    HandoffAreaIn,
    HandoffAreaOut,
    HandoffAreaPatch,
    HandoffDefaultsOut,
    HoldMusicOut,
    TeamMemberIn,
    TeamMemberOut,
    TeamMemberPatch,
)

router = APIRouter(tags=["handoff"])


def _client(db, p: Principal, client_id: str | None) -> Client:
    cid = scoped_client_id(p, client_id)
    if cid is None:
        raise Invalid("Indicá client_id")
    client = db.get(Client, cid)
    if client is None:
        raise NotFound("Cliente inexistente")
    return client


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
    return handoff.list_members(db, scoped_client_id(p, client_id))


@router.post("/team", response_model=TeamMemberOut, status_code=201)
def create_member(body: TeamMemberIn, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Suma una persona al equipo. El teléfono (Argentina) sirve para transferirle llamadas; el WhatsApp,
    para el puente de la bandeja. Cuenta para el tope del plan (`max_team_members`)."""
    member = handoff.create_member(db, _client(db, p, client_id), **body.model_dump())
    db.commit()
    return member


@router.patch("/team/{member_id}", response_model=TeamMemberOut)
def update_member(member_id: str, body: TeamMemberPatch, p: CurrentPrincipal, db: DB):
    member = handoff.get_member(db, scoped_client_id(p, None), member_id)
    handoff.update_member(db, member, **body.model_dump(exclude_unset=True))
    db.commit()
    return member


@router.delete("/team/{member_id}", status_code=204)
def delete_member(member_id: str, p: CurrentPrincipal, db: DB):
    handoff.delete_member(db, handoff.get_member(db, scoped_client_id(p, None), member_id))
    db.commit()


# ---------- areas ----------

@router.get("/handoff-areas/defaults", response_model=HandoffDefaultsOut)
def area_defaults(p: CurrentPrincipal):
    """Los mensajes por defecto de un área y las variables que aceptan."""
    return HandoffDefaultsOut(messages=handoff.DEFAULT_MESSAGES,
                              variables=["area", "persona", "cliente", "resumen", "horario"])


@router.get("/hold-music", response_model=HoldMusicOut)
def hold_music(p: CurrentPrincipal):
    """Temas de música de espera para la derivación (`handoff.hold_music.track` del agente)."""
    return HoldMusicOut(tracks=handoff.hold_tracks())


@router.get("/handoff-areas", response_model=list[HandoffAreaOut])
def list_areas(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    return [_area_out(db, a) for a in handoff.list_areas(db, scoped_client_id(p, client_id))]


@router.post("/handoff-areas", response_model=HandoffAreaOut, status_code=201)
def create_area(body: HandoffAreaIn, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Crea un área de derivación: a quién se llama, en qué orden y horario, y qué dice el agente."""
    data = body.model_dump(mode="json")
    area = handoff.create_area(db, _client(db, p, client_id).id, **data)
    db.commit()
    return _area_out(db, area)


@router.get("/handoff-areas/{area_id}", response_model=HandoffAreaOut)
def get_area(area_id: str, p: CurrentPrincipal, db: DB):
    return _area_out(db, handoff.get_area(db, scoped_client_id(p, None), area_id))


@router.patch("/handoff-areas/{area_id}", response_model=HandoffAreaOut)
def update_area(area_id: str, body: HandoffAreaPatch, p: CurrentPrincipal, db: DB):
    """Cambia un área. `schedule: null` la deja atendiendo siempre; `member_ids` reemplaza la lista."""
    area = handoff.get_area(db, scoped_client_id(p, None), area_id)
    handoff.update_area(db, area, **body.model_dump(mode="json", exclude_unset=True))
    db.commit()
    return _area_out(db, area)


@router.delete("/handoff-areas/{area_id}", status_code=204)
def delete_area(area_id: str, p: CurrentPrincipal, db: DB):
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
