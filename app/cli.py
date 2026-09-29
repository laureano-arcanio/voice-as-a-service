"""Tareas de administracion por linea de comandos.

    python -m app.cli seed                       # idempotente; lo corre `make migrate`
    python -m app.cli create-admin EMAIL         # pide la clave
    python -m app.cli create-api-key CLIENTE_SLUG NOMBRE

seed deja lo minimo para operar despues de migrar:
- tier "Interno" (sin limites) y cliente "interno", para pruebas, loadtest y eval;
- un agente del cliente interno por cada plantilla (app/agents/templates);
- las conversaciones anteriores a los agentes, asociadas al agente de igual slug;
- el numero de Anura (ANURA_DID) del cliente interno, atendido por el agente
  WORKFLOW_ID (demo_booking_classic si no esta);
- el admin ADMIN_EMAIL / ADMIN_PASSWORD si no existe.
"""
import argparse
import getpass
import os
import sys

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .agents.templates import load_template, template_ids
from .config import settings
from .db import get_sessionmaker, utcnow
from .models import (
    Agent,
    ApiKey,
    CallRow,
    Client,
    ConversationRow,
    PhoneNumber,
    Role,
    Tier,
    User,
)
from .services import agents as agent_service
from .services.security import generate_api_key, hash_password

INTERNAL_TIER = "Interno"
INTERNAL_CLIENT = "interno"


def _log(msg: str) -> None:
    print(msg, flush=True)


def seed(s: Session) -> None:
    tier = s.scalar(select(Tier).where(Tier.name == INTERNAL_TIER))
    if tier is None:
        tier = Tier(name=INTERNAL_TIER, description="Sin limites: pruebas, loadtest y capacidad")
        s.add(tier)
        s.flush()
        _log(f"tier {INTERNAL_TIER} creado")
    client = s.scalar(select(Client).where(Client.slug == INTERNAL_CLIENT))
    if client is None:
        client = Client(name="Interno", slug=INTERNAL_CLIENT, tier_id=tier.id)
        s.add(client)
        s.flush()
        _log(f"cliente {INTERNAL_CLIENT} creado")

    existing = set(s.scalars(select(Agent.slug).where(Agent.client_id == client.id)))
    for tid in template_ids():
        if tid in existing:
            continue
        w = load_template(tid)
        agent_service.create_agent(s, client, name=tid, slug=tid, description=f"{w.agent.name}, {w.agent.role}",
                                   definition=None, template_id=tid, user_id=None)
        _log(f"agente {tid} creado")
    s.flush()

    agents = {a.slug: a for a in s.scalars(select(Agent).where(Agent.client_id == client.id))}
    moved = 0
    for slug, agent in agents.items():
        ids = list(s.scalars(select(ConversationRow.id).where(
            ConversationRow.agent_id.is_(None), ConversationRow.legacy_workflow_id == slug)))
        if not ids:
            continue
        s.execute(update(ConversationRow).where(ConversationRow.id.in_(ids))
                  .values(agent_id=agent.id, agent_version=1, client_id=client.id))
        s.execute(update(CallRow).where(CallRow.conversation_id.in_(ids)).values(client_id=client.id))
        moved += len(ids)
    if moved:
        _log(f"{moved} conversaciones anteriores asociadas a agentes de {INTERNAL_CLIENT}")

    did = os.getenv("ANURA_DID", "").strip()
    if did:
        e164 = f"+54{did}"
        if s.scalar(select(PhoneNumber).where(PhoneNumber.e164 == e164)) is None:
            inbound = agents.get(os.getenv("WORKFLOW_ID") or "demo_booking_classic")
            s.add(PhoneNumber(client_id=client.id, e164=e164, label="Anura", assigned_at=utcnow(),
                              agent_id=inbound.id if inbound else None))
            _log(f"numero {e164} asignado a {INTERNAL_CLIENT} ({inbound.slug if inbound else 'sin agente'})")

    if settings.admin_email and settings.admin_password:
        email = settings.admin_email.lower()
        if s.scalar(select(User).where(User.email == email)) is None:
            s.add(User(email=email, name="Admin", password_hash=hash_password(settings.admin_password),
                       role=Role.admin))
            _log(f"admin {email} creado")
    s.commit()


def create_admin(s: Session, email: str, password: str) -> None:
    if len(password) < 10:
        sys.exit("La clave necesita al menos 10 caracteres")
    email = email.lower()
    user = s.scalar(select(User).where(User.email == email))
    if user is not None:
        user.password_hash = hash_password(password)
        _log(f"clave de {email} actualizada")
    else:
        s.add(User(email=email, name="Admin", password_hash=hash_password(password), role=Role.admin))
        _log(f"admin {email} creado")
    s.commit()


def create_api_key(s: Session, client_slug: str, name: str) -> None:
    client = s.scalar(select(Client).where(Client.slug == client_slug))
    if client is None:
        sys.exit(f"cliente inexistente: {client_slug}")
    key, prefix, key_hash = generate_api_key()
    s.add(ApiKey(client_id=client.id, name=name, prefix=prefix, key_hash=key_hash))
    s.commit()
    print(key)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="datos minimos (idempotente)")
    p = sub.add_parser("create-admin", help="crea un admin o le cambia la clave")
    p.add_argument("email")
    p = sub.add_parser("create-api-key", help="API key de un cliente (se imprime una sola vez)")
    p.add_argument("client_slug")
    p.add_argument("name")
    args = parser.parse_args(argv)
    with get_sessionmaker()() as s:
        if args.cmd == "seed":
            seed(s)
        elif args.cmd == "create-admin":
            password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Clave: ")
            create_admin(s, args.email, password)
        elif args.cmd == "create-api-key":
            create_api_key(s, args.client_slug, args.name)


if __name__ == "__main__":
    main()
