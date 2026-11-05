"""CLI de Registros: python -m registros.cli <comando> (make registros-cli ARGS=...)."""
import argparse
import getpass
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from sqlalchemy import delete, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from .auth import hash_password, new_api_key, normalize_email
from .db import get_sessionmaker
from .manifest import ManifestError, parse_manifest, sync_person
from .models import SCOPES, ApiKey, Person, Tenant, User, UserSession


class CliError(Exception):
    pass


def _tenant(s: Session, slug: str) -> Tenant:
    tenant = s.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None:
        raise CliError(f"No existe el tenant {slug}")
    return tenant


def create_tenant(s: Session, args: argparse.Namespace) -> None:
    try:
        amount = Decimal(args.amount)
    except InvalidOperation:
        raise CliError("--amount tiene que ser un número") from None
    if not amount.is_finite() or amount < 0:
        raise CliError("--amount no puede ser negativo")
    if s.scalar(select(Tenant).where(Tenant.slug == args.slug)):
        raise CliError(f"Ya existe el tenant {args.slug}")
    s.add(Tenant(slug=args.slug, name=args.name, charge_amount=amount, currency=args.currency))
    s.commit()
    print(f"Tenant {args.slug} creado")


def load_form(s: Session, args: argparse.Namespace) -> None:
    """Carga form.html, schema.json y manifest.json. Rehace nombres y teléfonos de las fichas ya
    cargadas, porque el manifiesto decide de dónde salen."""
    tenant = _tenant(s, args.tenant)
    folder = Path(args.dir)
    try:
        form_html = (folder / "form.html").read_text(encoding="utf-8")
        schema = json.loads((folder / "schema.json").read_text(encoding="utf-8"))
        raw_manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    except OSError as e:
        raise CliError(f"No se pudo leer el formulario: {e}") from None
    except ValueError as e:
        raise CliError(f"JSON inválido: {e}") from None
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        raise CliError(f"schema.json inválido: {e.message}") from None
    try:
        manifest = parse_manifest(raw_manifest)
    except ManifestError as e:
        raise CliError(f"manifest.json inválido: {e}") from None
    tenant.form_html, tenant.form_schema, tenant.manifest = form_html, schema, raw_manifest
    persons = list(s.scalars(select(Person).where(Person.tenant_id == tenant.id)))
    for person in persons:
        sync_person(s, person, manifest)
    s.commit()
    print(f"Formulario de {args.tenant} cargado; {len(persons)} fichas actualizadas")


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\n")
    return getpass.getpass("Clave: ")


def create_user(s: Session, args: argparse.Namespace) -> None:
    """Crea el usuario o, si ya existe, le cambia la clave y le cierra las sesiones."""
    tenant = _tenant(s, args.tenant)
    email = normalize_email(args.email)
    if "@" not in email:
        raise CliError("--email inválido")
    password = _read_password(args.password_stdin)
    if len(password) < 8:
        raise CliError("La clave necesita al menos 8 caracteres")
    user = s.scalar(select(User).where(User.tenant_id == tenant.id, User.email == email))
    if user is None:
        s.add(User(tenant_id=tenant.id, email=email, password_hash=hash_password(password)))
        verb = "creado"
    else:
        user.password_hash = hash_password(password)
        s.execute(delete(UserSession).where(UserSession.user_id == user.id))
        verb = "con clave nueva"
    s.commit()
    print(f"Usuario {email} {verb}")


def create_key(s: Session, args: argparse.Namespace) -> None:
    tenant = _tenant(s, args.tenant)
    key, key_hash = new_api_key()
    s.add(ApiKey(tenant_id=tenant.id, key_hash=key_hash, scope=args.scope, name=args.name))
    s.commit()
    print(key)  # no se vuelve a mostrar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="registros.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("create-tenant")
    p.add_argument("--slug", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--amount", required=True)
    p.add_argument("--currency", default="ARS")
    p.set_defaults(run=create_tenant)

    p = commands.add_parser("load-form")
    p.add_argument("--tenant", required=True)
    p.add_argument("--dir", required=True)
    p.set_defaults(run=load_form)

    p = commands.add_parser("create-user")
    p.add_argument("--tenant", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--password-stdin", action="store_true")
    p.set_defaults(run=create_user)

    p = commands.add_parser("create-key")
    p.add_argument("--tenant", required=True)
    p.add_argument("--scope", required=True, choices=SCOPES)
    p.add_argument("--name", required=True)
    p.set_defaults(run=create_key)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with get_sessionmaker()() as s:
        try:
            args.run(s, args)
        except CliError as e:
            print(e, file=sys.stderr)
            return 1
        except (IntegrityError, DataError):
            print("Dato inválido o en conflicto con uno existente", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
