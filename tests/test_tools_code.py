"""Herramientas de codigo (docs/features/HERRAMIENTAS.md): formato, y contra el sandbox real (tools-runner) si
TOOLS_RUNNER_TEST_URL apunta a uno (make tools-runner-test lo levanta aislado); si no, esos se saltean."""
import os

import pytest
from pydantic import ValidationError

from app.config import settings
from app.tools import runtime
from app.tools import schema as S
from app.tools.runtime import ToolContext, ToolSpec

RUNNER = os.getenv("TOOLS_RUNNER_TEST_URL", "")
needs_runner = pytest.mark.skipif(not RUNNER, reason="sin TOOLS_RUNNER_TEST_URL (make tools-runner-test)")
E = "export default async function ({ args, secrets, call, vars }) { %s }"


def code_tool(body: str, **extra) -> dict:
    return {"description": "Prueba.", "code": E % body,
            "parameters": {"type": "object", "properties": {"dni": {"type": "string", "description": "DNI"}}},
            **extra}


def spec(definition: dict) -> ToolSpec:
    return ToolSpec(slug="deuda", type="code", revision=1, tool=S.parse("code", definition))


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.setattr(settings, "tools_runner_url", RUNNER)
    monkeypatch.setattr(settings, "tools_runner_token", os.getenv("TOOLS_RUNNER_TEST_TOKEN", "tok"))


def test_code_format():
    tool = S.parse("code", code_tool("return 1;", secrets=["CRM_TOKEN"], allowed_hosts=["API.Ejemplo.com"]))
    assert tool.allowed_hosts == ["api.ejemplo.com"] and S.required_secrets(tool) == {"CRM_TOKEN"}
    assert S.llm_parameters(tool)["properties"] == {"dni": {"type": "string", "description": "DNI"}}
    for bad, message in [({"code": "function f() { return 1; } // sin export"}, "export default"),
                         ({"allowed_hosts": ["https://api.com/x"]}, "dominio"),
                         ({"secrets": ["minuscula"]}, "mayúsculas"),
                         ({"parameters": {"type": "string"}}, "object")]:
        with pytest.raises(ValidationError, match=message):
            S.parse("code", {**code_tool("return 1;"), **bad})


@needs_runner
async def test_returns_json_with_secrets_and_logs(runner):
    s = spec(code_tool('console.log("buscando", args.dni); return { dni: args.dni, token: secrets.CRM_TOKEN, '
                       'conversacion: call.id };', secrets=["CRM_TOKEN"]))
    ctx = ToolContext(conversation_id="c-9", secrets={"CRM_TOKEN": "secreto-largo-1234"})
    result = await runtime.run(s, {"dni": "30111222"}, ctx)
    assert result.ok, result
    assert result.data == {"dni": "30111222", "token": "[secreto:CRM_TOKEN]", "conversacion": "c-9"}
    assert "secreto-largo-1234" not in result.llm and result.logs == ["buscando 30111222"]


@needs_runner
async def test_only_declared_secrets_reach_the_code(runner):
    s = spec(code_tool("return Object.keys(secrets);", secrets=["A_TOKEN"]))
    result = await runtime.run(s, {}, ToolContext(secrets={"A_TOKEN": "aaaa1111", "OTRO": "bbbb2222"}))
    assert result.data == ["A_TOKEN"]


@needs_runner
@pytest.mark.parametrize("body, error", [
    ('throw new Error("se rompió");', "se rompió"),
    ("while (true) {}", "tiempo"),
    ('return await Deno.readTextFile("/etc/passwd");', "read access"),
    ('return Deno.env.get("TOOLS_RUNNER_TOKEN");', "env access"),
    ('return (await fetch("https://example.com/")).status;', "net access"),
    ('return { ok: false, error: "no encontrado" };', "no encontrado"),
])
async def test_failures(runner, body, error):
    result = await runtime.run(spec(code_tool(body, timeout_ms=1000)), {}, ToolContext())
    assert not result.ok and error in result.error


@needs_runner
async def test_private_address_is_blocked_by_the_egress_proxy(runner):
    s = spec(code_tool('return (await fetch("http://localtest.me/")).status;', allowed_hosts=["localtest.me"]))
    result = await runtime.run(s, {}, ToolContext())
    assert result.ok and result.data == 407           # Smokescreen: destino privado denegado
