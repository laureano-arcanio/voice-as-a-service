"""Dos keys: la del usuario (UI y scripts suyos: todo) y la de agentes (todo menos aprobar envios,
cargar historial, borrar y sincronizar GA). Asi "el agente no envia" queda en el servidor."""
import hmac
from typing import Annotated, Literal

from fastapi import Depends, Header

from .config import settings
from .services.errors import CrmError, Forbidden

Caller = Literal["usuario", "agente"]


class Unauthorized(CrmError):
    status = 401
    title = "Sin autorizacion"


def caller(authorization: Annotated[str | None, Header()] = None) -> Caller:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if settings.api_key and token and hmac.compare_digest(token, settings.api_key):
        return "usuario"
    if settings.agent_api_key and token and hmac.compare_digest(token, settings.agent_api_key):
        return "agente"
    raise Unauthorized("falta Authorization: Bearer <CRM_API_KEY o CRM_AGENT_API_KEY>")


def user_only(who: Annotated[Caller, Depends(caller)]) -> Caller:
    if who != "usuario":
        raise Forbidden("solo el usuario (CRM_API_KEY): los agentes dejan borradores")
    return who


Who = Annotated[Caller, Depends(caller)]
UserOnly = Annotated[Caller, Depends(user_only)]
