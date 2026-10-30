"""Asistente de primera vez (docs/features/PRIMERA_VEZ.md): rubro y voz para crear el primer agente,
celular verificado por WhatsApp y llamada de prueba al celular."""
from fastapi import APIRouter, BackgroundTasks

from ...models import User
from ...services import onboarding as service
from ...services.errors import Invalid
from ..deps import DB, CurrentPrincipal, Engine, require_not_support, require_user
from ..schemas import (
    AgentDetail,
    CallMeIn,
    CallStartedOut,
    IndustryOut,
    OnboardingAgentIn,
    OnboardingOut,
    PhoneCodeIn,
    PhoneCodeOut,
    PhoneVerifyIn,
)
from .agents import _out, _pregenerate_opening
from .clients import get_client

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _client(db, p):
    if not p.client_id:
        raise Invalid("Falta el cliente: entrá como el cliente", "client_required")
    return get_client(db, p, p.client_id)


def _user(db, p) -> User | None:
    """El usuario de la sesion (no un admin en soporte ni una API key)."""
    return db.get(User, p.id) if p.kind == "user" and not p.support and not p.is_admin else None


def _session_user(db, p) -> User:
    require_user(p)
    require_not_support(p)
    return db.get(User, p.id)


@router.get("", response_model=OnboardingOut)
def get_status(p: CurrentPrincipal, db: DB):
    return service.status(db, _client(db, p), _user(db, p))


@router.get("/industries", response_model=list[IndustryOut])
def list_industries(_: CurrentPrincipal):
    return [IndustryOut(id=k, label=v.label, template_id=v.template_id) for k, v in service.INDUSTRIES.items()]


@router.post("/agent", response_model=AgentDetail, status_code=201)
def create_agent(body: OnboardingAgentIn, p: CurrentPrincipal, db: DB, background: BackgroundTasks):
    """Crea el agente de la plantilla del rubro con la empresa y la voz, y guarda el rubro y el sitio."""
    client = _client(db, p)
    agent = service.create_first_agent(db, client, p.id if p.kind == "user" else None, body.industry, body.voice,
                                       body.website)
    db.commit()
    _pregenerate_opening(background, agent)
    return _out(agent, detail=True)


@router.post("/phone/code", response_model=PhoneCodeOut,
             responses={503: {"description": "Sin verificación por WhatsApp configurada"}})
async def send_phone_code(body: PhoneCodeIn, p: CurrentPrincipal, db: DB):
    """Manda un código por WhatsApp al celular. Devuelve el desafío para verificarlo."""
    sent = await service.send_code(db, _session_user(db, p), body.phone)
    return PhoneCodeOut(challenge=sent.challenge, phone=sent.phone, expires_at=sent.expires_at)


@router.post("/phone/verify", response_model=OnboardingOut,
             responses={422: {"description": "Código incorrecto o vencido (invalid_code)"}})
def verify_phone(body: PhoneVerifyIn, p: CurrentPrincipal, db: DB):
    user = service.confirm_code(db, _session_user(db, p), body.challenge, body.code)
    return service.status(db, _client(db, p), user)


@router.post("/call-me", response_model=CallStartedOut, status_code=201,
             responses={409: {"description": "Celular sin verificar (phone_not_verified)"},
                        429: {"description": "Sin llamadas de prueba (trial_calls) o líneas ocupadas"}})
async def call_me(body: CallMeIn, p: CurrentPrincipal, db: DB, engine: Engine):
    """El agente llama al celular verificado del usuario (llamada de prueba, no gasta minutos del plan)."""
    started = await service.call_me(db, engine, p, _session_user(db, p), body.agent_id)
    return CallStartedOut(**started.__dict__)
