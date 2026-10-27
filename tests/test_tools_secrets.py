"""Secretos del cliente y credenciales (docs/TOOLS_PLAN.md, 16): el agente usa los del cliente y los suyos los
pisan, "pasar al cliente", credenciales reutilizables entre herramientas y la prueba sin elegir agente."""
import pytest
from cryptography.fernet import Fernet

from app.config import settings
from scripts.tools import mock_api

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_client,
)
from .test_tools_api import classic_agent, put_tools, turnos_tool
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)

ARGS = {"sucursal": "centro", "fecha": "2026-11-05"}


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def with_credential(base: str = "https://api.acme.com") -> dict:
    tool = turnos_tool(base)
    tool["definition"]["http"]["auth"] = {"type": "credential", "credential": "api_turnos"}
    return tool


def credential(value: str | None = mock_api.TOKEN, secret: str = "MOCK_TOKEN") -> dict:
    return {"slug": "api_turnos", "name": "API de turnos", "auth": {"type": "bearer", "secret": secret},
            **({"value": value} if value is not None else {})}


def test_agent_uses_client_secret_and_its_own_overrides(api, admin):
    c = make_client(admin, max_tools=None)
    admin.post(f"{V1}/clients/{c['id']}/tools", json=turnos_tool())
    agent = classic_agent(admin, c).json()
    r = admin.post(f"{V1}/clients/{c['id']}/secrets", json={"name": "MOCK_TOKEN", "value": "x" * 20,
                                                            "description": "Token de turnos"})
    assert r.status_code == 201 and "x" * 20 not in r.text
    # Con el del cliente alcanza para guardar el agente.
    assert put_tools(admin, agent, [{"tool": "consultar_turnos"}]).status_code == 200
    [row] = admin.get(f"{V1}/agents/{agent['id']}/secrets").json()
    assert (row["source"], row["missing"], row["used_by"]) == ("client", False, ["consultar_turnos"])
    listed = admin.get(f"{V1}/clients/{c['id']}/secrets").json()
    assert listed[0]["used_by"] == ["consultar_turnos"] and listed[0]["agents"] == []
    # El propio pisa al del cliente; borrarlo vuelve al del cliente (no es secret_in_use).
    admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": "MOCK_TOKEN", "value": "y" * 20})
    [row] = admin.get(f"{V1}/agents/{agent['id']}/secrets").json()
    assert (row["source"], row["overrides"]) == ("agent", True)
    assert admin.get(f"{V1}/clients/{c['id']}/secrets").json()[0]["agents"] == [{"id": agent["id"],
                                                                                 "name": agent["name"]}]
    assert admin.delete(f"{V1}/agents/{agent['id']}/secrets/MOCK_TOKEN").status_code == 204
    # El del cliente no se borra mientras un agente lo use sin propio.
    r = admin.delete(f"{V1}/clients/{c['id']}/secrets/MOCK_TOKEN")
    assert r.status_code == 409 and r.json()["code"] == "secret_in_use"


def test_runtime_values_merge_client_and_agent(api, admin):
    from app.services import tools as svc
    c = make_client(admin, max_tools=None)
    agent = classic_agent(admin, c).json()
    admin.post(f"{V1}/clients/{c['id']}/secrets", json={"name": "A_TOKEN", "value": "cliente-a"})
    admin.post(f"{V1}/clients/{c['id']}/secrets", json={"name": "B_TOKEN", "value": "cliente-b"})
    admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": "B_TOKEN", "value": "agente-b"})
    with api.sessions() as s:
        assert svc.secret_values(s, agent["id"]) == {"A_TOKEN": "cliente-a", "B_TOKEN": "agente-b"}


def test_promote_moves_equal_values_and_refuses_a_different_one(api, admin):
    c = make_client(admin, max_tools=None)
    a1 = classic_agent(admin, c).json()
    a2 = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "Otro", "slug": "otro",
                                          "definition": a1["definition"]}).json()
    for a in (a1, a2):
        admin.post(f"{V1}/agents/{a['id']}/secrets", json={"name": "CRM_TOKEN", "value": "mismo-valor-1234"})
    r = admin.post(f"{V1}/agents/{a1['id']}/secrets/CRM_TOKEN/promote")
    assert r.status_code == 200 and r.json()["moved"] == 2
    assert admin.get(f"{V1}/agents/{a2['id']}/secrets").json() == []
    assert [x["name"] for x in admin.get(f"{V1}/clients/{c['id']}/secrets").json()] == ["CRM_TOKEN"]
    admin.post(f"{V1}/agents/{a2['id']}/secrets", json={"name": "CRM_TOKEN", "value": "otro-valor-12345"})
    r = admin.post(f"{V1}/agents/{a2['id']}/secrets/CRM_TOKEN/promote")
    assert r.status_code == 409 and r.json()["code"] == "secret_name_taken"


def test_credential_crud_and_tool_resolution(api, admin):
    c = make_client(admin, max_tools=None)
    # Sin la credencial, la herramienta no se guarda.
    r = admin.post(f"{V1}/clients/{c['id']}/tools", json=with_credential())
    assert r.status_code == 422 and r.json()["errors"][0]["path"] == "definition.http.auth.credential"
    # Sin valor ni secreto cargado, la credencial tampoco.
    r = admin.post(f"{V1}/clients/{c['id']}/credentials", json=credential(value=None))
    assert r.status_code == 422 and r.json()["errors"][0]["path"] == "value"
    r = admin.post(f"{V1}/clients/{c['id']}/credentials", json=credential())
    assert r.status_code == 201, r.text
    out = r.json()
    assert (out["type"], out["secret"], out["secret_set"]) == ("bearer", "MOCK_TOKEN", True)
    assert mock_api.TOKEN not in r.text
    assert admin.get(f"{V1}/clients/{c['id']}/secrets").json()[0]["credentials"] == ["api_turnos"]
    bad = {**credential(), "slug": "otra", "auth": {"type": "credential", "credential": "api_turnos"}}
    assert admin.post(f"{V1}/clients/{c['id']}/credentials", json=bad).status_code == 422
    tool = admin.post(f"{V1}/clients/{c['id']}/tools", json=with_credential())
    assert tool.status_code == 201 and tool.json()["secrets"] == ["MOCK_TOKEN"]
    assert admin.get(f"{V1}/clients/{c['id']}/credentials/api_turnos").json()["used_by"] == ["consultar_turnos"]
    # Un header de la herramienta no puede chocar con el de la credencial.
    clash = with_credential()
    clash["definition"]["http"]["headers"] = {"Authorization": "x"}
    r = admin.put(f"{V1}/clients/{c['id']}/tools/consultar_turnos", json={"type": "http",
                                                                          "definition": clash["definition"]})
    assert r.status_code == 422
    # En uso: no se borra; el secreto que la guarda tampoco.
    r = admin.delete(f"{V1}/clients/{c['id']}/credentials/api_turnos")
    assert r.status_code == 409 and r.json()["code"] == "credential_in_use"
    assert admin.delete(f"{V1}/clients/{c['id']}/secrets/MOCK_TOKEN").json()["code"] == "secret_in_use"
    # Cambiarla a un secreto que un agente no tiene rompe al agente: no se guarda.
    agent = classic_agent(admin, c).json()
    assert put_tools(admin, agent, [{"tool": "consultar_turnos"}]).status_code == 200
    r = admin.put(f"{V1}/clients/{c['id']}/credentials/api_turnos",
                  json={"name": "API de turnos", "auth": {"type": "api_key", "secret": "OTRA_KEY", "name": "X-Key"}})
    assert r.status_code == 422 and r.json()["code"] == "invalid_credential"   # sin valor para OTRA_KEY
    other = make_client(admin, "otro", max_tools=None)
    user = client_user(api, admin, other, "luis@otro.com")
    assert user.get(f"{V1}/clients/{c['id']}/credentials").status_code == 404
    assert user.get(f"{V1}/clients/{c['id']}/secrets").status_code == 404


def test_test_uses_client_secrets_and_the_credential(api, admin, mock_api_url):
    c = make_client(admin, max_tools=None)
    admin.post(f"{V1}/clients/{c['id']}/credentials", json=credential())
    tool = admin.post(f"{V1}/clients/{c['id']}/tools", json=with_credential(mock_api_url)).json()
    r = admin.post(f"{V1}/clients/{c['id']}/tools/test",
                   json={"type": "http", "definition": tool["definition"], "args": ARGS})
    out = r.json()
    assert out["ok"] and out["data"]["turnos"] == ["10:00", "11:30", "16:00"], out
    assert mock_api.TOKEN not in r.text and "[secreto:MOCK_TOKEN]" in out["request"]["headers"]["Authorization"]
    # Con el propio (malo) de un agente, la prueba con ese agente falla.
    agent = classic_agent(admin, c).json()
    admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": "MOCK_TOKEN", "value": "token-que-no-sirve"})
    out = admin.post(f"{V1}/clients/{c['id']}/tools/consultar_turnos/test",
                     json={"args": ARGS, "agent_id": agent["id"]}).json()
    assert not out["ok"] and out["status"] == 401


def test_runtime_without_the_credential_fails_clearly():
    import asyncio

    from app.tools import schema as S
    from app.tools.runtime import ToolContext, ToolSpec, run
    tool = S.parse("http", with_credential()["definition"])
    result = asyncio.run(run(ToolSpec(slug="t", type="http", revision=1, tool=tool), ARGS, ToolContext()))
    assert not result.ok and "api_turnos" in (result.error or "")
