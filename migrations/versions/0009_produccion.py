"""Produccion multi-cliente (revision del 7-oct-2026, H01-H14).

- tiers.max_call_duration_seconds: tope duro de cada llamada (NULL: CALL_MAX_DURATION_SECONDS).
- tiers.retention_days y clients.retention_days: retencion de datos (el del cliente pisa
  al del tier; NULL en los dos: sin borrado).
- wa_messages: cuerpo del entrante y estado de procesamiento (WhatsApp durable, H03).
- conversations: version (control optimista, H08) y purged_at (retencion).
- call_logs.idempotency_key: POST /calls con Idempotency-Key, unica por cliente, y
  idempotency_fingerprint (sha256 del pedido: la misma clave con otro pedido da 409).
- wa_campaign_recipients.claimed_at: reclamo atomico del envio (H14).
- H01: el agente de un numero es del mismo cliente que el numero. En PostgreSQL, FK
  compuesta phone_numbers(agent_id, client_id) -> agents(id, client_id); en SQLite no
  (las FK no se aplican ahi y el SET NULL de columnas exige PG 15+).

En PostgreSQL corre con lock_timeout de 5 s: si no consigue un lock, falla y se reintenta
(mejor en una ventana sin llamadas) en vez de frenar la admision de llamadas.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-08
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _is_pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _is_pg():
        # Toma ACCESS EXCLUSIVE sobre tiers, clients, conversations, call_logs, ... con la app
        # vieja atendiendo. Sin tope, una lectura larga (ej. /stats) la deja esperando con los
        # locks ya tomados y frena quota.admit (llamadas entrantes colgadas): mejor fallar y
        # reintentar. SET LOCAL: solo esta transaccion.
        op.execute("SET LOCAL lock_timeout = '5s'")
    # H01: antes de la FK, que no haya numeros ruteados a un agente de otro cliente
    # (en modo offline, --sql, no hay base que leer).
    mixed = [] if op.get_context().as_sql else op.get_bind().execute(sa.text(
        "SELECT p.e164 FROM phone_numbers p JOIN agents a ON a.id = p.agent_id "
        "WHERE p.client_id IS NULL OR p.client_id <> a.client_id")).scalars().all()
    if mixed:
        raise RuntimeError(
            "0009: numeros ruteados a un agente de otro cliente: " + ", ".join(mixed)
            + ". Corregir (PATCH /api/v1/phone-numbers/{id} con agent_id null o un agente del cliente) y reintentar.")

    with op.batch_alter_table("tiers") as t:
        t.add_column(sa.Column("max_call_duration_seconds", sa.Integer(), nullable=True))
        t.add_column(sa.Column("retention_days", sa.Integer(), nullable=True))
        t.create_check_constraint("ck_tiers_max_call_duration",
                                  "max_call_duration_seconds IS NULL OR max_call_duration_seconds > 0")
        t.create_check_constraint("ck_tiers_retention", "retention_days IS NULL OR retention_days > 0")

    with op.batch_alter_table("clients") as t:
        t.add_column(sa.Column("retention_days", sa.Integer(), nullable=True))
        t.create_check_constraint("ck_clients_retention", "retention_days IS NULL OR retention_days > 0")

    with op.batch_alter_table("wa_messages") as t:
        t.add_column(sa.Column("body", JSONDoc, nullable=True))
        t.add_column(sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
        t.add_column(sa.Column("claimed_at", sa.DateTime(), nullable=True))
        t.add_column(sa.Column("processed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_wa_messages_direction_status_created", "wa_messages",
                    ["direction", "status", "created_at"])

    with op.batch_alter_table("conversations") as t:
        t.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="0"))
        t.add_column(sa.Column("purged_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("call_logs") as t:
        t.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
        t.add_column(sa.Column("idempotency_fingerprint", sa.String(64), nullable=True))
        t.create_unique_constraint("uq_call_logs_client_idempotency", ["client_id", "idempotency_key"])

    with op.batch_alter_table("wa_campaign_recipients") as t:
        t.add_column(sa.Column("claimed_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("agents") as t:
        t.create_unique_constraint("uq_agents_id_client", ["id", "client_id"])

    if _is_pg():
        # Borrar el agente deja el numero sin agente pero con su cliente: SET NULL solo de
        # agent_id (PG 15+). MATCH SIMPLE: un numero libre o sin agente no se chequea.
        op.execute("ALTER TABLE phone_numbers ADD CONSTRAINT fk_phone_numbers_agent_client "
                   "FOREIGN KEY (agent_id, client_id) REFERENCES agents (id, client_id) "
                   "ON DELETE SET NULL (agent_id)")


def downgrade() -> None:
    if _is_pg():
        op.execute("ALTER TABLE phone_numbers DROP CONSTRAINT fk_phone_numbers_agent_client")

    with op.batch_alter_table("agents") as t:
        t.drop_constraint("uq_agents_id_client", type_="unique")

    with op.batch_alter_table("wa_campaign_recipients") as t:
        t.drop_column("claimed_at")

    with op.batch_alter_table("call_logs") as t:
        t.drop_constraint("uq_call_logs_client_idempotency", type_="unique")
        t.drop_column("idempotency_fingerprint")
        t.drop_column("idempotency_key")

    with op.batch_alter_table("conversations") as t:
        t.drop_column("purged_at")
        t.drop_column("version")

    op.drop_index("ix_wa_messages_direction_status_created", table_name="wa_messages")
    with op.batch_alter_table("wa_messages") as t:
        t.drop_column("processed_at")
        t.drop_column("claimed_at")
        t.drop_column("attempts")
        t.drop_column("body")

    with op.batch_alter_table("clients") as t:
        t.drop_constraint("ck_clients_retention", type_="check")
        t.drop_column("retention_days")

    with op.batch_alter_table("tiers") as t:
        t.drop_constraint("ck_tiers_retention", type_="check")
        t.drop_constraint("ck_tiers_max_call_duration", type_="check")
        t.drop_column("retention_days")
        t.drop_column("max_call_duration_seconds")
