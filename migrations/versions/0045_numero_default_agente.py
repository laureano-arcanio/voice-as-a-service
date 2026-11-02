"""Un numero arranca atendido por su agente, no por el equipo (docs/features/EQUIPO_TELEFONIA.md). Los que
estaban en team sin personas pasan a agent: es el default viejo, nadie los eligio. Las entrantes siguen igual
(un team sin personas ya iba al agente del numero); cambia que el panel muestra el selector de agente.

Revision ID: 0045
Revises: 0044
Create Date: 2026-11-02
"""
import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as batch:
        batch.alter_column("answer_mode", existing_type=sa.String(8), server_default="agent")
    op.execute("UPDATE phone_numbers SET answer_mode = 'agent' WHERE answer_mode = 'team' AND NOT EXISTS "
               "(SELECT 1 FROM phone_number_members m WHERE m.phone_number_id = phone_numbers.id)")


def downgrade() -> None:
    # Solo el default: los numeros que paso a agent quedan asi (atienden igual).
    with op.batch_alter_table("phone_numbers") as batch:
        batch.alter_column("answer_mode", existing_type=sa.String(8), server_default="team")
