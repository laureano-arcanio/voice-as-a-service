"""Una persona por usuario de cliente y rol del cliente: team_members.user_id único y users.client_role.

- A cada usuario `client` sin persona le vincula la única persona del mismo nombre de su cliente (sin usuario)
  o le crea una con el nombre del usuario (o la parte local del email); después el índice único parcial.
- Si un usuario ya está vinculado a dos personas falla con el detalle (no elige por su cuenta).
- `client_role`: admin a todos los usuarios `client` existentes (decisión del 24-nov-2026).

Revision ID: 0064
Revises: 0063
Create Date: 2026-11-24

"""
import datetime
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

INDEX = "uq_team_members_user_id"


def _name(user_name: str | None, email: str) -> str:
    return (user_name or "").strip()[:120] or email.rsplit("@", 1)[0][:120]


def upgrade() -> None:
    with op.batch_alter_table("users") as t:
        t.add_column(sa.Column("client_role", sa.String(8), nullable=True))
    op.execute("UPDATE users SET client_role = 'admin' WHERE role = 'client'")

    conn = op.get_bind()
    duplicated = conn.execute(sa.text(
        "SELECT user_id, COUNT(*) AS n FROM team_members WHERE user_id IS NOT NULL "
        "GROUP BY user_id HAVING COUNT(*) > 1")).all()
    if duplicated:
        detail = ", ".join(f"{user_id} ({n} personas)" for user_id, n in duplicated)
        raise RuntimeError(f"Hay usuarios con más de una persona en el equipo: {detail}. "
                           "Dejá una sola por usuario y volvé a correr la migración.")

    users = conn.execute(sa.text(
        "SELECT id, client_id, email, name FROM users WHERE role = 'client' AND client_id IS NOT NULL")).all()
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    for user_id, client_id, email, name in users:
        linked = conn.execute(sa.text(
            "SELECT id FROM team_members WHERE user_id = :uid LIMIT 1"), {"uid": user_id}).scalar()
        if linked:
            continue
        candidates = conn.execute(sa.text(
            "SELECT id FROM team_members WHERE client_id = :cid AND user_id IS NULL "
            "AND lower(trim(name)) = lower(trim(:name))"), {"cid": client_id, "name": name or ""}).all()
        if len(candidates) == 1:
            conn.execute(sa.text("UPDATE team_members SET user_id = :uid, updated_at = :now WHERE id = :id"),
                         {"uid": user_id, "id": candidates[0][0], "now": now})
            continue
        conn.execute(sa.text(
            "INSERT INTO team_members (id, client_id, name, phone, user_id, active, whatsapp_notify, created_at, "
            "updated_at) VALUES (:id, :cid, :name, NULL, :uid, :active, :wa, :now, :now)"),
            {"id": str(uuid.uuid4()), "cid": client_id, "name": _name(name, email), "uid": user_id,
             "active": True, "wa": False, "now": now})

    op.create_index(INDEX, "team_members", ["user_id"], unique=True,
                    postgresql_where=sa.text("user_id IS NOT NULL"),
                    sqlite_where=sa.text("user_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_index(INDEX, table_name="team_members")
    with op.batch_alter_table("users") as t:
        t.drop_column("client_role")
