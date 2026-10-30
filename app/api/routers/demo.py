from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import sessionmaker

from ... import legal as legal_docs
from ...billing import mp
from ...billing import service as billing
from ...config import settings
from ...services import contact, legal, signup
from ...services import demo as service
from ..deps import DB, Definitions, Engine, client_ip
from ..schemas import (
    ConsumerRequestCreated,
    ConsumerRequestIn,
    DemoCallIn,
    DemoCallOut,
    DemoCallResult,
    DemoContactIn,
    DemoSessionIn,
    DemoSessionOut,
    DemoTtsIn,
    LegalVersionOut,
    PublicPlanOut,
    PublicPlansOut,
    SignupCheckIn,
    SignupIn,
    SignupOut,
)
from .auth import legal_out

router = APIRouter(prefix="/demo", tags=["demo"])
_bearer = HTTPBearer(auto_error=False, description="Token de la sesion de demo o de la llamada")
Bearer = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def demo_session(creds: Bearer) -> str:
    return service.require_session(creds.credentials if creds else None)


DemoSession = Annotated[str, Depends(demo_session)]


@router.post("/sessions", response_model=DemoSessionOut, status_code=201)
async def create_session(body: DemoSessionIn, request: Request):
    """Canjea un token de Turnstile por una sesion corta para llamar y sintetizar."""
    token, expires_in = await service.create_session(body.turnstile_token, client_ip(request))
    return DemoSessionOut(token=token, expires_in=expires_in)


@router.post("/calls", response_model=DemoCallOut, status_code=201,
             responses={429: {"description": "Limite por IP, agentes ocupados o cupo diario agotado"}})
async def start_call(body: DemoCallIn, request: Request, _: DemoSession, db: DB, engine: Engine):
    """Llamada por navegador con un agente de la demo: devuelve el token de LiveKit y el del resultado."""
    started = await service.start_call(db, engine, body.agent, body.voice, client_ip(request))
    return DemoCallOut(**started.__dict__)


@router.get("/calls/{conversation_id}", response_model=DemoCallResult)
def call_result(conversation_id: str, creds: Bearer, db: DB, definitions: Definitions):
    """Estado y datos extraidos de la llamada, con el result_token de POST /demo/calls."""
    return service.call_result(db, definitions, conversation_id, creds.credentials if creds else None)


@router.post("/tts", response_class=StreamingResponse,
             responses={200: {"content": {"audio/wav": {}, "audio/pcm": {}}}})
async def synthesize(body: DemoTtsIn, request: Request, _: DemoSession, db: DB):
    """`format=wav` (default): el archivo completo. `format=pcm`: audio crudo (16 bits, mono, 24 kHz) que se
    transmite mientras se sintetiza, para reproducirlo con Web Audio sin esperar."""
    stream = await service.synthesize(sessionmaker(bind=db.get_bind()), body.voice, body.text, client_ip(request),
                                      body.format)
    return StreamingResponse(stream, media_type="audio/pcm" if body.format == "pcm" else "audio/wav",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/contact", status_code=204, response_class=Response,
             responses={429: {"description": "Limite por IP"}})
async def send_contact(body: DemoContactIn, request: Request, _: DemoSession, db: DB):
    """Formulario de contacto de la landing: guarda el pedido y avisa por mail (Resend)."""
    if not body.website:
        await contact.submit(db, contact.ContactData(
            name=body.name, company=body.company, email=body.email or "", phone=body.phone,
            message=body.message, page=body.page), client_ip(request))
    return Response(status_code=204)


@router.post("/signup", response_model=SignupOut, status_code=201,
             responses={409: {"description": "El email ya tiene cuenta (email_taken) o las condiciones cambiaron "
                                             "(terms_outdated)"},
                        422: {"description": "Falta aceptar las condiciones (terms_required)"},
                        429: {"description": "Limite por IP"}, 503: {"description": "Registro apagado"}})
async def create_account(body: SignupIn, request: Request, db: DB):
    """Registro desde la landing: crea el cliente en el plan gratuito con la clave elegida y devuelve el
    link de un solo uso que abre la sesion en el dashboard (y, con un plan pago, lleva a pagarlo)."""
    if body.website:   # trampa para bots: parece que anduvo
        return SignupOut(continue_url=settings.site_url)
    url = await signup.signup(db, signup.SignupData(company=body.company, name=body.name, email=str(body.email),
                                                    password=body.password, phone=body.phone, plan=body.plan,
                                                    card_token_id=body.card_token_id,
                                                    accept_terms=body.accept_terms,
                                                    terms_version=body.terms_version,
                                                    privacy_version=body.privacy_version, ip=client_ip(request),
                                                    user_agent=request.headers.get("user-agent", "")),
                              body.turnstile_token, client_ip(request))
    return SignupOut(continue_url=url)


@router.post("/signup/check", status_code=204, response_class=Response,
             responses={409: {"description": "El email ya tiene cuenta (email_taken)"},
                        422: {"description": "Email descartable"}, 429: {"description": "Limite por IP"}})
def check_signup_email(body: SignupCheckIn, request: Request, db: DB):
    """Antes del paso del pago del registro: si el email puede registrarse."""
    signup.check_email(db, str(body.email), client_ip(request))
    return Response(status_code=204)


@router.get("/plans", response_model=PublicPlansOut)
def public_plans(db: DB):
    """Planes con precio para el registro, y la public key de Mercado Pago si se paga con tarjeta."""
    return PublicPlansOut(
        mp_public_key=settings.mp_billing_public_key if mp.enabled() else None,
        plans=[PublicPlanOut(id=t.id, name=t.name, price_ars=t.price_ars)
               for t in billing.public_tiers(db) if t.price_ars])


@router.get("/legal", response_model=list[LegalVersionOut])
def legal_versions():
    """Versiones vigentes de las condiciones y la politica de privacidad: las que manda el registro."""
    return [legal_out(v) for v in legal_docs.current_all()]


@router.post("/consumer-requests", response_model=ConsumerRequestCreated, status_code=201,
             responses={403: {"description": "Turnstile invalido"}, 429: {"description": "Limite por IP"}})
async def consumer_request(body: ConsumerRequestIn, request: Request, db: DB):
    """Boton de arrepentimiento o de baja (Disp. 954/2025): sin cuenta. Devuelve el codigo de tramite y lo manda
    por mail al email del pedido."""
    if body.website:   # trampa para bots
        return ConsumerRequestCreated(code=legal._new_code(body.kind))
    row = await legal.submit_request(db, legal.RequestData(kind=body.kind, name=body.name, email=str(body.email),
                                                           company=body.company, message=body.message),
                                     body.turnstile_token, client_ip(request))
    return ConsumerRequestCreated(code=row.code)
