import ast
import asyncio
import socket
import threading
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from conftest import alembic_config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import sessionmaker

from registros import db as db_module
from registros import main
from registros.config import settings
from registros.db import Base, get_engine
from registros.main import app

PACKAGE = Path(main.__file__).parent


def test_health(client):
    r = client.get("/health")
    assert (r.status_code, r.json()) == (200, {"status": "ok"})


def test_health_sin_secreto_de_sesion_avisa(client, monkeypatch):
    monkeypatch.setattr(settings, "session_secret", "")
    assert client.get("/health").status_code == 503


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Forwarder:
    """La base que aparece después: un puerto que recién al arrancar reenvía al Postgres de prueba."""

    def __init__(self, port: int, target: tuple[str, int]):
        self.target = target
        self.server = socket.create_server(("127.0.0.1", port))
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while True:
            try:
                downstream, _ = self.server.accept()
            except OSError:
                return
            upstream = socket.create_connection(self.target)
            for a, b in ((downstream, upstream), (upstream, downstream)):
                threading.Thread(target=self._pipe, args=(a, b), daemon=True).start()

    @staticmethod
    def _pipe(a, b):
        try:
            while data := a.recv(65536):
                b.sendall(data)
        except OSError:
            pass
        finally:
            for sock in (a, b):
                try:
                    sock.close()
                except OSError:
                    pass

    def close(self):
        self.server.close()


def test_arranca_sin_base_da_503_y_al_volver_200_sin_reiniciar(monkeypatch):
    real = make_url(settings.db_dsn)
    port = _free_port()
    engine = db_module.make_engine(real.set(host="127.0.0.1", port=port).render_as_string(hide_password=False))
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: sessions)

    with TestClient(app) as browser:  # el lifespan no se cae ni se cuelga sin base
        r = browser.get("/health")
        assert (r.status_code, r.json()) == (503, {"status": "unavailable"})
        forwarder = Forwarder(port, (real.host, real.port or 5432))
        try:
            assert browser.get("/health").json() == {"status": "ok"}
        finally:
            engine.dispose()
            forwarder.close()


def test_el_reintento_de_conexion_sigue_hasta_que_hay_base(monkeypatch):
    results = iter([False, False, True])
    monkeypatch.setattr(main, "db_ready", lambda: next(results))
    monkeypatch.setattr(main, "DB_RETRY_MIN_SECONDS", 0)
    asyncio.run(main._wait_for_db())
    assert next(results, "agotado") == "agotado"


def test_base_caida_en_una_ruta_da_503_sin_detalle():
    port = _free_port()
    dead = create_engine(f"postgresql+psycopg://secreto:secreto@127.0.0.1:{port}/x", hide_parameters=True)
    app.dependency_overrides[db_module.get_session] = lambda: sessionmaker(bind=dead)()
    try:
        browser = TestClient(app, raise_server_exceptions=False)
        r = browser.post("/auth/login", json={"tenant": "x", "email": "a@b.c", "password": "x"})
    finally:
        app.dependency_overrides.clear()
    assert (r.status_code, r.json()) == (503, {"detail": "Base no disponible"})


def test_errores_de_validacion_sin_lo_recibido(client):
    r = client.post("/auth/login", json={"tenant": "x", "email": "dato-personal@example.com"})
    assert r.status_code == 422
    assert "dato-personal" not in r.text


def test_cabeceras_de_seguridad(client):
    headers = client.get("/health").headers
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_sin_documentacion_publica(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_los_routers_de_api_y_panel_ya_estan_incluidos():
    from registros import api, panel

    assert api.router.prefix == "/v1"
    assert panel.router.prefix == ""
    source = (PACKAGE / "main.py").read_text()
    assert "include_router(api.router)" in source and "include_router(panel.router)" in source


def test_static_del_panel_montado():
    assert any(getattr(route, "path", None) == "/static" for route in app.routes)


def test_el_paquete_no_importa_la_plataforma_ni_el_crm():
    for path in PACKAGE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            for name in names:
                assert name.split(".")[0] not in ("app", "crm"), f"{path}: importa {name}"


def test_el_rol_de_prueba_no_es_superusuario():
    with get_engine().connect() as conn:
        assert conn.scalar(text("select rolsuper from pg_roles where rolname = current_user")) is False


def test_la_migracion_coincide_con_los_modelos():
    with get_engine().connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert diff == []


def test_la_migracion_va_y_vuelve():
    config = alembic_config()
    command.downgrade(config, "base")
    with get_engine().connect() as conn:
        assert conn.scalar(text("select to_regclass('public.persons')")) is None
    command.upgrade(config, "head")
    with get_engine().connect() as conn:
        assert conn.scalar(text("select to_regclass('public.persons')")) is not None
