"""Un solo motor (AGENTS.md, 26-oct-2026): se quitan el motor assistant y las apps por cliente
(tablas apps, app_links, app_job_runs y wa_operators) y se archivan los agentes con motor assistant (no
tienen con que correr). Historial de las herramientas del cliente: tabla tool_versions con cada revision.

El downgrade vuelve a crear las tablas de apps y operadores vacias (los datos no vuelven) y no desarchiva.

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    agents = sa.table("agents", sa.column("id", sa.String), sa.column("definition", JSONDoc),
                      sa.column("archived_at", sa.DateTime))
    for agent_id, definition in bind.execute(sa.select(agents.c.id, agents.c.definition)).all():
        if (definition or {}).get("engine") == "assistant":
            bind.execute(agents.update().where(agents.c.id == agent_id)
                         .values(archived_at=sa.func.coalesce(agents.c.archived_at, sa.func.now())))
    op.drop_index("ix_wa_operators_client_id", table_name="wa_operators")
    op.drop_table("wa_operators")
    op.drop_table("app_job_runs")
    op.drop_index("ix_app_links_app_id", table_name="app_links")
    op.drop_table("app_links")
    op.drop_index("ix_apps_client_id", table_name="apps")
    op.drop_table("apps")

    op.create_table(
        "tool_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tool_id", sa.String(36), sa.ForeignKey("tools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        sa.Column("definition", JSONDoc, nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tool_id", "revision", name="uq_tool_versions_tool_revision"),
    )
    op.create_index("ix_tool_versions_tool_id", "tool_versions", ["tool_id"])
    # La revision vigente de cada herramienta que ya existe.
    tools = sa.table("tools", sa.column("id", sa.String), sa.column("revision", sa.Integer),
                     sa.column("type", sa.String), sa.column("definition", JSONDoc), sa.column("created_by", sa.String),
                     sa.column("updated_at", sa.DateTime))
    versions = sa.table("tool_versions", sa.column("id", sa.String), sa.column("tool_id", sa.String),
                        sa.column("revision", sa.Integer), sa.column("type", sa.String),
                        sa.column("definition", JSONDoc), sa.column("created_by", sa.String),
                        sa.column("created_at", sa.DateTime))
    import uuid
    for row in bind.execute(sa.select(tools)).all():
        bind.execute(versions.insert().values(id=str(uuid.uuid4()), tool_id=row.id, revision=row.revision,
                                              type=row.type, definition=row.definition, created_by=row.created_by,
                                              created_at=row.updated_at))


def downgrade() -> None:
    op.drop_index("ix_tool_versions_tool_id", table_name="tool_versions")
    op.drop_table("tool_versions")
    op.create_table(
        "apps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("base_url", sa.String(255), nullable=False),
        sa.Column("token_enc", sa.Text(), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("manifest", JSONDoc, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("last_error", sa.String(255), nullable=True),
        sa.Column("last_health_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('ok', 'down', 'invalid')", name="ck_apps_status"),
    )
    op.create_index("ix_apps_client_id", "apps", ["client_id"])
    op.create_table(
        "app_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("view", sa.String(64), nullable=False),
        sa.Column("params", JSONDoc, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("opens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_opened_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_app_links_app_id", "app_links", ["app_id"])
    op.create_table(
        "app_job_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job", sa.String(64), nullable=False),
        sa.Column("run_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("app_id", "job", "run_on", name="uq_app_job_runs_day"),
    )
    op.create_table(
        "wa_operators",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wa_id", sa.String(32), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("account_id", "wa_id", name="uq_wa_operators_account_waid"),
    )
    op.create_index("ix_wa_operators_client_id", "wa_operators", ["client_id"])
