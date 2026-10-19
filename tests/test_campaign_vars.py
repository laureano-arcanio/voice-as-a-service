"""Campañas de voz, fase 3 (docs/LLAMADAS_SALIENTES_PLAN.md, 4 y 10): datos del contacto en la
conversacion (apertura con {{variable}}, campos precargados, prompt), el reporte por contacto
(report.csv), los indicadores y el filtro por campaña de las llamadas."""
import csv
import datetime
import io

import pytest
from sqlalchemy import select

from app.agents.definitions import DbDefinitions
from app.agents.templates import load_reference, reference_data
from app.conversation import contact as contact_data
from app.conversation.assistant import build_system
from app.conversation.engine import ConversationEngine
from app.conversation.models import ConversationState
from app.db import utcnow
from app.llm.prompt import (
    build_classic_messages,
    build_classic_system,
    build_user_prompt,
)
from app.models import CallRow, Campaign, CampaignContact
from app.services import campaign_reports

from .helpers import FakeLLM
from .test_api import V1, client_user, make_agent, make_client
from .test_campaign_dialer import close, dialer_for, members
from .test_campaigns import load_contacts, voice_body
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_campaigns import (
    CampaignGraph,
    make_campaign,
    recipients,
    sender_for,
)
from .test_whatsapp_service import (
    WA_ID,
    conversations,
    make_wa,
    reply,
    send,
    status_payload,
    text_payload,
)

OPENING = "Hola {{nombre}}, te habla Valentina de Fibranet. ¿Hablo con {{Nombre}} por la deuda de ${{deuda}}?"


# ---------- variables en la apertura ----------

def test_render_template_replaces_by_name():
    vars = {"nombre": "Ana", "deuda": 15000.0, "Fecha Vence": "2026-11-01", "params": ["x"]}
    assert contact_data.render_template("{{nombre}} debe ${{ deuda }}", vars) == "Ana debe $15000"
    # Sin importar mayusculas ni acentos, como los atributos del contacto.
    assert contact_data.render_template("Vence el {{fecha_vence}}. {{NOMBRE}}", vars) == "Vence el 2026-11-01. Ana"
    assert contact_data.render_template("Hola.", vars) == "Hola."


def test_render_template_missing_variable_is_empty_and_tidy():
    assert contact_data.render_template("Hola {{nombre}}, soy Valentina.", {}) == "Hola, soy Valentina."
    assert contact_data.render_template("Hola {{nombre}}! ¿Cómo estás?", {"nombre": ""}) == "Hola! ¿Cómo estás?"
    # Los valores posicionales de WhatsApp no son variables del contacto.
    assert contact_data.render_template("{{params}}|{{1}}", {"params": ["x"]}) == "|"
    # Sin variables faltantes el texto no se toca.
    assert contact_data.render_template("Hola  {{nombre}} , soy", {"nombre": "Ana"}) == "Hola  Ana , soy"


# ---------- campos precargados ----------

def test_preload_matches_workflow_fields_and_keeps_the_rest():
    wf = load_reference("eval_cobranza")     # cuotas: integer, promesa: choice
    fields, rest = contact_data.preload(wf, {"nombre": "Ana", "Cuotas": "3", "promesa": "cuotas", "deuda": 15000,
                                             "motivo": "", "params": ["x"]})
    assert fields == {"cuotas": 3, "promesa": "cuotas"}
    assert rest == {"nombre": "Ana", "deuda": 15000}      # sin vacios ni params
    # Un valor que el tipo del campo no acepta no se precarga: queda como dato del contacto.
    fields, rest = contact_data.preload(wf, {"cuotas": "muchas", "promesa": "nunca"})
    assert fields == {} and rest == {"cuotas": "muchas", "promesa": "nunca"}


def test_new_conversation_with_contact(store):
    engine = ConversationEngine(FakeLLM(), store)
    wf = reference_data("eval_cobranza")
    state, text = engine.new_conversation("eval_cobranza", contact={"nombre": "Ana", "titular": "true", "deuda": 100})
    assert text == wf["conversation"]["opening"] == state.messages[0].text      # sin variables: igual
    assert state.fields["titular"] is True and state.progress.preloaded == ["titular"]
    assert state.progress.contact == {"nombre": "Ana", "deuda": 100}
    # La apertura pregunta por el primer dato que falta: titular ya viene cargado.
    assert state.progress.asked == "mejor_momento"
    # Sin contact (llamada entrante o de prueba) nada cambia.
    state, _ = engine.new_conversation("eval_cobranza")
    assert state.progress.contact == {} and state.progress.preloaded == [] and state.progress.asked == "titular"
    assert all(v is None for v in state.fields.values())


def test_new_conversation_opening_text_is_rendered_only_with_contact(store):
    engine = ConversationEngine(FakeLLM(), store)
    _, text = engine.new_conversation("eval_cobranza", opening="Hola {{nombre}}", contact={"nombre": "Ana"})
    assert text == "Hola Ana"
    _, text = engine.new_conversation("eval_cobranza", opening="Hola {{nombre}}")
    assert text == "Hola {{nombre}}"
    state, text = engine.new_conversation("eval_cobranza", opening=False, contact={"nombre": "Ana"})
    assert text == "" and state.messages == [] and state.progress.contact == {"nombre": "Ana"}


def test_contact_survives_the_store(store):
    engine = ConversationEngine(FakeLLM(), store)
    state, _ = engine.start_conversation("eval_cobranza", contact={"nombre": "Ana", "cuotas": 3})
    again = store.get(state.conversation_id)
    assert again.progress.contact == {"nombre": "Ana"} and again.progress.preloaded == ["cuotas"]
    assert again.fields["cuotas"] == 3


# ---------- el prompt, en los tres motores ----------

def _state(wf, **kw) -> ConversationState:
    return ConversationState(conversation_id="c", agent_id=wf.id, fields={n: None for n in wf.fields}, **kw)


def test_classic_prompt_has_the_contact_data_only_when_there_is():
    wf = load_reference("eval_cobranza_classic")
    plain = build_classic_system(wf, "voice", _state(wf))
    assert plain == build_classic_system(wf) and "DATOS DEL CONTACTO" not in plain
    state = _state(wf)
    state.progress.contact = {"nombre": "Ana", "deuda": 15000}
    state.progress.preloaded = ["cuotas"]
    state.fields["cuotas"] = 3
    system = build_classic_system(wf, "voice", state)
    assert "DATOS DEL CONTACTO" in system and "- nombre: Ana" in system and "- deuda: 15000" in system
    assert "DATOS YA CONOCIDOS" in system and "- cuotas: 3" in system
    assert build_classic_messages(wf, state, "Hola")[0]["content"] == system


def test_structured_prompt_has_the_contact_data():
    wf = load_reference("eval_cobranza")
    state = _state(wf)
    assert "DATOS DEL CONTACTO" not in build_user_prompt(wf, state, "Hola")
    state.progress.contact = {"nombre": "Ana"}
    state.fields["cuotas"], state.progress.preloaded = 3, ["cuotas"]
    prompt = build_user_prompt(wf, state, "Hola")
    # Va antes de la conversacion (prefix caching); lo precargado ya esta en known_fields.
    assert prompt.index("- nombre: Ana") < prompt.index("CONVERSATION:")
    assert '"cuotas": 3' in prompt and "cuotas" not in prompt.split("pending_objectives")[1].split("]")[0]


def test_assistant_prompt_has_the_contact_data():
    wf = load_reference("eval_cobranza")
    state = _state(wf)
    assert "DATOS DEL CONTACTO" not in build_system(wf, state, [])
    state.progress.contact = {"nombre": "Ana"}
    assert "- nombre: Ana" in build_system(wf, state, [])


# ---------- la llamada de una campaña ----------

@pytest.fixture
def cobranza(api, admin):  # noqa: F811
    """Un cliente con campañas de voz y un agente de cobranza con {{variables}} en la apertura."""
    c = make_client(admin, slug="cobra", campaign_channels=["voice"])
    definition = reference_data("eval_cobranza")
    definition["conversation"]["opening"] = OPENING
    agent = make_agent(admin, c, definition=definition)
    return client_user(api, admin, c, email="cobra@x.com"), agent, c


def start_campaign(user, agent, rows, **extra) -> dict:
    load_contacts(user, rows)
    body = voice_body(agent, tags=["mora"], window_start=0, window_end=24, rate_per_minute=600, **extra)
    camp = user.post(f"{V1}/campaigns", json=body).json()["campaign"]
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    return camp


ROWS = [{"phone": "351 555-1001", "name": "Ana", "attributes": {"deuda": 15000, "cuotas": "3"}, "tags": ["mora"],
         "external_id": "A-1"},
        {"phone": "351 555-1002", "attributes": {}, "tags": ["mora"]}]


async def test_the_call_carries_the_contact_data(api, cobranza):
    user, agent, _ = cobranza
    camp = start_campaign(user, agent, ROWS, concurrency=2)
    assert await dialer_for(api).tick() == 2
    ana, sin_datos = members(api, camp["id"])
    state = api.engine.store.get(ana.conversation_id)
    assert state.messages[0].text == ("Hola Ana, te habla Valentina de Fibranet. ¿Hablo con Ana por la deuda de "
                                      "$15000?")
    # `cuotas` es un campo del agente: viene cargado y el agente no lo pregunta. El resto va al prompt.
    assert state.fields["cuotas"] == 3 and state.progress.preloaded == ["cuotas"]
    assert state.progress.contact == {"nombre": "Ana", "telefono": "+5493515551001", "external_id": "A-1",
                                      "deuda": 15000}
    # Un contacto sin nombre ni deuda: las variables quedan vacias y el texto, acomodado.
    other = api.engine.store.get(sin_datos.conversation_id)
    assert other.messages[0].text == "Hola, te habla Valentina de Fibranet. ¿Hablo con por la deuda de $?"
    assert other.fields["cuotas"] is None and other.progress.preloaded == []
    assert other.progress.contact == {"telefono": "+5493515551002"}


# ---------- reporte e indicadores ----------

def answer(api, member: CampaignContact, *, seconds=60, hour=14, promesa=None):
    """El intento atendido: la llamada se conecto, duro `seconds` y la conversacion termino con esa promesa."""
    with api.sessions() as s:
        call = s.scalar(select(CallRow).where(CallRow.campaign_contact_id == member.id))
        call.status, call.duration_seconds = "finalizada", seconds
        call.created_at = call.started_at = datetime.datetime(2026, 10, 19, hour + 3, 0, tzinfo=datetime.UTC).replace(tzinfo=None)    # hora local = UTC-3
        s.commit()
    if promesa:
        state = api.engine.store.get(member.conversation_id)
        state.fields.update({"titular": True, "promesa": promesa, "fecha_pago": "2026-10-20" if promesa == "paga_total" else None})
        state.status = "completed"
        api.engine.store.save(state)
    close(api, member.id, "answered")


async def test_report_csv_and_stats(api, cobranza):
    user, agent, _ = cobranza
    rows = ROWS + [{"phone": "351 555-1003", "tags": ["mora"]}, {"phone": "351 555-1004", "tags": ["mora"]}]
    camp = start_campaign(user, agent, rows, concurrency=4)
    assert await dialer_for(api).tick() == 4
    ana, b, c, d = members(api, camp["id"])
    answer(api, ana, seconds=120, hour=14, promesa="paga_total")       # objetivo cumplido
    answer(api, b, seconds=60, hour=14, promesa="ya_pago")             # atendio, sin objetivo
    close(api, c.id, "busy")                                            # reintenta
    close(api, d.id, "invalid", error={"message": "Número inexistente"})

    r = user.get(f"{V1}/campaigns/{camp['id']}/report.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.startswith("﻿")
    table = list(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
    assert list(table[0]) == campaign_reports.REPORT_COLUMNS and len(table) == 4
    a, bb, cc, dd = table
    assert (a["external_id"], a["telefono"], a["nombre"], a["estado"], a["resultado"], a["intentos"]) == (
        "A-1", "+5493515551001", "Ana", "done", "answered", "1")
    assert (a["duracion_segundos"], a["outcome"]) == ("120", "Compromiso de pago total")
    assert (bb["duracion_segundos"], bb["outcome"]) == ("60", "Dice que ya pagó")
    assert (a["objetivo"], bb["objetivo"]) == ("si", "no")
    assert '"deuda":15000' in a["vars"] and '"promesa":"paga_total"' in a["campos"] and '"cuotas":3' in a["campos"]
    assert a["conversation_id"] == ana.conversation_id and a["link"].endswith(f"/calls/{ana.conversation_id}")
    assert (cc["estado"], cc["resultado"], cc["intentos"], cc["objetivo"]) == ("retry", "busy", "1", "")
    assert (dd["estado"], dd["resultado"], dd["error"]) == ("failed", "invalid", "Número inexistente")
    assert user.get(f"{V1}/campaigns/{camp['id']}/report.csv").status_code == 200
    assert api.client.get(f"{V1}/campaigns/{camp['id']}/report.csv").status_code == 401

    st = user.get(f"{V1}/campaigns/{camp['id']}/stats").json()
    assert (st["channel"], st["contacts"], st["attempts"], st["reached"]) == ("voice", 4, 4, 2)
    assert st["contact_rate"] == 50.0 and st["goal"] == 1 and st["goal_rate"] == 50.0
    assert st["avg_duration_seconds"] == 90 and st["minutes"] == 3.0
    assert st["results"]["answered"] == 2 and st["results"]["busy"] == 1 and st["results"]["invalid"] == 1
    by_hour = {h["hour"]: h for h in st["by_hour"]}
    assert len(st["by_hour"]) == 24 and by_hour[14] == {"hour": 14, "attempts": 2, "reached": 2}
    assert sum(h["attempts"] for h in st["by_hour"]) == 4 and st["timezone"]


def test_csv_cells_are_safe_for_excel():
    assert campaign_reports._cell("=HYPERLINK(\"x\")") == "'=HYPERLINK(\"x\")"
    assert campaign_reports._cell("@usuario") == "'@usuario"
    assert campaign_reports._cell("+549 351 555-1234") == "+549 351 555-1234"
    assert campaign_reports._cell("-cmd") == "'-cmd"
    assert campaign_reports._cell(None) == "" and campaign_reports._cell(3) == "3"


async def test_report_permissions(api, admin, cobranza):  # noqa: F811
    user, agent, _ = cobranza
    camp = start_campaign(user, agent, ROWS[:1])
    other = make_client(admin, slug="otro", campaign_channels=["voice"])
    stranger = client_user(api, admin, other, email="otro@x.com")
    for path in ("report.csv", "stats"):
        assert stranger.get(f"{V1}/campaigns/{camp['id']}/{path}").status_code == 404
        assert admin.get(f"{V1}/campaigns/{camp['id']}/{path}").status_code == 200
    assert user.get(f"{V1}/campaigns/inexistente/stats").status_code == 404


async def test_calls_and_stats_filter_by_campaign(api, cobranza):
    user, agent, _ = cobranza
    camp = start_campaign(user, agent, ROWS, concurrency=2)
    other = user.post(f"{V1}/calls", json={"agent_id": agent["id"]})       # una de prueba, fuera de la campaña
    assert other.status_code == 201, other.text
    assert await dialer_for(api).tick() == 2
    ana, _ = members(api, camp["id"])
    answer(api, ana, promesa="paga_total")

    assert user.get(f"{V1}/calls").json()["total"] == 3
    page = user.get(f"{V1}/calls", params={"campaign_id": camp["id"]}).json()
    assert page["total"] == 2 and {i["id"] for i in page["items"]} >= {ana.conversation_id}
    assert other.json()["conversation_id"] not in {i["id"] for i in page["items"]}
    stats = user.get(f"{V1}/stats", params={"campaign_id": camp["id"]}).json()
    assert (stats["total"], stats["calls"], stats["goal"]) == (2, 2, 1)
    assert user.get(f"{V1}/calls", params={"campaign_id": "inexistente"}).json()["total"] == 0
    day = utcnow().date()
    daily = user.get(f"{V1}/stats/daily", params={"campaign_id": camp["id"], "date_from": str(day - datetime.timedelta(1)),
                                                  "date_to": str(day + datetime.timedelta(1))}).json()
    assert sum(daily["totals"]) == 2


async def test_campaign_filter_does_not_cross_clients(api, admin, cobranza):  # noqa: F811
    user, agent, _ = cobranza
    camp = start_campaign(user, agent, ROWS, concurrency=2)
    assert await dialer_for(api).tick() == 2
    other = make_client(admin, slug="ajeno", campaign_channels=["voice"])
    stranger = client_user(api, admin, other, email="ajeno@x.com")
    # Otro cliente no ve nada filtrando por la campaña de este; el admin si.
    assert stranger.get(f"{V1}/calls", params={"campaign_id": camp["id"]}).json()["total"] == 0
    assert stranger.get(f"{V1}/stats", params={"campaign_id": camp["id"]}).json()["total"] == 0
    assert admin.get(f"{V1}/calls", params={"campaign_id": camp["id"]}).json()["total"] == 2


async def test_whatsapp_campaign_report_and_stats(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("¡Genial! ¿Querés que te llame?")), graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001")
    await sender_for(w).tick()
    await send(w, status_payload("status_read.json", "wamid.tpl1"))
    await send(w, text_payload("sí, contame", "wamid.in1"))
    (conv,) = conversations(sessions)
    definitions = DbDefinitions(sessions)
    with sessions() as s:
        camp = s.get(Campaign, cid)
        st = campaign_reports.stats(s, camp, definitions)
        table = list(csv.DictReader(io.StringIO(campaign_reports.report_csv(s, camp, definitions).lstrip("﻿"))))
    assert (st["channel"], st["contacts"], st["attempts"], st["reached"], st["contact_rate"]) == (
        "whatsapp", 2, 2, 1, 50.0)
    assert st["results"] == {"sent": 2, "delivered": 1, "read": 1, "replied": 1}
    assert st["avg_duration_seconds"] is None and st["minutes"] is None
    assert sum(h["attempts"] for h in st["by_hour"]) == 2 and sum(h["reached"] for h in st["by_hour"]) == 1
    first, second = table
    assert (first["telefono"], first["resultado"], first["estado"], first["intentos"]) == ("+" + WA_ID, "replied", "done", "1")
    assert first["conversation_id"] == conv.id and first["link"].endswith(f"/calls/{conv.id}")
    assert (second["resultado"], second["conversation_id"], second["link"]) == ("sent", "", "")
    assert recipients(sessions, cid)[0].replied_at is not None
