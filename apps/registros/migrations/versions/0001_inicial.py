"""Esquema inicial de Registros.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("charge_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("form_html", sa.Text()),
        sa.Column("form_schema", JSONB()),
        sa.Column("manifest", JSONB()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_table(
        "persons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("titular_name", sa.String(200), nullable=False),
        sa.Column("al_dia", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("al_dia_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("al_dia_at", sa.DateTime()),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "id", name="uq_persons_tenant_id"),
    )
    op.create_index("ix_persons_tenant_name", "persons", ["tenant_id", "name"])
    op.create_table(
        "person_phones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("person_id", sa.String(36), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("relation", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "person_id"], ["persons.tenant_id", "persons.id"],
                                name="fk_person_phones_person", ondelete="CASCADE"),
        sa.UniqueConstraint("person_id", "phone", name="uq_person_phones_person_phone"),
    )
    op.create_index("ix_person_phones_tenant_phone", "person_phones", ["tenant_id", "phone"])
    op.create_table(
        "conversation_choices",
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("conversation_id", sa.String(64), primary_key=True),
        sa.Column("from_phone", sa.String(20), nullable=False),
        sa.Column("refs", JSONB(), nullable=False),
        sa.Column("person_id", sa.String(36)),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "person_id"], ["persons.tenant_id", "persons.id"],
                                name="fk_conversation_choices_person"),
    )
    op.create_table(
        "charges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("person_id", sa.String(36), nullable=False),
        sa.Column("titular_name", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="simulated"),
        sa.Column("from_phone", sa.String(20), nullable=False),
        sa.Column("operator_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "person_id"], ["persons.tenant_id", "persons.id"],
                                name="fk_charges_person"),
        sa.UniqueConstraint("tenant_id", "conversation_id", name="uq_charges_tenant_conversation"),
    )
    op.create_index("ix_charges_tenant_person", "charges", ["tenant_id", "person_id"])
    op.create_table(
        "record_links",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("person_ids", JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "conversation_id", name="uq_record_links_tenant_conversation"),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id")),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("person_id", sa.String(36), sa.ForeignKey("persons.id", ondelete="SET NULL")),
        sa.Column("detail", JSONB()),
        sa.Column("at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_log_action_at", "audit_log", ["action", "at"])
    op.create_index("ix_audit_log_tenant_at", "audit_log", ["tenant_id", "at"])


def downgrade() -> None:
    for table in ("audit_log", "record_links", "charges", "conversation_choices", "person_phones",
                  "persons", "sessions", "users", "api_keys", "tenants"):
        op.drop_table(table)
