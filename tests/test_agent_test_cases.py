"""Casos de prueba de un agente: snapshot, chequeos sugeridos y API (docs/features/CASOS_DE_PRUEBA.md)."""
import json
import uuid

import pytest

from app.llm.prompt import TRUNCATED
from app.models import AgentTestCase, ConversationRow
from app.services import calls as calls_service

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401


def make_conversation(api, agent, messages, progress=None, channel="voice", cid=None):
    cid = cid or str(uuid.uuid4())
    with api.sessions() as s:
        s.add(ConversationRow(id=cid, client_id=agent["client_id"], agent_id=agent["id"], agent_version=agent["version"],
                              channel=channel, status="completed", fields={}, messages=messages,
                              progress=progress or {}))
        s.commit()
    return cid


def mensajes(tool_result=None, trace_output=None, handoff=None):
    tools = []
    if tool_result is not None:
        tools = [{"id": "call_0", "name": "estrella_salidas", "arguments": '{"destino": "Castelli"}',
                  "result": tool_result}]
    return [
        {"role": "assistant", "text": "Hola, soy Sofía."},
        {"role": "user", "text": "¿Hay salidas a Castelli?"},
        {"role": "assistant", "text": "Hay dos salidas a las 12:00 y a las 14:30, a $29.300.",
         "tools": tools or None, "handoff": handoff,
         "llm": [{"kind": "turno", "output": "{}"},
                 *([{"kind": "herramienta", "output": trace_output}] if trace_output else [])]},
        {"role": "user", "text": "Gracias."},
    ]


def progreso(cid):
    return {
        "variables": {"nombre": "Ana", "horario": "tarde"},
        "variable_sources": {"nombre": "contact", "horario": "tool:estrella_salidas"},
        "hidden_variables": ["horario"],
        "call": {"id": cid, "from": "+5491155550000", "mode": "api"},
        "started_at": "2026-11-20T10:00:00-03:00",
        "caller_phone": "+5491155550000",
        "handoff_areas": [{"id": "a1", "name": "Operaciones", "when": "consultas", "schedule": None}],
    }


def setup(api, admin, **kwargs):
    c = make_client(admin)
    agent = make_agent(admin, c)
    cid = make_conversation(api, agent, mensajes(**kwargs), progreso("x"))
    # El id de progress.call es el de la conversacion (el worker lo fija asi).
    with api.sessions() as s:
        row = s.get(ConversationRow, cid)
        row.progress = {**row.progress, "call": {**row.progress["call"], "id": cid}}
        s.commit()
    return c, agent, cid


# ---------- snapshot y preview ----------

def test_preview_copia_sin_trazas_ni_variables_de_herramienta(api, admin):
    c, agent, cid = setup(api, admin, tool_result='{"hay_lugar": 2}', handoff="Operaciones")
    r = admin.post(f"{V1}/agents/{agent['id']}/test-cases/preview",
                   json={"conversation_id": cid, "message_index": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    snapshot = body["snapshot"]
    assert snapshot["user_message"] == "¿Hay salidas a Castelli?"
    assert [m["text"] for m in snapshot["messages"]] == ["Hola, soy Sofía."]
    assert "llm" not in snapshot["messages"][0] and "recording" not in snapshot["messages"][0]
    # Las variables que asigno una herramienta no estaban en el prompt del turno.
    assert snapshot["progress"]["variables"] == {"nombre": "Ana"}
    assert snapshot["progress"]["variable_sources"] == {"nombre": "contact"}
    assert snapshot["progress"]["hidden_variables"] == []
    # El chat de prueba (mode api) simula la llamada: puede derivar.
    assert snapshot["handoff"] is True and body["reply"]["handoff"] == "Operaciones"
    assert body["reply"]["text"].startswith("Hay dos salidas")
    assert body["reply"]["tool_calls"] == [{"name": "estrella_salidas", "arguments": '{"destino": "Castelli"}'}]
    assert body["reply"]["tool_results"] == ['{"hay_lugar": 2}']
    assert {"type": "no_deriva"} in body["checks"]
    assert {"type": "usa_herramienta", "tool": "estrella_salidas"} in body["checks"]
    # No guardo nada.
    with api.sessions() as s:
        assert s.query(AgentTestCase).count() == 0


def test_preview_toma_la_salida_completa_de_la_traza_si_el_resultado_se_recorto(api, admin):
    recortado = '{"salidas": [' + "x" * 100 + TRUNCATED
    c, agent, cid = setup(api, admin, tool_result=recortado, trace_output='{"salidas": [{"hora": "12:00"}]}')
    body = admin.post(f"{V1}/agents/{agent['id']}/test-cases/preview",
                      json={"conversation_id": cid, "message_index": 1}).json()
    assert body["reply"]["tool_results"] == ['{"salidas": [{"hora": "12:00"}]}']


def test_preview_rechaza_un_indice_que_no_es_del_usuario(api, admin):
    c, agent, cid = setup(api, admin)
    for index in (0, 2):
        r = admin.post(f"{V1}/agents/{agent['id']}/test-cases/preview",
                       json={"conversation_id": cid, "message_index": index})
        assert r.status_code == 422 and r.json()["code"] == "invalid_message_index"


def test_preview_rechaza_un_mensaje_de_un_tramo_derivado(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    messages = mensajes()
    messages[1]["handoff_leg"] = "leg-1"
    cid = make_conversation(api, agent, messages, progreso("x"))
    r = admin.post(f"{V1}/agents/{agent['id']}/test-cases/preview",
                   json={"conversation_id": cid, "message_index": 1})
    assert r.status_code == 422 and r.json()["code"] == "invalid_message_index"


def test_preview_conversacion_de_otro_agente_o_cliente_da_404(api, admin):
    c, agent, cid = setup(api, admin)
    otro = make_agent(admin, c, template="demo_booking", slug="turnos", name="Turnos")
    r = admin.post(f"{V1}/agents/{otro['id']}/test-cases/preview",
                   json={"conversation_id": cid, "message_index": 1})
    assert r.status_code == 404
    c2 = make_client(admin, slug="beta")
    agent2 = make_agent(admin, c2)
    r = admin.post(f"{V1}/agents/{agent2['id']}/test-cases/preview",
                   json={"conversation_id": cid, "message_index": 1})
    assert r.status_code == 404


# ---------- crear, leer, editar, borrar ----------

def test_crear_caso_con_pisados(api, admin):
    c, agent, cid = setup(api, admin, tool_result='{"hay_lugar": 2}')
    body = {"conversation_id": cid, "message_index": 1, "name": "Salidas a Castelli",
            "checks": [{"type": "dice", "text": "hay lugar"}, {"type": "no_dice", "text": "asientos libres"}],
            "known_failure": True,
            "user_message": "¿Hay lugar en el de las doce?",
            "tool_results": [{"name": "estrella_salidas", "arguments": {}, "result": {"hay_lugar": 1}}]}
    r = admin.post(f"{V1}/agents/{agent['id']}/test-cases", json=body)
    assert r.status_code == 201, r.text
    case = r.json()
    assert case["name"] == "Salidas a Castelli" and case["known_failure"] is True
    assert case["snapshot"]["user_message"] == "¿Hay lugar en el de las doce?"
    assert case["tool_results"][0]["result"] == '{"hay_lugar": 1}'
    assert case["history"] == []
    assert case["last_run"] is None

    # Lo lee y lo edita.
    got = admin.get(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}").json()
    assert got["checks"] == body["checks"]
    r = admin.patch(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}",
                    json={"name": "Otro nombre", "checks": [{"type": "no_deriva"}]})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Otro nombre" and r.json()["checks"] == [{"type": "no_deriva"}]
    # Los chequeos invalidos no se guardan.
    r = admin.patch(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}",
                    json={"checks": [{"type": "dice"}]})
    assert r.status_code == 422 and r.json()["code"] == "invalid_checks"
    # Aparece en la lista.
    lista = admin.get(f"{V1}/agents/{agent['id']}/test-cases").json()
    assert [x["id"] for x in lista] == [case["id"]]
    assert admin.delete(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}").status_code == 204
    assert admin.get(f"{V1}/agents/{agent['id']}/test-cases").json() == []


def test_chequeos_invalidos_al_crear(api, admin):
    c, agent, cid = setup(api, admin)
    r = admin.post(f"{V1}/agents/{agent['id']}/test-cases",
                   json={"conversation_id": cid, "message_index": 1, "name": "x",
                         "checks": [{"type": "desconocido"}]})
    assert r.status_code == 422 and r.json()["code"] == "invalid_checks"
    assert r.json()["errors"][0]["path"] == "checks.0.type"


def test_tope_de_casos(api, admin):
    c, agent, cid = setup(api, admin)
    with api.sessions() as s:
        for i in range(30):
            s.add(AgentTestCase(client_id=c["id"], agent_id=agent["id"], name=f"Caso {i}", channel="voice",
                                snapshot={"messages": [], "user_message": "x", "progress": {}},
                                tool_results=[], checks=[]))
        s.commit()
    r = admin.post(f"{V1}/agents/{agent['id']}/test-cases",
                   json={"conversation_id": cid, "message_index": 1, "name": "Extra"})
    assert r.status_code == 422 and r.json()["code"] == "too_many_cases"


def test_caso_y_agente_de_otro_cliente_dan_404(api, admin):
    c, agent, cid = setup(api, admin)
    case = admin.post(f"{V1}/agents/{agent['id']}/test-cases",
                      json={"conversation_id": cid, "message_index": 1, "name": "Caso"}).json()
    c2 = make_client(admin, slug="beta")
    agent2 = make_agent(admin, c2)
    assert admin.get(f"{V1}/agents/{agent2['id']}/test-cases/{case['id']}").status_code == 404
    assert admin.delete(f"{V1}/agents/{agent2['id']}/test-cases/{case['id']}").status_code == 404
    # El agente de otro cliente tampoco.
    assert admin.get(f"{V1}/agents/nope/test-cases").status_code == 404


def test_usuario_no_admin_solo_lee(api, admin):
    c, agent, cid = setup(api, admin)
    case = admin.post(f"{V1}/agents/{agent['id']}/test-cases",
                      json={"conversation_id": cid, "message_index": 1, "name": "Caso"}).json()
    user = client_user(api, admin, c, email="user@acme.com", client_role="user")
    assert user.get(f"{V1}/agents/{agent['id']}/test-cases").status_code == 200
    assert user.get(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}").status_code == 200
    r = user.post(f"{V1}/agents/{agent['id']}/test-cases",
                  json={"conversation_id": cid, "message_index": 1, "name": "Otro"})
    assert r.status_code == 403
    assert user.patch(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}",
                      json={"name": "x"}).status_code == 403
    assert user.delete(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}").status_code == 403


def test_key_mcp_read_no_escribe(api, admin):
    c, agent, cid = setup(api, admin)
    key = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "lectura", "scopes": ["mcp_read"]}).json()
    headers = {"Authorization": f"Bearer {key['key']}"}
    assert api.client.get(f"{V1}/agents/{agent['id']}/test-cases", headers=headers).status_code == 200
    r = api.client.post(f"{V1}/agents/{agent['id']}/test-cases", headers=headers,
                        json={"conversation_id": cid, "message_index": 1, "name": "Caso"})
    assert r.status_code == 403 and r.json()["code"] == "scope_missing"


def test_admin_entrando_como_el_cliente_puede(api, admin):
    c, agent, cid = setup(api, admin)
    headers = {"X-Atentina-Client": c["id"]}
    r = admin.post(f"{V1}/agents/{agent['id']}/test-cases", headers=headers,
                   json={"conversation_id": cid, "message_index": 1, "name": "Caso"})
    assert r.status_code == 201, r.text


def test_agente_externo_no_tiene_casos(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c, template="sales_discovery")
    definition = {**agent["definition"], "tools": [], "external": {"connection": "x"}}
    # La definicion externa se valida al guardar; para el caso alcanza con la marca en la fila.
    with api.sessions() as s:
        from app.models import Agent
        row = s.get(Agent, agent["id"])
        row.definition = {**row.definition, "external": {"connection": "x"}}
        s.commit()
    cid = make_conversation(api, agent, mensajes())
    r = admin.post(f"{V1}/agents/{agent['id']}/test-cases/preview",
                   json={"conversation_id": cid, "message_index": 1})
    assert r.status_code == 422 and r.json()["code"] == "external_agent_not_supported"


def test_borrar_la_conversacion_deja_el_origen_en_null(api, admin):
    c, agent, cid = setup(api, admin)
    case = admin.post(f"{V1}/agents/{agent['id']}/test-cases",
                      json={"conversation_id": cid, "message_index": 1, "name": "Caso"}).json()
    with api.sessions() as s:
        calls_service.delete_conversations(s, [cid])
    got = admin.get(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}").json()
    assert got["source_conversation_id"] is None
    assert got["snapshot"]["user_message"] == "¿Hay salidas a Castelli?"


def test_historial_con_muchas_corridas_de_otros(api, admin):
    """201 corridas `done` más nuevas de otro cliente y de otro agente no tapan las del caso."""
    import datetime

    from app.models import AgentTestRun

    c, agent, cid = setup(api, admin)
    case = admin.post(f"{V1}/agents/{agent['id']}/test-cases",
                      json={"conversation_id": cid, "message_index": 1, "name": "Caso"}).json()
    otro_cliente = make_client(admin, slug="beta")
    agente_ajeno = make_agent(admin, otro_cliente)
    otro_agente = make_agent(admin, c, template="demo_booking", slug="turnos", name="Turnos")
    base = datetime.datetime(2026, 11, 21)
    with api.sessions() as s:
        for i in range(201):
            ajeno = agente_ajeno if i % 2 else otro_agente
            s.add(AgentTestRun(client_id=ajeno["client_id"], agent_id=ajeno["id"], status="done", repetitions=1,
                               variants=[], cases=[{"id": case["id"], "name": "Caso"}], done=1, total=1,
                               created_at=base + datetime.timedelta(minutes=i)))
        # La del caso, más vieja.
        s.add(AgentTestRun(client_id=c["id"], agent_id=agent["id"], status="done", repetitions=1,
                           variants=[{"key": "publicada", "version": 1}],
                           cases=[{"id": case["id"], "name": "Caso"}],
                           summary=[{"case_id": case["id"],
                                     "variants": [{"key": "publicada", "passed": 1, "total": 1}]}],
                           done=1, total=1, created_at=base - datetime.timedelta(days=1)))
        s.commit()
    detalle = admin.get(f"{V1}/agents/{agent['id']}/test-cases/{case['id']}").json()
    assert len(detalle["history"]) == 1
    assert detalle["history"][0]["variants"] == [{"key": "publicada", "passed": 1, "total": 1, "fallbacks": 0}]
    assert admin.get(f"{V1}/agents/{agent['id']}/test-cases").json()[0]["last_run"]["run_id"] == \
        detalle["history"][0]["run_id"]
