from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...services import contact
from ...services import demo as service
from ..deps import DB, Definitions, Engine, client_ip
from ..schemas import (
    DemoCallIn,
    DemoCallOut,
    DemoCallResult,
    DemoContactIn,
    DemoSessionIn,
    DemoSessionOut,
    DemoTtsIn,
)

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
async def synthesize(body: DemoTtsIn, request: Request, _: DemoSession):
    """`format=wav` (default): el archivo completo. `format=pcm`: audio crudo (16 bits, mono, 24 kHz) que se
    transmite mientras se sintetiza, para reproducirlo con Web Audio sin esperar."""
    stream = await service.synthesize(body.voice, body.text, client_ip(request), body.format)
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
