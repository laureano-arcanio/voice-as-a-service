"""API de inferencia: limites por tier (tokens del LLM, minutos de TTS y STT, pedidos por minuto),
alcance de las API keys (scopes) y consumo diario (api_usage_daily). Ver app/services/api_usage.py.

Los tiers que ya existian quedan SIN inferencia (0) y con 60 pedidos por minuto: la API es nueva
y un NULL (ilimitado) abriria las GPUs a quien cree una key. Los tiers sin ningun limite de
llamadas (el interno, Atentina) quedan ilimitados. Las API keys que ya existian siguen siendo
de llamadas (`calls`).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TIER_COLUMNS = (
    ("api_llm_input_tokens", sa.BigInteger()),
    ("api_llm_output_tokens", sa.BigInteger()),
    ("api_tts_minutes", sa.Integer()),
    ("api_stt_minutes", sa.Integer()),
    ("api_rate_limit", sa.Integer()),
)
CHECKS = {
    "api_llm_input_tokens": "ck_tiers_api_llm_in",
    "api_llm_output_tokens": "ck_tiers_api_llm_out",
    "api_tts_minutes": "ck_tiers_api_tts",
    "api_stt_minutes": "ck_tiers_api_stt",
    "api_rate_limit": "ck_tiers_api_rate",
}


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        for name, type_ in TIER_COLUMNS:
            batch.add_column(sa.Column(name, type_, nullable=True))
        for name, check in CHECKS.items():
            batch.create_check_constraint(check, f"{name} IS NULL OR {name} >= 0")
    op.execute(
        "UPDATE tiers SET api_llm_input_tokens = 0, api_llm_output_tokens = 0, api_tts_minutes = 0, "
        "api_stt_minutes = 0, api_rate_limit = 60 "
        "WHERE NOT (max_concurrent_calls IS NULL AND inbound_minutes IS NULL AND outbound_minutes IS NULL "
        "AND max_phone_numbers IS NULL)")

    with op.batch_alter_table("api_keys") as batch:
        batch.add_column(sa.Column("scopes", sa.String(64), nullable=False, server_default="calls"))

    op.create_table(
        "api_usage_daily",
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("api_key_id", sa.String(36), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("llm_requests", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("llm_input_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("llm_output_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("stt_requests", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("stt_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tts_requests", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tts_seconds", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_api_usage_daily_client_day", "api_usage_daily", ["client_id", "day"])


def downgrade() -> None:
    op.drop_index("ix_api_usage_daily_client_day", table_name="api_usage_daily")
    op.drop_table("api_usage_daily")
    with op.batch_alter_table("api_keys") as batch:
        batch.drop_column("scopes")
    with op.batch_alter_table("tiers") as batch:
        for check in CHECKS.values():
            batch.drop_constraint(check, type_="check")
        for name, _ in TIER_COLUMNS:
            batch.drop_column(name)
