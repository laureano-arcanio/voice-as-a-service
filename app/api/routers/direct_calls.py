"""Llamadas directas (docs/features/EQUIPO_TELEFONIA.md): el equipo del cliente llama y atiende sin el agente.

- Saliente: POST /direct-calls (desde el panel devuelve el token; por API key o MCP, `user_id` y `join_url`).
- Volver a entrar, atender y rechazar: /direct-calls/{id}/join, /answer y /decline (sesion del panel).
- Presencia y timbre: PUT /me/presence (pulso cada ~20 s), GET /me/ringing y GET /team/presence.
- Aviso de grabacion: /clients/{id}/direct-call-settings.
Cortar es el POST /calls/{id}/hangup de siempre. Un admin en "ver como cliente" no llama ni atiende
(403 support_read_only), y hasta que el cliente acepta las condiciones 2026-10-28 (o posteriores) nadie llama
ni atiende (403 terms_pending, services/legal_gate.py).
"""
from fastapi import APIRouter

from ...services import direct_calls as service
from ...services.errors import Invalid
from ..deps import DB, CurrentPrincipal, scoped_client_id
from ..schemas import (
    DirectCallIn,
    DirectCallOut,
    DirectCallSettings,
    DirectJoinOut,
    PresenceIn,
    PresenceOut,
    RingingOut,
    TeamPresenceOut,
)
from .clients import get_client

router = APIRouter(tags=["direct-calls"])

ERRORS = {403: {"description": "Admin en soporte (support_read_only), número bloqueado (blocked_number), condiciones "
                               "de las llamadas directas sin aceptar (terms_pending) u otro usuario"},
          409: {"description": "Contacto dado de baja sin confirmar (opted_out), llamada terminada o ya atendida"},
          429: {"description": "Plan sin llamadas directas, sin minutos salientes, al tope de llamadas o sin "
                               "canales libres"}}


@router.post("/direct-calls", response_model=DirectCallOut, status_code=201, responses=ERRORS)
async def start_direct_call(body: DirectCallIn, p: CurrentPrincipal, db: DB):
    """Llama a un contacto (o a un número) desde un número del cliente: habla una persona desde el navegador,
    sin agente. Con la sesión del panel devuelve el token para entrar; por API key o MCP, `user_id` (quien va
    a hablar) es obligatorio y la respuesta trae `join_url`, la página del panel que entra con su sesión. El
    worker marca cuando el usuario entra a la room. Si el contacto pidió no recibir llamadas: 409 opted_out,
    salvo `confirm_opted_out: true` (queda registrado en la llamada)."""
    started = await service.start_direct_call(db, p, service.DirectCallRequest(**body.model_dump()))
    return DirectCallOut(**started.__dict__)


@router.post("/direct-calls/{conversation_id}/join", response_model=DirectJoinOut, responses=ERRORS)
def join_direct_call(conversation_id: str, p: CurrentPrincipal, db: DB):
    """Token nuevo para volver a entrar a la llamada (recargó la página o la abre por el join_url): solo el
    usuario de la llamada y mientras está activa."""
    return DirectJoinOut(**service.join(db, p, conversation_id).__dict__)


@router.post("/direct-calls/{conversation_id}/answer", response_model=DirectJoinOut, responses=ERRORS)
def answer_direct_call(conversation_id: str, p: CurrentPrincipal, db: DB):
    """Atiende en el panel una entrante que le suena: el primero que atiende se queda con la llamada y a los
    demás se les apaga (409 already_answered si ya la tomó otro)."""
    return DirectJoinOut(**service.answer(db, p, conversation_id).__dict__)


@router.post("/direct-calls/{conversation_id}/decline", status_code=204, responses=ERRORS)
def decline_direct_call(conversation_id: str, p: CurrentPrincipal, db: DB):
    """Rechaza el timbre propio; la llamada sigue sonando a los demás."""
    service.decline(db, p, conversation_id)


@router.put("/me/presence", response_model=PresenceOut, responses=ERRORS)
def set_presence(body: PresenceIn, p: CurrentPrincipal, db: DB):
    """Disponible en el panel para atender: el panel lo manda cada ~20 s mientras está prendido; sin pulso por
    60 s deja de estar disponible. `available: false` lo apaga ya."""
    return PresenceOut(**service.set_presence(db, p, body.available).__dict__)


@router.get("/me/ringing", response_model=list[RingingOut])
def my_ringing(p: CurrentPrincipal, db: DB):
    """Las entrantes que le suenan ahora al usuario en el panel."""
    return [RingingOut(**r.__dict__) for r in service.ringing(db, p)]


@router.get("/team/presence", response_model=list[TeamPresenceOut])
def team_presence(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Los usuarios del cliente: si están Disponibles en el panel y si están en una llamada."""
    cid = scoped_client_id(p, client_id)
    if cid is None:
        raise Invalid("Indicá client_id")
    return [TeamPresenceOut(**t.__dict__) for t in service.team_presence(db, cid)]


@router.get("/clients/{client_id}/direct-call-settings", response_model=DirectCallSettings)
def get_settings(client_id: str, p: CurrentPrincipal, db: DB):
    return service.get_settings(get_client(db, p, client_id))


@router.put("/clients/{client_id}/direct-call-settings", response_model=DirectCallSettings)
def update_settings(client_id: str, body: DirectCallSettings, p: CurrentPrincipal, db: DB):
    """Aviso "Esta llamada está siendo grabada" al empezar las llamadas directas (siempre se graban; avisar y
    tener el consentimiento es responsabilidad del cliente)."""
    return service.update_settings(db, get_client(db, p, client_id), body.recording_notice)
