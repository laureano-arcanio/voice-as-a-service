"""Migración 0064: una persona por usuario de cliente y rol del cliente (ida y vuelta)."""
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parent.parent


def _run(engine, fn, revision):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        fn(cfg, revision)


def _base(engine):
    _run(engine, command.upgrade, "0063")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, created_at, updated_at) "
                             "VALUES ('t', 'T', '', '2026-01-01', '2026-01-01')"))
        for slug in ("a", "b"):
            conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                                 "VALUES (:id, :slug, :slug, 't', 1, '2026-01-01', '2026-01-01')"),
                         {"id": f"c-{slug}", "slug": slug})


def _user(conn, uid, email, role, client_id, name=""):
    conn.execute(sa.text(
        "INSERT INTO users (id, email, name, password_hash, role, client_id, active, session_version, "
        "created_at, updated_at) VALUES (:id, :email, :name, 'x', :role, :cid, 1, 0, '2026-01-01', '2026-01-01')"),
        {"id": uid, "email": email, "name": name, "role": role, "cid": client_id})


def _person(conn, pid, client_id, name, user_id=None):
    conn.execute(sa.text(
        "INSERT INTO team_members (id, client_id, name, phone, user_id, active, whatsapp_notify, created_at, "
        "updated_at) VALUES (:id, :cid, :name, NULL, :uid, 1, 0, '2026-01-01', '2026-01-01')"),
        {"id": pid, "cid": client_id, "name": name, "uid": user_id})


def _persons(engine):
    with engine.connect() as conn:
        return {(r.id, r.client_id, r.name, r.user_id) for r in conn.execute(sa.text(
            "SELECT id, client_id, name, user_id FROM team_members"))}


def test_0064_links_by_name_or_creates_and_sets_the_role(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _base(engine)
    with engine.begin() as conn:
        _person(conn, "p-ana", "c-a", "  Ana ")
        _person(conn, "p-b1", "c-a", "Beto")
        _person(conn, "p-b2", "c-a", "beto")          # dos candidatos: no elige, crea una nueva
        _person(conn, "p-otro", "c-b", "Ana")          # de otro cliente: no
        _person(conn, "p-carla", "c-a", "Carla", user_id="u-carla")   # ya vinculada
        _user(conn, "u-ana", "ana@a.com", "client", "c-a", "Ana")
        _user(conn, "u-beto", "beto@a.com", "client", "c-a", "Beto")
        _user(conn, "u-carla", "carla@a.com", "client", "c-a", "Carla")
        _user(conn, "u-sin", "sin-nombre@a.com", "client", "c-a", "")
        _user(conn, "u-admin", "admin@x.com", "admin", None, "Admin")

    _run(engine, command.upgrade, "0064")
    persons = _persons(engine)
    by_user = {p[3]: p for p in persons if p[3]}
    assert by_user["u-ana"][:3] == ("p-ana", "c-a", "  Ana ")      # el nombre de la persona manda
    assert by_user["u-beto"][1:3] == ("c-a", "Beto") and by_user["u-beto"][0] not in ("p-b1", "p-b2")
    assert by_user["u-carla"][0] == "p-carla"
    assert by_user["u-sin"][1:3] == ("c-a", "sin-nombre")
    assert "u-admin" not in by_user and len([p for p in persons if p[3] == "u-ana"]) == 1
    with engine.connect() as conn:
        assert dict(conn.execute(sa.text("SELECT id, client_role FROM users")).all()) == {
            "u-ana": "admin", "u-beto": "admin", "u-carla": "admin", "u-sin": "admin", "u-admin": None}
        assert conn.execute(sa.text("SELECT count(*) FROM team_members")).scalar() == 7
    index = {i["name"]: i for i in sa.inspect(engine).get_indexes("team_members")}
    assert index["uq_team_members_user_id"]["unique"]
    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        _person(conn, "p-dup", "c-a", "Ana", user_id="u-ana")

    # Ida y vuelta: quita el índice y la columna, y vuelve a correr sin duplicar personas.
    _run(engine, command.downgrade, "0063")
    assert "client_role" not in {c["name"] for c in sa.inspect(engine).get_columns("users")}
    assert "uq_team_members_user_id" not in {i["name"] for i in sa.inspect(engine).get_indexes("team_members")}
    _run(engine, command.upgrade, "0064")
    assert len(_persons(engine)) == 7


def test_0064_fails_with_the_detail_when_a_user_has_two_persons(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _base(engine)
    with engine.begin() as conn:
        _user(conn, "u-1", "uno@a.com", "client", "c-a", "Uno")
        _person(conn, "p-1", "c-a", "Uno", user_id="u-1")
        _person(conn, "p-2", "c-a", "Otra", user_id="u-1")
    with pytest.raises(RuntimeError, match="u-1 \\(2 personas\\)"):
        _run(engine, command.upgrade, "0064")
