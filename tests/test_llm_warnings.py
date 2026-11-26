"""Avisos del modelo de lenguaje al validar y guardar un agente (docs/features/LLM_CONEXIONES.md).

`app/services/llm_warnings.py`: no bloquean nada y no consultan la clave del cliente. El catalogo publico de
OpenRouter se pisa con `model_status`; el autouse de `conftest.py` lo deja en "unknown" para el resto de la suite.
"""
import pytest

from app.agents.templates import reference_data
from app.models import LlmConnection
from app.services import llm_warnings as service

from .test_api import V1, admin, client_user, make_client  # noqa: F401
from .test_llm_byok import new_connection


def definition(conn, model="vendor/model", **stage):
    return {**reference_data("sales_discovery"),
            "llm": {"stages": [{"from_turn": 1, "connection": conn["id"], "model": model, **stage}],
                    "fallback_local": True}}


def validate(admin, definition_):
    r = admin.post(f"{V1}/agents/validate", json={"definition": definition_})
    assert r.status_code == 200, r.text
    return r.json()


def status(monkeypatch, result: str, seen: list | None = None):
    async def fake(model: str) -> str:
        if seen is not None:
            seen.append(model)
        return result
    monkeypatch.setattr(service, "model_status", fake)


def failed_test(api, conn, detail="clave inválida o sin permiso"):
    """Deja la ultima prueba de la conexion fallida, como la guarda POST /{id}/test."""
    with api.sessions() as s:
        row = s.get(LlmConnection, conn["id"])
        row.last_test_ok, row.last_test_detail = False, detail
        s.commit()


@pytest.mark.parametrize("result, code", [
    ("ok", None),
    ("not_found", "model_not_found"),
    ("no_endpoints", "model_no_endpoints"),
    ("invalid", "invalid_model"),
    ("unknown", None),          # catalogo caido: sin aviso
])
def test_cada_estado_del_catalogo_da_su_aviso(api, admin, monkeypatch, result, code):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    status(monkeypatch, result)
    out = validate(admin, definition(conn))
    assert out["valid"] is True
    assert [w["code"] for w in out["warnings"]] == ([code] if code else [])
    if code:
        assert out["warnings"][0]["path"] == "llm.stages.0.model"


def test_el_modelo_free_avisa_aunque_exista(api, admin, monkeypatch):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    status(monkeypatch, "ok")
    out = validate(admin, definition(conn, model="vendor/model:free"))
    assert [w["code"] for w in out["warnings"]] == ["free_model"]
    assert "tope de pedidos por minuto" in out["warnings"][0]["message"]


def test_la_ultima_prueba_fallida_avisa_con_el_detalle(api, admin, monkeypatch):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    failed_test(api, conn)
    status(monkeypatch, "ok")
    out = validate(admin, definition(conn))
    assert out["warnings"] == [{
        "path": "llm.stages.0.connection", "code": "connection_test_failed",
        "message": "La última prueba de la conexión falló: clave inválida o sin permiso"}]


def test_sin_modelo_avisa(api, admin):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    data = {"llm": {"stages": [{"from_turn": 1, "connection": conn["id"]}]}}
    with api.sessions() as s:
        out = service.llm_warnings(s, data, lambda client_id: True)
    assert out == [{"path": "llm.stages.0.model", "code": "model_missing",
                    "message": "Falta el modelo de la conexión"}]


def test_una_conexion_de_otro_cliente_no_da_aviso_ni_detalle(api, admin):
    """Aislamiento en validate: el principal solo ve las conexiones de su cliente."""
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    conn = new_connection(admin, other)
    failed_test(api, conn, detail="detalle de otro cliente")
    user = client_user(api, admin, acme)
    r = user.post(f"{V1}/agents/validate", json={"definition": definition(conn)})
    assert r.status_code == 200, r.text
    assert r.json()["warnings"] == []
    assert "detalle de otro cliente" not in r.text


def test_guardar_devuelve_los_avisos_y_guarda_igual(api, admin, monkeypatch):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    status(monkeypatch, "not_found")
    r = admin.post(f"{V1}/agents", json={"client_id": acme["id"], "name": "Ventas", "definition": definition(conn)})
    assert r.status_code == 201, r.text
    saved = r.json()
    assert [w["code"] for w in saved["warnings"]] == ["model_not_found"]
    r = admin.put(f"{V1}/agents/{saved['id']}/definition",
                  json={"definition": {**saved["definition"], "prompt": "Otro prompt."}})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == saved["version"] + 1
    assert [w["code"] for w in r.json()["warnings"]] == ["model_not_found"]


def test_consulta_el_catalogo_una_vez_por_modelo(api, admin, monkeypatch):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    seen: list[str] = []
    status(monkeypatch, "ok", seen)
    data = {**reference_data("sales_discovery"), "llm": {"stages": [
        {"from_turn": 1, "connection": conn["id"], "model": "vendor/model"},
        {"from_turn": 3, "connection": conn["id"], "model": "vendor/model"}]}}
    assert validate(admin, data)["warnings"] == []
    assert seen == ["vendor/model"]


def test_anthropic_con_free_no_tiene_aviso_de_modelo(api, admin, monkeypatch):
    """Los demas kinds no tienen catalogo publico: no se consulta ni se avisa del :free."""
    acme = make_client(admin, "acme")
    r = admin.post(f"{V1}/clients/{acme['id']}/llm-connections",
                   json={"name": "Claude", "kind": "anthropic", "api_key": "sk-ant-xyz",
                         "default_model": "claude-x"})
    assert r.status_code == 201, r.text
    conn = r.json()

    async def boom(model: str) -> str:
        raise AssertionError("no se consulta el catalogo de un anthropic")

    monkeypatch.setattr(service, "model_status", boom)
    out = validate(admin, definition(conn, model="claude-x:free"))
    assert out["warnings"] == []
