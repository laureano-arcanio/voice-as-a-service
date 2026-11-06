"""CLI de Registros: python -m registros.cli <comando> (make registros-cli ARGS=...)."""
import argparse
import getpass
import sys
from pathlib import Path

from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from . import admin_ops
from .admin_ops import OpsError
from .db import get_sessionmaker
from .models import SCOPES


def create_tenant(s: Session, args: argparse.Namespace) -> None:
    admin_ops.create_tenant(s, args.slug, args.name, args.amount, args.currency)
    s.commit()
    print(f"Tenant {args.slug} creado")


def load_form(s: Session, args: argparse.Namespace) -> None:
    """Carga form.html, schema.json y manifest.json y rehace nombres y teléfonos de las fichas ya cargadas."""
    tenant = admin_ops.tenant_by_slug(s, args.tenant)
    folder = Path(args.dir)
    try:
        texts = [(folder / name).read_text(encoding="utf-8") for name in ("form.html", "schema.json", "manifest.json")]
    except (OSError, ValueError) as e:
        raise OpsError(f"No se pudo leer el formulario: {e}") from None
    count = admin_ops.load_form(s, tenant, *texts)
    s.commit()
    print(f"Formulario de {args.tenant} cargado; {count} fichas actualizadas")


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\n")
    return getpass.getpass("Clave: ")


def create_user(s: Session, args: argparse.Namespace) -> None:
    """Crea el usuario o, si ya existe, le cambia la clave y le cierra las sesiones."""
    tenant = admin_ops.tenant_by_slug(s, args.tenant)
    email = admin_ops.check_email(args.email)
    user, created = admin_ops.set_user(s, tenant, email, _read_password(args.password_stdin))
    s.commit()
    print(f"Usuario {user.email} {'creado' if created else 'con clave nueva'}")


def create_key(s: Session, args: argparse.Namespace) -> None:
    _, key = admin_ops.create_key(s, admin_ops.tenant_by_slug(s, args.tenant), args.scope, args.name)
    s.commit()
    print(key)  # no se vuelve a mostrar


def create_admin(s: Session, args: argparse.Namespace) -> None:
    """Único camino para crear o resetear un administrador: la UI no lo permite."""
    email = admin_ops.check_email(args.email)
    user, created = admin_ops.ensure_admin(s, email, _read_password(args.password_stdin))
    s.commit()
    print(f"Administrador {user.email} {'creado' if created else 'con clave nueva'}")


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

    p = commands.add_parser("create-admin")
    p.add_argument("--email", required=True)
    p.add_argument("--password-stdin", action="store_true")
    p.set_defaults(run=create_admin)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with get_sessionmaker()() as s:
        try:
            args.run(s, args)
        except OpsError as e:
            print(e, file=sys.stderr)
            return 1
        except (IntegrityError, DataError):
            print("Dato inválido o en conflicto con uno existente", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
