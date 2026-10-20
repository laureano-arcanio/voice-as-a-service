"""Link publico para llamar a un agente desde el navegador (docs/LINK_LLAMADA_PLAN.md).

- `/agents/{agent_id}/call-link`: lo gestiona el cliente (o un admin), uno activo por agente.
- `/public/call-links/{token}`: la usa la pagina publica (sin auth; Turnstile al llamar).
"""
from fastapi import APIRouter, Request, Response

from ...models import CallLink, Client
from ...services import call_links as service
from ...services import limits as limits_service
from ...services.errors import NotFound
from ..deps import DB, CurrentPrincipal, Engine, client_ip
from ..schemas import (
    CallLinkIn,
    CallLinkOut,
    CallLinkPatch,
    CallLinkStateOut,
    CallLinkUsageOut,
    PublicLinkCallIn,
    PublicLinkCallOut,
    PublicLinkOut,
)
from .agents import get_agent

router = APIRouter(tags=["call-links"])

PUBLIC_ERRORS = {404: {"description": "Link inexistente o revocado"},
                 429: {"description": "busy (lineas ocupadas) o rate_limited (llamadas seguidas desde la IP)"},
                 503: {"description": "unavailable (pausado, cliente inactivo, sin minutos o sin configurar)"}}


def _out(db, link: CallLink) -> CallLinkOut:
    usage = CallLinkUsageOut(**service.usage(db, link).__dict__)
    return CallLinkOut.model_validate({**{k: getattr(link, k) for k in CallLinkOut.model_fields
                                          if k not in ("url", "usage")},
                                       "url": service.url(link), "usage": usage})


def _user_id(p) -> str | None:
    return p.id if p.kind == "user" else None


def _link(db, agent_id: str) -> CallLink:
    link = service.for_agent(db, agent_id)
    if link is None:
        raise NotFound("El agente no tiene link", "call_link_not_found")
    return link


@router.get("/agents/{agent_id}/call-link", response_model=CallLinkStateOut)
def read_link(agent_id: str, p: CurrentPrincipal, db: DB):
    """El link del agente (o null) y cuantos permite el plan."""
    agent = get_agent(db, p, agent_id)
    client = db.get(Client, agent.client_id)
    link = service.for_agent(db, agent.id)
    return CallLinkStateOut(
        link=_out(db, link) if link else None,
        plan_max=limits_service.effective_limits(db, client).max_call_links,
        plan_used=service.active_count(db, client.id), enabled=service.enabled(),
        default_display_name=(agent.definition.get("agent") or {}).get("name") or agent.name,
        default_company_name=client.name)


@router.post("/agents/{agent_id}/call-link", response_model=CallLinkOut, status_code=201,
             responses={409: {"description": "El agente ya tiene link"},
                        429: {"description": "call_links_limit: el plan no incluye mas links"}})
def create_link(agent_id: str, body: CallLinkIn, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    link = service.create(db, agent, _user_id(p), **body.model_dump())
    db.commit()
    return _out(db, link)


@router.patch("/agents/{agent_id}/call-link", response_model=CallLinkOut)
def update_link(agent_id: str, body: CallLinkPatch, p: CurrentPrincipal, db: DB):
    """Textos, topes y pausa. Un tope en null lo deja sin tope propio (solo los del plan)."""
    agent = get_agent(db, p, agent_id)
    link = service.update(db, _link(db, agent.id), body.model_dump(exclude_unset=True))
    db.commit()
    return _out(db, link)


@router.post("/agents/{agent_id}/call-link/rotate", response_model=CallLinkOut)
def rotate_link(agent_id: str, p: CurrentPrincipal, db: DB):
    """Crea un link nuevo con la misma configuracion; el actual deja de funcionar."""
    agent = get_agent(db, p, agent_id)
    link = service.rotate(db, _link(db, agent.id), _user_id(p))
    db.commit()
    return _out(db, link)


@router.delete("/agents/{agent_id}/call-link", status_code=204, response_class=Response)
def delete_link(agent_id: str, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    service.revoke(db, _link(db, agent.id))
    db.commit()
    return Response(status_code=204)


@router.get("/public/call-links/{token}", response_model=PublicLinkOut, responses={404: PUBLIC_ERRORS[404]})
def public_link(token: str, db: DB):
    """Lo que muestra la pagina publica del link."""
    view = service.public_view(db, token)
    return PublicLinkOut(**{k: v for k, v in view.__dict__.items() if k != "token"})


@router.post("/public/call-links/{token}/calls", response_model=PublicLinkCallOut, status_code=201,
             responses={403: {"description": "captcha_failed"}, **PUBLIC_ERRORS})
async def public_call(token: str, body: PublicLinkCallIn, request: Request, db: DB, engine: Engine):
    """Empieza la llamada: devuelve la URL y el token de LiveKit para entrar a la room."""
    started = await service.start_call(db, engine, token, body.turnstile_token, client_ip(request))
    return PublicLinkCallOut(**started.__dict__)
