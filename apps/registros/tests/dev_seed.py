"""Datos de ejemplo de make registros-dev: dos tenants, para mirar a mano el aislamiento. Solo para el
Postgres de prueba (compose.test.yaml), que se borra con registros-dev-down."""
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from registros.auth import api_key_hash, hash_password  # noqa: E402
from registros.db import get_sessionmaker  # noqa: E402
from registros.manifest import parse_manifest, sync_person  # noqa: E402
from registros.models import ApiKey, Person, Tenant, User  # noqa: E402

FORM = ROOT / "tests" / "fixtures" / "form_ejemplo"
PASSWORD = "dev-registros"
PERSONS = {
    "ejemplo": [
        {"datos": {"nombre": "Ana Ejemplo", "documento": "20000001", "codigo": "A1", "celular": "+5493510000001"},
         "cobertura": {"titular": "Ana Ejemplo"},
         "contactos": [{"nombre": "Beto Ejemplo", "telefono": "+5493510000002"}]},
    ],
    "otro": [
        {"datos": {"nombre": "Carla Otra", "documento": "20000002", "codigo": "B1", "celular": "+5493510000003"},
         "cobertura": {"titular": "Carla Otra"}},
    ],
}


def seed() -> None:
    with get_sessionmaker()() as s:
        for slug, persons in PERSONS.items():
            if s.scalar(select(Tenant).where(Tenant.slug == slug)):
                continue
            raw = json.loads((FORM / "manifest.json").read_text(encoding="utf-8"))
            tenant = Tenant(slug=slug, name=slug.capitalize(), charge_amount=Decimal("1000"),
                            form_html=(FORM / "form.html").read_text(encoding="utf-8"),
                            form_schema=json.loads((FORM / "schema.json").read_text(encoding="utf-8")), manifest=raw)
            s.add(tenant)
            s.flush()
            s.add(User(tenant_id=tenant.id, email=f"dev@{slug}.test", password_hash=hash_password(PASSWORD)))
            for scope in ("read", "charge"):
                s.add(ApiKey(tenant_id=tenant.id, key_hash=api_key_hash(f"reg_dev_{slug}_{scope}"), scope=scope,
                             name=f"dev {scope}"))
            manifest = parse_manifest(raw)
            for data in persons:
                person = Person(tenant_id=tenant.id, name="", titular_name="", data=data)
                s.add(person)
                sync_person(s, person, manifest)
        s.commit()


if __name__ == "__main__":
    seed()
