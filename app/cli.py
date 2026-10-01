"""Tareas de administracion por linea de comandos.

    python -m app.cli seed                       # idempotente; lo corre `make migrate`
    python -m app.cli create-admin EMAIL         # pide la clave
    python -m app.cli create-api-key CLIENTE_SLUG NOMBRE
    python -m app.cli wa-account PHONE_NUMBER_ID --waba WABA --display "+1 555 145 6632" \
        --client interno --agent SLUG [--name ...]   # conecta un numero de WhatsApp (idempotente)

seed deja lo minimo para operar despues de migrar:
- tier "Interno" (sin limites) y cliente "interno", para pruebas, loadtest y eval;
- un agente del cliente interno por cada plantilla (app/agents/templates);
- las conversaciones anteriores a los agentes, asociadas al agente de igual slug;
- el numero de Anura (ANURA_DID) del cliente interno, atendido por el agente
  WORKFLOW_ID (demo_booking_classic si no esta);
- tier "Landing" y cliente DEMO_CLIENT con un agente por plantilla landing_* (slug sin el
  prefijo), los que atiende la demo de la landing (/api/v1/demo);
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
DEMO_TIER = "Landing"
DEMO_TEMPLATE_PREFIX = "landing_"
DEMO_MAX_CONCURRENT_CALLS = 3


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

    seed_demo(s)

    if settings.admin_email and settings.admin_password:
        email = settings.admin_email.lower()
        if s.scalar(select(User).where(User.email == email)) is None:
            s.add(User(email=email, name="Admin", password_hash=hash_password(settings.admin_password),
                       role=Role.admin))
            _log(f"admin {email} creado")
    s.commit()


def seed_demo(s: Session) -> None:
    tier = s.scalar(select(Tier).where(Tier.name == DEMO_TIER))
    if tier is None:
        tier = Tier(name=DEMO_TIER, description="Demo de la landing: llamadas por navegador",
                    max_concurrent_calls=DEMO_MAX_CONCURRENT_CALLS, inbound_minutes=0, outbound_minutes=0,
                    max_phone_numbers=0)
        s.add(tier)
        s.flush()
        _log(f"tier {DEMO_TIER} creado")
    client = s.scalar(select(Client).where(Client.slug == settings.demo_client))
    if client is None:
        client = Client(name="Landing", slug=settings.demo_client, tier_id=tier.id)
        s.add(client)
        s.flush()
        _log(f"cliente {settings.demo_client} creado")
    existing = set(s.scalars(select(Agent.slug).where(Agent.client_id == client.id)))
    for tid in template_ids():
        slug = tid.removeprefix(DEMO_TEMPLATE_PREFIX)
        if not tid.startswith(DEMO_TEMPLATE_PREFIX) or slug in existing:
            continue
        w = load_template(tid)
        agent_service.create_agent(s, client, name=slug.capitalize(), slug=slug,
                                   description=f"{w.agent.name}, {w.agent.role}", definition=None,
                                   template_id=tid, user_id=None)
        _log(f"agente {slug} de {settings.demo_client} creado")
    s.flush()


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


def wa_account(s: Session, phone_number_id: str, waba_id: str, display: str, client_slug: str,
               agent_slug: str, name: str | None) -> None:
    """Crea la cuenta o le actualiza agente, numero visible y nombre. El token queda en
    NULL: se usa WA_ACCESS_TOKEN (system user de nuestro portafolio)."""
    from .services.errors import ServiceError
    from .whatsapp import store as wa_store

    client = s.scalar(select(Client).where(Client.slug == client_slug))
    if client is None:
        sys.exit(f"cliente inexistente: {client_slug}")
    agent = s.scalar(select(Agent).where(Agent.client_id == client.id, Agent.slug == agent_slug))
    if agent is None:
        sys.exit(f"el cliente {client_slug} no tiene el agente {agent_slug}")
    try:
        account = wa_store.account_by_pnid(s, phone_number_id.strip())
        if account is None:
            wa_store.create_account(s, client_id=client.id, agent_id=agent.id, phone_number_id=phone_number_id,
                                    waba_id=waba_id, display_phone_number=display, name=name or "")
            _log(f"cuenta de WhatsApp {phone_number_id} creada ({client_slug}/{agent_slug})")
        else:
            if account.client_id != client.id:
                sys.exit(f"el numero {phone_number_id} ya esta conectado a otro cliente")
            changes = {"agent_id": agent.id, "display_phone_number": display, "waba_id": waba_id}
            if name is not None:
                changes["name"] = name
            wa_store.update_account(s, account, **changes)
            _log(f"cuenta de WhatsApp {phone_number_id} actualizada ({client_slug}/{agent_slug})")
    except ServiceError as e:
        sys.exit(e.message)
    s.commit()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="datos minimos (idempotente)")
    p = sub.add_parser("create-admin", help="crea un admin o le cambia la clave")
    p.add_argument("email")
    p = sub.add_parser("create-api-key", help="API key de un cliente (se imprime una sola vez)")
    p.add_argument("client_slug")
    p.add_argument("name")
    p = sub.add_parser("wa-account", help="conecta un numero de WhatsApp a un agente (idempotente)")
    p.add_argument("phone_number_id")
    p.add_argument("--waba", required=True)
    p.add_argument("--display", required=True, help="numero visible, ej. '+1 555 145 6632'")
    p.add_argument("--client", default=INTERNAL_CLIENT, help="slug del cliente")
    p.add_argument("--agent", required=True, help="slug del agente que atiende")
    p.add_argument("--name", default=None)
    args = parser.parse_args(argv)
    with get_sessionmaker()() as s:
        if args.cmd == "seed":
            seed(s)
        elif args.cmd == "create-admin":
            password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Clave: ")
            create_admin(s, args.email, password)
        elif args.cmd == "create-api-key":
            create_api_key(s, args.client_slug, args.name)
        elif args.cmd == "wa-account":
            wa_account(s, args.phone_number_id, args.waba, args.display, args.client, args.agent, args.name)


if __name__ == "__main__":
    main()
