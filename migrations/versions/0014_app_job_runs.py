"""Avisos programados de las apps (contrato v1.1, docs/APPS_PLAN.md): app_job_runs, una corrida por
dia y job.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_table("app_job_runs")
