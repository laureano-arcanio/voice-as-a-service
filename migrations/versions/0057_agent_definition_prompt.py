"""Definicion del agente con prompt libre: las definiciones guardadas pasan a la forma nueva
(docs/ARQUITECTURA.md, "Definicion de un agente").

- `definition_legacy` (jsonb, NULL) en `agents`, `agent_versions`, `tools` y `tool_versions`: la definicion de antes,
  para la vuelta atras. La escribe y la lee esta migracion; la app no la usa.
- Las definiciones con la forma vieja (`objective`, `conversation` o `completion`) se copian a `definition_legacy` y
  se reescriben con `app.conversation.legacy.upgrade` (`prompt`, `first_message` y `analysis`); `id` y `version`
  quedan como estaban.
- Las herramientas con `{{vars.x}}` o `{{contact.x}}` en algun texto se copian y pasan a `{{x}}`.
- Las filas con la forma nueva no se tocan. Por lotes y en la misma transaccion de la migracion.

`legacy.upgrade` esta congelado porque lo importa esta migracion; no se importa `Workflow` (el modelo cambia con el
tiempo y romperia un `upgrade` desde cero). La validacion de lo que queda guardado esta en la verificacion
(tests/test_migration_0057.py y el script de scratch contra la copia del backup).

Downgrade: restaura cada definicion desde `definition_legacy` y borra la columna. Aborta, sin tocar nada, si hay
definiciones con la forma nueva (o herramientas con `{{x}}`) sin copia: se guardaron despues de esta migracion y la
0056 no sabe leerlas. Ahi se vuelve con el backup de la base.

Revision ID: 0057
Revises: 0056
Create Date: 2026-11-13
"""
import re

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.conversation import legacy

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
BATCH = 200
# Los templates viejos de una herramienta: {{vars.x}} y {{contact.x}} pasan a {{x}}.
OLD_TEMPLATE_RE = re.compile(r"\{\{\s*(?:vars|contact)\.([A-Za-z0-9_]+)\s*\}\}")
# {{x}} sin espacio, lo que la 0056 solo aceptaba para now, today y channel.
BARE_TEMPLATE_RE = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")
BARE_OLD = {"now", "today", "channel"}
DEFINITION_TABLES = ("agents", "agent_versions")
TOOL_TABLES = ("tools", "tool_versions")

AGENTS = sa.table("agents", sa.column("id", sa.String), sa.column("definition", JSONDoc),
                  sa.column("definition_legacy", JSONDoc))
VERSIONS = sa.table("agent_versions", sa.column("agent_id", sa.String), sa.column("version", sa.Integer),
                    sa.column("definition", JSONDoc), sa.column("definition_legacy", JSONDoc))
TOOLS = sa.table("tools", sa.column("id", sa.String), sa.column("definition", JSONDoc),
                 sa.column("definition_legacy", JSONDoc))
TOOL_VERSIONS = sa.table("tool_versions", sa.column("id", sa.String), sa.column("definition", JSONDoc),
                         sa.column("definition_legacy", JSONDoc))


def _by_id(bind, table):
    """Las filas de a lotes, por id creciente: la paginacion no se mueve al escribir las demas columnas."""
    last = ""
    while rows := bind.execute(sa.select(table).where(table.c.id > last).order_by(table.c.id).limit(BATCH)).all():
        for row in rows:
            last = row.id
            yield row


def _versions(bind):
    """agent_versions, de a lotes, por (agent_id, version)."""
    last = ("", -1)
    while rows := bind.execute(sa.select(VERSIONS).where(sa.or_(
            VERSIONS.c.agent_id > last[0],
            sa.and_(VERSIONS.c.agent_id == last[0], VERSIONS.c.version > last[1])))
            .order_by(VERSIONS.c.agent_id, VERSIONS.c.version).limit(BATCH)).all():
        for row in rows:
            last = (row.agent_id, row.version)
            yield row


def _replace(value):
    """Los templates viejos a {{x}} en cualquier texto de la definicion de la herramienta. (valor, cambio)."""
    if isinstance(value, str):
        new = OLD_TEMPLATE_RE.sub(r"{{\1}}", value)
        return new, new != value
    if isinstance(value, list):
        out, changed = [], False
        for item in value:
            item, one = _replace(item)
            out.append(item)
            changed = changed or one
        return out, changed
    if isinstance(value, dict):
        out, changed = {}, False
        for key, item in value.items():
            item, one = _replace(item)
            out[key] = item
            changed = changed or one
        return out, changed
    return value, False


def _has_bare(value) -> bool:
    """Si la definicion de la herramienta tiene un {{x}} que la 0056 no sabia guardar."""
    if isinstance(value, str):
        return any(m.group(1) not in BARE_OLD for m in BARE_TEMPLATE_RE.finditer(value))
    if isinstance(value, list):
        return any(_has_bare(v) for v in value)
    if isinstance(value, dict):
        return any(_has_bare(v) for v in value.values())
    return False


def upgrade() -> None:
    for name in (*DEFINITION_TABLES, *TOOL_TABLES):
        with op.batch_alter_table(name) as batch:
            batch.add_column(sa.Column("definition_legacy", JSONDoc, nullable=True))

    bind = op.get_bind()
    for row in _by_id(bind, AGENTS):
        if legacy.is_legacy(row.definition):
            bind.execute(AGENTS.update().where(AGENTS.c.id == row.id)
                         .values(definition_legacy=row.definition, definition=legacy.upgrade(row.definition)))
    for row in _versions(bind):
        if legacy.is_legacy(row.definition):
            bind.execute(VERSIONS.update()
                         .where(sa.and_(VERSIONS.c.agent_id == row.agent_id, VERSIONS.c.version == row.version))
                         .values(definition_legacy=row.definition, definition=legacy.upgrade(row.definition)))
    for table in (TOOLS, TOOL_VERSIONS):
        for row in _by_id(bind, table):
            definition, changed = _replace(row.definition)
            if changed:
                bind.execute(table.update().where(table.c.id == row.id)
                             .values(definition_legacy=row.definition, definition=definition))


def _count_new(bind, name: str) -> int:
    """Definiciones con la forma nueva (prompt) y sin copia: las guardo alguien despues de esta migracion."""
    where = "json_extract(definition, '$.prompt') IS NOT NULL" if bind.dialect.name == "sqlite" \
        else "definition ? 'prompt'"
    return bind.scalar(sa.text(f"SELECT count(*) FROM {name} WHERE definition_legacy IS NULL AND {where}")) or 0


def _count_bare(bind, table) -> int:
    """Herramientas con {{x}} y sin copia: las guardo alguien despues de esta migracion."""
    rows = bind.execute(sa.select(table.c.definition).where(table.c.definition_legacy.is_(None))).scalars()
    return sum(1 for definition in rows if _has_bare(definition))


def _unrestorable(bind) -> list[str]:
    found = []
    for name in DEFINITION_TABLES:
        if count := _count_new(bind, name):
            found.append(f"{count} en {name} con la forma nueva y sin definition_legacy")
    for name, table in zip(TOOL_TABLES, (TOOLS, TOOL_VERSIONS)):
        if count := _count_bare(bind, table):
            found.append(f"{count} en {name} con {{{{x}}}} y sin definition_legacy")
    return found


def downgrade() -> None:
    bind = op.get_bind()
    # Primero el chequeo: si no se puede volver, la migracion falla y la transaccion no toca nada.
    if found := _unrestorable(bind):
        raise RuntimeError(
            "La 0057 no puede deshacerse: " + "; ".join(found) + ". Se guardaron despues de la migracion y la 0056 "
            "no sabe leerlas; se vuelve con el backup de la base (docs/INFRA.md) en vez de make migrate-down.")

    for row in _by_id(bind, AGENTS):
        if row.definition_legacy is not None:
            bind.execute(AGENTS.update().where(AGENTS.c.id == row.id).values(definition=row.definition_legacy))
    for row in _versions(bind):
        if row.definition_legacy is not None:
            bind.execute(VERSIONS.update()
                         .where(sa.and_(VERSIONS.c.agent_id == row.agent_id, VERSIONS.c.version == row.version))
                         .values(definition=row.definition_legacy))
    for table in (TOOLS, TOOL_VERSIONS):
        for row in _by_id(bind, table):
            if row.definition_legacy is not None:
                bind.execute(table.update().where(table.c.id == row.id).values(definition=row.definition_legacy))

    for name in (*DEFINITION_TABLES, *TOOL_TABLES):
        with op.batch_alter_table(name) as batch:
            batch.drop_column("definition_legacy")
