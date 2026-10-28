"""Aceptacion de las condiciones y botones de arrepentimiento y de baja (docs/features/LEGAL.md).

- `record`: una fila de legal_acceptances por documento, en la transaccion de quien la llama (el registro la
  guarda junto con la cuenta: sin aceptacion no hay cuenta).
- `pending`: los documentos vigentes que un usuario de cliente no acepto; el panel no deja seguir sin aceptarlos.
- `submit_request`: el pedido de los botones de la landing; el codigo sale por mail en el momento.
"""
import asyncio
import datetime
import secrets
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import legal
from ..config import settings
from ..db import utcnow
from ..mail import messages, notify
from ..models import Client, ConsumerRequest, LegalAcceptance, Role, User
from .demo import verify_turnstile
from .errors import Conflict, Forbidden, NotFound
from .ratelimit import Limit, RateLimiter, client_key

HOUR, DAY = 3600, 86_400
limiter = RateLimiter()
CODE_PREFIX = {"revocation": "ARR", "cancellation": "BAJ"}
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin 0/O ni 1/I: se dictan por telefono


class TermsOutdated(Conflict):
    """El formulario mostro otra version (la pagina quedo abierta mientras se publicaba una nueva)."""


def check_versions(terms_version: str, privacy_version: str) -> list[legal.Version]:
    """Las versiones vigentes, si son las que vio el usuario; si no, 409 terms_outdated."""
    current = {v.doc.id: v for v in legal.current_all()}
    if (terms_version, privacy_version) != (current["terms"].version, current["privacy"].version):
        raise TermsOutdated("Las condiciones cambiaron mientras completabas el formulario. Recargá la página para "
                            "ver la versión vigente.", "terms_outdated")
    return list(current.values())


def record(s: Session, user: User, client: Client | None, accepted: list[legal.Version], statement: str,
           channel: str, ip: str, user_agent: str) -> datetime.datetime:
    """Agrega la aceptacion de cada version (sin commit), con el texto que vio el usuario. Devuelve el momento,
    para el mail."""
    now = utcnow()
    for v in accepted:
        s.add(LegalAcceptance(created_at=now, user_id=user.id, client_id=user.client_id, email=user.email,
                              client_name=client.name if client else "", document=v.doc.id, version=v.version,
                              sha256=v.sha256, statement=statement, channel=channel, ip=ip[:45],
                              user_agent=user_agent[:512]))
    return now


def pending(s: Session, user: User) -> list[legal.Version]:
    """Versiones vigentes que el usuario no acepto. Solo usuarios de cliente: los admin somos nosotros."""
    if user.role != Role.client:
        return []
    done = set(s.execute(select(LegalAcceptance.document, LegalAcceptance.version)
                         .where(LegalAcceptance.user_id == user.id)).tuples())
    return [v for v in legal.current_all() if (v.doc.id, v.version) not in done]


def panel_text(accepted: list[legal.Version]) -> str:
    """La casilla del panel (web/src/features/auth/LegalModal.tsx) y los links que muestra arriba."""
    return (PANEL_CHECKBOX + " Versiones: " + ", ".join(f"{v.doc.title} {v.version}" for v in accepted) + ".")


PANEL_CHECKBOX = "Leí y acepto las condiciones del servicio y la política de privacidad."


def accept(s: Session, user: User, terms_version: str, privacy_version: str, ip: str, user_agent: str) -> None:
    """Aceptacion desde el panel (invitados, clientes de antes del registro con casilla, versiones nuevas): de los
    documentos pendientes, que tienen que venir con su version vigente (los ya aceptados pueden venir vacios)."""
    todo = pending(s, user)
    if not todo:
        return
    given = {"terms": terms_version, "privacy": privacy_version}
    if any(given[v.doc.id] != v.version for v in todo):
        raise TermsOutdated("Hay una versión más nueva de las condiciones. Recargá la página para verla.",
                            "terms_outdated")
    client = s.get(Client, user.client_id) if user.client_id else None
    accepted = todo
    moment = record(s, user, client, accepted, panel_text(accepted), "panel", ip, user_agent)
    s.commit()
    notify.deliver([messages.legal_accepted(email=user.email, name=user.name, client_name=client.name if client else "",
                                            accepted=accepted, accepted_at=moment)])


# ---------- botones de arrepentimiento y de baja ----------

@dataclass(frozen=True)
class RequestData:
    kind: str       # revocation | cancellation
    name: str
    email: str
    company: str = ""
    message: str = ""


def _new_code(kind: str) -> str:
    return f"{CODE_PREFIX[kind]}-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def _admin_to() -> list[str]:
    return [a.strip() for a in (settings.contact_to or settings.support_email).split(",") if a.strip()]


def create_request(s: Session, data: RequestData, ip: str) -> ConsumerRequest:
    email = data.email.strip().lower()
    user = s.scalar(select(User).where(User.email == email, User.role == Role.client))
    row = ConsumerRequest(kind=data.kind, code=_new_code(data.kind), name=data.name.strip(), email=email,
                          company=data.company.strip(), message=data.message.strip(), ip=ip[:45],
                          client_id=user.client_id if user else None)
    s.add(row)
    s.commit()
    # El codigo al que pidio, en el momento (Disp. 954/2025: dentro de las 24 h); el estado queda en la fila.
    sent = notify.send(messages.consumer_request_received(email=email, name=row.name, kind=row.kind, code=row.code,
                                                   created_at=row.created_at))
    row.email_status = sent.status
    s.commit()
    client_url = f"{settings.app_url.rstrip('/')}/clients/{row.client_id}" if row.client_id else None
    notify.deliver([messages.consumer_request_admin(to=to, kind=row.kind, code=row.code, name=row.name, email=email,
                                                    company=row.company, message=row.message,
                                                    client_url=client_url) for to in _admin_to()])
    return row


async def submit_request(s: Session, data: RequestData, turnstile_token: str, ip: str) -> ConsumerRequest:
    """Sin cuenta ni registro previo (lo exige la norma); Turnstile y un tope por IP frenan el abuso."""
    key = f"consumer:{client_key(ip)}"
    limiter.check(key, [Limit(5, HOUR), Limit(20, DAY)], "Ya recibimos varios pedidos desde esta conexión. "
                  f"Si necesitás algo más, escribinos a {settings.support_email}.")
    if not await verify_turnstile(turnstile_token, ip):
        raise Forbidden("No pudimos verificar que seas una persona. Recargá la página.", "captcha_failed")
    limiter.hit(key)
    return await asyncio.to_thread(create_request, s, data, ip)


def acceptance_counts(s: Session) -> dict[tuple[str, str], int]:
    """Aceptaciones por (documento, version), para la pantalla Legales del admin."""
    q = select(LegalAcceptance.document, LegalAcceptance.version, func.count()).group_by(
        LegalAcceptance.document, LegalAcceptance.version)
    return {(doc, version): n for doc, version, n in s.execute(q)}


def find_version(doc_id: str, version: str) -> legal.Version:
    v = next((v for v in legal.versions(doc_id) if v.version == version), None) if doc_id in legal.BY_ID else None
    if v is None:
        raise NotFound("Versión no encontrada", "legal_version_not_found")
    return v


def list_requests(s: Session, status: str | None = None, limit: int = 100) -> list[ConsumerRequest]:
    q = select(ConsumerRequest).order_by(ConsumerRequest.created_at.desc()).limit(limit)
    if status:
        q = q.where(ConsumerRequest.status == status)
    return list(s.scalars(q))


def resolve_request(s: Session, request_id: str, status: str, resolution: str) -> ConsumerRequest:
    row = s.get(ConsumerRequest, request_id)
    if row is None:
        raise NotFound("Pedido no encontrado", "consumer_request_not_found")
    row.status, row.resolution = status, resolution.strip()
    row.resolved_at = utcnow() if status != "open" else None
    s.commit()
    return row
