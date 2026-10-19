"""Campañas de voz, fase 4 (docs/LLAMADAS_SALIENTES_PLAN.md, secciones 4, 5, 6, 8 y 11): contestador por
heuristica, feriados, finalidad y Registro No Llame, baja por voz, seguimiento por WhatsApp y webhook."""
import datetime
import hashlib
import hmac
import json

import httpx
import pytest
from sqlalchemy import select

from app.agents.templates import load_reference
from app.campaigns.callbacks import CallbackDispatcher, backoff
from app.campaigns.voicemail import VoicemailDetector, looks_like_voicemail, normalize
from app.config import settings
from app.conversation.models import Outcome
from app.models import (
    Campaign,
    CampaignCallback,
    CampaignContact,
    Contact,
    ContactOptout,
    ConversationRow,
)
from app.services import campaign_callbacks, campaign_calls
from app.services import campaigns as common
from app.whatsapp import campaigns as wa
from app.whatsapp.sender import CampaignSender

from .helpers import FakeLLM
from .test_api import V1
from .test_campaign_dialer import (
    Now,
    campaign,
    close,
    dialer_for,
    make_voice,
    members,
    naive_utc,
    states,
)
from .test_campaigns import (  # noqa: F401  (fixtures)
    load_contacts,
    voice,
    voice_body,
)
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_campaigns import (  # noqa: F401  (fixtures)
    CampaignGraph,
    Clock,
    account,
)
from .test_whatsapp_service import (
    WA_ID,
    conversations,
    make_wa,
    send,
    text_payload,
)
from .test_whatsapp_signup import acme, meta  # noqa: F401  (fixtures)

# ---------- contestador (seccion 5) ----------


@pytest.mark.parametrize("text", [
    "Hola, deje su mensaje después de la señal",
    "Deje un mensaje y le devolveremos la llamada.",
    "Está comunicado con el buzón de voz de Juan",
    "El número al que usted llamó no está disponible",
    "Su llamada será transferida al contestador automático",
    "Hola, soy Laura, no puedo atender en este momento. Después del tono, dejá tu mensaje",
    "El abonado se encuentra apagado o fuera del área de cobertura",
    "Gracias por llamar. Deja tu mensaje.",
    "DEJE SU MENSAJE",
])
def test_voicemail_phrases(text):
    assert looks_like_voicemail(text)


@pytest.mark.parametrize("text", [
    "", "hola", "Hola, buenas tardes", "¿Quién habla?", "Sí, dígame", "No me interesa, gracias",
    "Estoy manejando, llamame más tarde", "Mi mensaje de ayer era otro tema", "No, no tengo tiempo ahora",
])
def test_humans_are_not_voicemail(text):
    assert not looks_like_voicemail(text)


def test_normalize():
    assert normalize("  ¡Después de la SEÑAL!  ") == "despues de la senal"


def test_detector_only_looks_at_the_first_turns():
    d = VoicemailDetector(segments=3)
    assert not d.feed("Hola", is_final=False)
    assert not d.feed("Hola, buenas", True)
    assert not d.feed("   ", True)                              # vacio: no cuenta como turno
    assert not d.feed("Este es el buzón", False)                # parcial: se ignora
    assert d.feed("Deje su mensaje", True) and d.detected      # el saludo llega en pedazos
    assert not d.feed("Deje su mensaje", True)                  # avisa una sola vez

    late = VoicemailDetector(segments=2)
    late.feed("Hola", True)
    late.feed("Sí, ¿quién habla?", True)
    assert not late.feed("Deje su mensaje", True) and not late.detected


def test_detector_joins_the_pieces():
    d = VoicemailDetector()
    assert not d.feed("No está", True)
    assert d.feed("disponible, deje su mensaje", True)


async def test_voicemail_retries_and_ends_in_done(api, voice):  # noqa: F811
    """`voicemail` entra en los reintentos por default; agotados los intentos, el contacto queda done."""
    user, agent, _ = voice
    camp = make_voice(user, agent, n=1, concurrency=1, rate_per_minute=600, max_attempts=2)
    now = Now()
    dialer = dialer_for(api, now=now)
    assert await dialer.tick() == 1
    (m,) = members(api, camp["id"])
    close(api, m.id, "voicemail", now=now.t)
    assert states(api, camp["id"]) == [("retry", "voicemail", 1)]
    now.advance(minutes=61)
    assert await dialer.tick() == 1
    close(api, m.id, "voicemail", now=now.t)
    assert states(api, camp["id"]) == [("done", "voicemail", 2)]
    assert campaign(api, camp["id"]).status == "done"


async def test_close_attempt_as_voicemail_is_idempotent_with_the_final_answered(api, voice):  # noqa: F811
    """El worker cierra como `voicemail` y despues finalize intenta `answered`: no pisa el resultado."""
    user, agent, _ = voice
    camp = make_voice(user, agent, n=1, concurrency=1, rate_per_minute=600)
    await dialer_for(api).tick()
    (m,) = members(api, camp["id"])
    with api.sessions() as s:
        assert campaign_calls.close_attempt(s, m.conversation_id, "voicemail") is not None
        assert campaign_calls.close_attempt(s, m.conversation_id, "answered") is None
        s.commit()
    assert states(api, camp["id"])[0][1] == "voicemail"


# ---------- feriados (seccion 11) ----------

def test_holidays_setting(monkeypatch):
    monkeypatch.setattr(settings, "campaign_holidays", " 2026-12-25, basura ,2027-01-01,,")
    assert common.holidays() == {datetime.date(2026, 12, 25), datetime.date(2027, 1, 1)}
    monkeypatch.setattr(settings, "campaign_holidays", "")
    assert common.holidays() == frozenset()


async def test_dialer_skips_holidays_only_for_voice(api, voice, monkeypatch):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=5, rate_per_minute=600)
    monday = naive_utc(2026, 10, 19, 15)       # 12:00 en Buenos Aires
    now, clock = Now(monday), Clock()
    monkeypatch.setattr(settings, "campaign_holidays", "2026-10-19")
    dialer = dialer_for(api, now=now, clock=clock)
    assert await dialer.tick() == 0 and states(api, camp["id"]) == [("pending", None, 0)] * 3
    c = campaign(api, camp["id"])
    assert not common.in_window(c, monday)
    wa_like = Campaign(channel="whatsapp", window_start=0, window_end=24, weekdays=None)
    assert common.in_window(wa_like, monday)       # las de WhatsApp no los miran
    # El feriado se mira en hora local: a las 22:00 de Buenos Aires del dia anterior ya es el 20 en UTC.
    monkeypatch.setattr(settings, "campaign_holidays", "2026-10-20")
    clock.t += 2
    assert await dialer.tick() == 3


# ---------- finalidad y Registro No Llame (seccion 11) ----------

def test_commercial_campaign_needs_the_registry_confirmation(api, voice):  # noqa: F811
    user, agent, _ = voice
    load_contacts(user)
    body = voice_body(agent, purpose="comercial", tags=["mora"])
    camp = user.post(f"{V1}/campaigns", json=body).json()["campaign"]
    assert camp["purpose"] == "comercial" and camp["registry_confirmed"] is False
    r = user.post(f"{V1}/campaigns/{camp['id']}/start")
    assert r.status_code == 422 and "Registro No Llame" in r.json()["detail"]
    assert user.post(f"{V1}/campaigns/{camp['id']}/start", json={"no_call_registry_checked": False}).status_code == 422
    started = user.post(f"{V1}/campaigns/{camp['id']}/start", json={"no_call_registry_checked": True}).json()
    assert started["status"] == "running" and started["registry_confirmed"] is True
    # Ya confirmada: pausar y retomar no la pide de nuevo.
    assert user.post(f"{V1}/campaigns/{camp['id']}/pause").status_code == 200
    assert user.post(f"{V1}/campaigns/{camp['id']}/resume").json()["status"] == "running"


def test_registry_confirmation_comes_with_start_on_create(api, voice):  # noqa: F811
    user, agent, _ = voice
    load_contacts(user)
    body = voice_body(agent, purpose="comercial", tags=["mora"], start=True)
    r = user.post(f"{V1}/campaigns", json=body)
    assert r.status_code == 422                                      # no queda nada creado
    assert user.get(f"{V1}/campaigns").json() == []
    ok = user.post(f"{V1}/campaigns", json={**body, "no_call_registry_checked": True})
    assert ok.status_code == 201 and ok.json()["campaign"]["status"] == "running"


@pytest.mark.parametrize("purpose", ["cobranza", "turnos", "aviso", None])
def test_other_purposes_start_without_confirmation(api, voice, purpose):  # noqa: F811
    user, agent, _ = voice
    load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, purpose=purpose, tags=["mora"])).json()["campaign"]
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").json()["status"] == "running"


def test_changing_the_purpose_asks_again(api, voice):  # noqa: F811
    user, agent, _ = voice
    load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, purpose="cobranza", tags=["mora"])).json()["campaign"]
    url = f"{V1}/campaigns/{camp['id']}"
    assert user.post(f"{url}/start").status_code == 200
    # En curso no se cambia la finalidad (se saltearia la confirmacion).
    assert user.patch(url, json={"purpose": "comercial"}).status_code == 409
    assert user.post(f"{url}/pause").status_code == 200
    assert user.patch(url, json={"purpose": "comercial"}).json()["purpose"] == "comercial"
    assert user.post(f"{url}/resume").status_code == 422
    assert user.post(f"{url}/resume", json={"no_call_registry_checked": True}).json()["status"] == "running"
    assert user.post(f"{url}/pause").status_code == 200
    assert user.patch(url, json={"purpose": "aviso"}).json()["registry_confirmed"] is False
    assert user.patch(url, json={"purpose": "nada"}).status_code == 422


def test_whatsapp_commercial_campaign_also_asks(api, account):  # noqa: F811
    user, acc, _ = account
    camp = user.post(f"{V1}/campaigns", json={
        "channel": "whatsapp", "account_id": acc["id"], "template_name": "demo", "name": "Promo",
        "purpose": "comercial", "param_names": ["nombre"],
        "contacts": [{"phone": "351 555-1001", "name": "Ana"}]}).json()["campaign"]
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 422
    r = user.post(f"{V1}/campaigns/{camp['id']}/start", json={"no_call_registry_checked": True})
    assert r.status_code == 200 and r.json()["status"] == "running"


# ---------- baja por voz (seccion 4) ----------

class StubDefinitions:
    def __init__(self, workflow):
        self.workflow = workflow

    def get(self, agent_id, version, session=None):
        return self.workflow


def flagged_workflow(no_contact=True):
    """El resultado "no_llamar" se elige por el id guardado en la conversacion; su `when` no se cumple solo."""
    wf = load_reference("sales_discovery").model_copy(deep=True)
    wf.completion.outcomes.insert(0, Outcome(id="no_llamar", label="No llamar", when={"baja": True}, message="Listo",
                                             no_contact=no_contact))
    return wf


def test_outcome_flag_is_part_of_the_definition():
    assert Outcome(id="x", label="X", message="m").no_contact is False
    wf = load_reference("sales_discovery").model_dump()
    wf["completion"]["outcomes"][-1:] = [{"id": "baja", "label": "Baja", "when": {}, "message": "ok", "no_contact": True}]
    from app.conversation.models import Workflow
    assert Workflow.model_validate(wf).completion.outcomes[-1].no_contact is True


async def test_no_contact_outcome_adds_a_voice_optout(api, voice):  # noqa: F811
    user, agent, c = voice
    camp = make_voice(user, agent, n=2, concurrency=2, rate_per_minute=600)
    await dialer_for(api).tick()
    first, second = members(api, camp["id"])
    for m in (first, second):
        close(api, m.id, "answered")
    # La primera conversacion termino en el resultado "no contactar"; la segunda, en uno comun.
    with api.sessions() as s:
        for m, outcome in ((first, "no_llamar"), (second, flagged_workflow().completion.outcomes[-1].id)):
            conv = s.get(ConversationRow, m.conversation_id)
            conv.status, conv.progress = "completed", {"outcome": outcome}
        s.commit()
    defs = StubDefinitions(flagged_workflow())
    with api.sessions() as s:
        assert campaign_calls.apply_outcome_optout(s, first.conversation_id, defs) is True
        assert campaign_calls.apply_outcome_optout(s, second.conversation_id, defs) is False
        assert campaign_calls.apply_outcome_optout(s, "no-existe", defs) is False
        s.commit()
        optouts = list(s.scalars(select(ContactOptout)))
        assert [(o.client_id, o.phone, o.channel, o.source) for o in optouts] == [
            (c["id"], "+5493515551001", "voice", "outcome")]
        # Idempotente.
        assert campaign_calls.apply_outcome_optout(s, first.conversation_id, defs) is True
        s.commit()
        assert len(list(s.scalars(select(ContactOptout)))) == 1
    # No llamar es de voz: WhatsApp sigue habilitado. Y otra campaña de voz ya no lo marca.
    assert user.get(f"{V1}/contacts/optouts").json()[0]["channel"] == "voice"
    other = user.post(f"{V1}/campaigns", json=voice_body(agent, name="Otra", tags=["mora"], window_start=0, window_end=24,
                                                         concurrency=5, rate_per_minute=600)).json()
    assert other["added"] == 1 and other["skipped"][0]["reason"] == "pidió la baja"


async def test_outcome_without_the_flag_or_unfinished_does_nothing(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, n=1, concurrency=1, rate_per_minute=600)
    await dialer_for(api).tick()
    (m,) = members(api, camp["id"])
    defs = StubDefinitions(flagged_workflow(no_contact=False))
    with api.sessions() as s:
        conv = s.get(ConversationRow, m.conversation_id)
        conv.status, conv.progress = "completed", {"outcome": "no_llamar"}
        s.commit()
        assert campaign_calls.apply_outcome_optout(s, m.conversation_id, defs) is False
        conv.status = "active"
        assert campaign_calls.apply_outcome_optout(s, m.conversation_id, StubDefinitions(flagged_workflow())) is False


# ---------- seguimiento por WhatsApp (seccion 6) ----------

@pytest.fixture
def both(api, admin, account):  # noqa: F811
    """Un cliente con numero de WhatsApp conectado, la plantilla `demo` aprobada y un plan con
    campañas de WhatsApp y de voz, con seguimiento."""
    user, acc, c = account
    r = admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"campaign_channels": ["whatsapp", "voice"],
                                                          "campaign_followup": True})
    assert r.status_code == 200, r.text
    return user, acc, c


def followup_cfg(acc, **extra):
    return {"account_id": acc["id"], "template_name": "demo", "params": ["nombre"], **extra}


def voice_with_followup(user, acc, *, n=3, followup=True, **extra) -> dict:
    load_contacts(user, [{"phone": f"351 555-100{i}", "name": f"Ana{i}", "tags": ["mora"]} for i in range(1, n + 1)])
    body = {"channel": "voice", "name": "Mora", "agent_id": acc["agent_id"], "tags": ["mora"], "window_start": 0,
            "window_end": 24, "concurrency": 5, "rate_per_minute": 600, "max_attempts": 1,
            **({"followup": followup_cfg(acc)} if followup else {}), **extra}
    r = user.post(f"{V1}/campaigns", json=body)
    assert r.status_code == 201, r.text
    return r.json()["campaign"]


def wa_sender(api, graph=None, hour=12, clock=None) -> tuple[CampaignSender, CampaignGraph]:
    graph = graph or CampaignGraph()
    return CampaignSender(api.sessions, graph_factory=lambda token: graph, hour=lambda: hour,
                          clock=clock or Clock()), graph


def test_followup_is_validated_and_stored(api, meta, both):  # noqa: F811
    user, acc, _ = both
    camp = voice_with_followup(user, acc)
    f = camp["followup_config"]
    assert (f["after"], f["account_id"], f["template_name"], f["params"], f["template_params"]) == (
        ["no_answer", "busy", "voicemail"], acc["id"], "demo", ["nombre"], 1)
    assert f["template_body"].startswith("Hola {{1}}") and f["agent_id"] is None
    assert camp["followup"] == {"pending": 0, "sent": 0, "replied": 0, "failed": 0, "skipped": 0}

    url = f"{V1}/campaigns"
    base = {"channel": "voice", "name": "V", "agent_id": acc["agent_id"]}
    # Variables de la plantilla sin mapear, o de mas.
    r = user.post(url, json={**base, "followup": followup_cfg(acc, params=[])})
    assert r.status_code == 422 and "variables" in r.json()["detail"]
    r = user.post(url, json={**base, "followup": followup_cfg(acc, params=["a", "b"])})
    assert r.status_code == 422
    # Plantilla inexistente / no aprobada.
    assert user.post(url, json={**base, "followup": followup_cfg(acc, template_name="otra")}).status_code == 422
    meta.templates[-1]["status"] = "PAUSED"
    assert user.post(url, json={**base, "followup": followup_cfg(acc)}).status_code == 422
    meta.templates[-1]["status"] = "APPROVED"
    # Resultados inexistentes, y WhatsApp no tiene seguimiento.
    assert user.post(url, json={**base, "followup": followup_cfg(acc, after=["answered"])}).status_code == 422
    wa_body = {"channel": "whatsapp", "account_id": acc["id"], "template_name": "demo", "name": "W",
               "followup": followup_cfg(acc)}
    assert user.post(url, json=wa_body).status_code == 422


def test_followup_needs_the_plan_and_an_own_account(api, admin, meta, both):  # noqa: F811
    user, acc, c = both
    base = {"channel": "voice", "name": "V", "agent_id": acc["agent_id"], "followup": followup_cfg(acc)}
    # La cuenta de otro cliente no sirve.
    from .test_api import client_user, make_client
    other = client_user(api, admin, make_client(admin, slug="otro", campaign_channels=["voice"],
                                                campaign_followup=True), email="otro@x.com")
    assert other.post(f"{V1}/campaigns", json=base).status_code in (403, 404, 422)
    # Un plan sin seguimiento lo rechaza, al crear y al iniciar.
    camp = voice_with_followup(user, acc)
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"campaign_followup": False})
    r = user.post(f"{V1}/campaigns", json=base)
    assert r.status_code == 429 and r.json()["code"] == "campaign_followup_not_in_plan"
    r = user.post(f"{V1}/campaigns/{camp['id']}/start")
    assert r.status_code == 429 and r.json()["code"] == "campaign_followup_not_in_plan"
    assert user.patch(f"{V1}/campaigns/{camp['id']}", json={"followup": None}).json()["followup_config"] is None
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200       # sin seguimiento, anda


def test_start_rechecks_the_followup_template(api, meta, both):  # noqa: F811
    user, acc, _ = both
    camp = voice_with_followup(user, acc)
    meta.templates[-1]["status"] = "PAUSED"
    r = user.post(f"{V1}/campaigns/{camp['id']}/start")
    assert r.status_code == 422 and "PAUSED" in r.json()["detail"]


def test_followup_can_be_changed_while_a_draft(api, meta, both):  # noqa: F811
    user, acc, _ = both
    camp = voice_with_followup(user, acc, followup=False)
    assert camp["followup_config"] is None and camp["followup"] is None
    url = f"{V1}/campaigns/{camp['id']}"
    r = user.patch(url, json={"followup": followup_cfg(acc, after=["busy", "failed"], agent_id=acc["agent_id"])})
    assert r.status_code == 200, r.text
    assert r.json()["followup_config"]["after"] == ["busy", "failed"]
    assert r.json()["followup_config"]["agent_id"] == acc["agent_id"]
    assert user.patch(url, json={"followup": followup_cfg(acc, agent_id="no-existe")}).status_code == 404


async def test_last_attempt_queues_the_followup(api, both):
    user, acc, _ = both
    camp = voice_with_followup(user, acc, n=4, max_attempts=2)
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    now = Now()
    dialer = dialer_for(api, now=now)
    assert await dialer.tick() == 4
    a, b, c, d = members(api, camp["id"])
    close(api, a.id, "no_answer", now=now.t)         # reintento: todavia no
    close(api, b.id, "answered", now=now.t)
    close(api, c.id, "rejected", now=now.t)          # no esta en `after`
    close(api, d.id, "voicemail", now=now.t)
    got = {m.id: (m.status, m.result, m.followup_status) for m in members(api, camp["id"])}
    assert got == {a.id: ("retry", "no_answer", None), b.id: ("done", "answered", None),
                   c.id: ("done", "rejected", None), d.id: ("retry", "voicemail", None)}
    now.advance(minutes=61)
    assert await dialer.tick() == 2
    close(api, a.id, "no_answer", now=now.t)         # segundo intento: termino sin atender
    close(api, d.id, "busy", now=now.t)
    got = {m.id: (m.status, m.followup_status) for m in members(api, camp["id"])}
    assert got == {a.id: ("done", "pending"), b.id: ("done", None), c.id: ("done", None), d.id: ("done", "pending")}
    assert campaign(api, camp["id"]).status == "done"       # el seguimiento no demora el cierre
    assert user.get(f"{V1}/campaigns/{camp['id']}").json()["followup"]["pending"] == 2


async def test_sender_sends_the_followup_with_the_campaign_pace(api, both):
    user, acc, _ = both
    camp = voice_with_followup(user, acc, n=3)
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    await dialer_for(api, clock=Clock()).tick()
    for m in members(api, camp["id"]):
        close(api, m.id, "no_answer")
    # Ritmo de la campaña: un seguimiento cada 5 s.
    with api.sessions() as s:
        s.get(Campaign, camp["id"]).rate_per_minute = 12
        s.commit()
    clock = Clock()
    sender, graph = wa_sender(api, clock=clock)
    assert await sender.tick() == 1 and await sender.tick() == 0       # sin tiempo transcurrido no hay credito
    clock.t += 10
    assert await sender.tick() == 2
    assert sorted(t[2:] for t in graph.templates) == [("demo", "es_AR", ["Ana1"]), ("demo", "es_AR", ["Ana2"]),
                                                       ("demo", "es_AR", ["Ana3"])]
    assert graph.templates[0][0] == acc["phone_number_id"]
    for m in members(api, camp["id"]):
        assert (m.followup_status, m.followup_wamid.startswith("wamid.tpl"), m.followup_sent_at is not None) == (
            "sent", True, True)
        assert m.result == "no_answer" and m.sent_at is None       # lo de la llamada no se pisa
    out = user.get(f"{V1}/campaigns/{camp['id']}").json()
    assert out["followup"] == {"pending": 0, "sent": 3, "replied": 0, "failed": 0, "skipped": 0}
    clock.t += 10
    assert await sender.tick() == 0


async def test_followup_skips_fixed_lines_optouts_archived_and_missing_variables(api, both):
    user, acc, c = both
    camp = voice_with_followup(user, acc, n=2)
    contacts = user.get(f"{V1}/contacts").json()["items"]
    # Un tercero sin nombre (no completa {{1}}), uno de baja de WhatsApp y un fijo (solo por la base: la
    # agenda toma todo como celular).
    nameless = user.post(f"{V1}/contacts", json=[{"phone": "351 555-2001"}]).json()["contacts"][0]
    opted = user.post(f"{V1}/contacts", json=[{"phone": "351 555-2002", "name": "Eva"}]).json()["contacts"][0]
    archived = user.post(f"{V1}/contacts", json=[{"phone": "351 555-2003", "name": "Ivo"}]).json()["contacts"][0]
    assert user.post(f"{V1}/contacts/optouts", json={"phone": "351 555-2002", "channel": "whatsapp"}).status_code == 201
    with api.sessions() as s:
        fixed = Contact(client_id=c["id"], phone="+543514445566", name="Fijo")
        s.add(fixed)
        s.flush()
        for contact_id in (nameless["id"], opted["id"], archived["id"], fixed.id):
            s.add(CampaignContact(campaign_id=camp["id"], contact_id=contact_id,
                                  vars={"nombre": "x"} if contact_id != nameless["id"] else {}))
        s.flush()
        for r in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])):
            r.status, r.result, r.followup_status = "done", "no_answer", "pending"
        s.get(Campaign, camp["id"]).status = "done"
        s.commit()
    assert user.post(f"{V1}/contacts/{archived['id']}/archive").status_code == 200
    sender, graph = wa_sender(api)
    assert await sender.tick() == 2          # solo Ana1 y Ana2
    reasons = {}
    with api.sessions() as s:
        for r in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])):
            reasons[r.contact.phone] = (r.followup_status, (r.followup_error or {}).get("reason"))
    assert reasons == {
        "+5493515551001": ("sent", None), "+5493515551002": ("sent", None),
        "+5493515552001": ("skipped", "missing_params"), "+5493515552002": ("skipped", "optout"),
        "+5493515552003": ("skipped", "contact_archived"), "+543514445566": ("skipped", "no_whatsapp")}
    assert len(contacts) == 2 and len(graph.templates) == 2
    out = user.get(f"{V1}/campaigns/{camp['id']}").json()
    assert out["followup"] == {"pending": 0, "sent": 2, "replied": 0, "failed": 0, "skipped": 4}


async def test_followup_waits_while_the_plan_does_not_include_it(api, admin, both):  # noqa: F811
    user, acc, c = both
    camp = voice_with_followup(user, acc, n=2)
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    await dialer_for(api, clock=Clock()).tick()
    for m in members(api, camp["id"]):
        close(api, m.id, "no_answer")
    assert admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"campaign_followup": False}).status_code == 200
    clock = Clock()
    sender, graph = wa_sender(api, clock=clock)
    assert await sender.tick() == 0 and graph.templates == []
    assert [m.followup_status for m in members(api, camp["id"])] == ["pending", "pending"]      # esperan, no se pierden
    assert admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"campaign_followup": True}).status_code == 200
    clock.t += 700      # pasa la espera del sender
    assert await sender.tick() == 2
    assert [m.followup_status for m in members(api, camp["id"])] == ["sent", "sent"]


async def test_followup_respects_window_and_campaign_state(api, both):
    user, acc, _ = both
    camp = voice_with_followup(user, acc, n=3, window_start=9, window_end=20)
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    with api.sessions() as s:
        for r in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])):
            r.status, r.result, r.followup_status = "done", "busy", "pending"
        s.commit()
    sender, graph = wa_sender(api, hour=21)
    assert await sender.tick() == 0 and graph.templates == []            # fuera de horario
    sender, graph = wa_sender(api, hour=12)
    assert user.post(f"{V1}/campaigns/{camp['id']}/pause").status_code == 200
    assert await sender.tick() == 0                                       # pausada: espera
    assert user.post(f"{V1}/campaigns/{camp['id']}/resume").status_code == 409     # nada pendiente de llamar
    # Cancelada: los seguimientos sin mandar quedan salteados.
    assert user.post(f"{V1}/campaigns/{camp['id']}/cancel").json()["followup"]["skipped"] == 3
    assert await sender.tick() == 0 and graph.templates == []


async def test_followup_meta_errors_do_not_pause_the_voice_campaign(api, both):
    from app.whatsapp.graph import GraphError
    user, acc, _ = both
    camp = voice_with_followup(user, acc, n=3)
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    with api.sessions() as s:
        for r in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])):
            r.status, r.result, r.followup_status = "done", "busy", "pending"
        s.get(Campaign, camp["id"]).status = "done"
        s.commit()
    clock = Clock()
    sender, graph = wa_sender(api, clock=clock)
    # Cuenta o plantilla con problemas: frena un rato, vuelve a pendiente y no toca la campaña.
    graph.fail_template = GraphError("Plantilla pausada", code=132015)
    assert await sender.tick() == 0
    assert campaign(api, camp["id"]).status == "done"
    assert [m.followup_status for m in members(api, camp["id"])] == ["pending"] * 3
    graph.fail_template = None
    clock.t += 60
    assert await sender.tick() == 0      # sigue en espera
    clock.t += 600
    assert await sender.tick() == 3
    assert campaign(api, camp["id"]).status == "done"
    # Un numero invalido falla ese contacto solo.
    with api.sessions() as s:
        first = s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])
                          .order_by(CampaignContact.created_at, CampaignContact.id)).first()
        first.followup_status = "pending"
        s.commit()
    graph.fail_template = GraphError("Invalid parameter", code=100)
    clock.t += 600
    assert await sender.tick() == 0
    got = members(api, camp["id"])[0]
    assert (got.followup_status, got.followup_error["code"]) == ("failed", 100)
    assert [m.followup_status for m in members(api, camp["id"])[1:]] == ["sent", "sent"]


def test_recover_marks_inflight_followups_as_failed(api, both):
    user, acc, _ = both
    camp = voice_with_followup(user, acc, n=1)
    with api.sessions() as s:
        s.scalar(select(CampaignContact)).followup_status = "in_progress"
        s.commit()
    sender, _ = wa_sender(api)
    assert sender.recover() == 1
    assert members(api, camp["id"])[0].followup_status == "failed"


def seed_followup(w, *, agent_id=None, phone=WA_ID, sent_at=None) -> tuple[str, str]:
    """Una campaña de voz con seguimiento ya enviado a `phone` por la cuenta de `w`."""
    sent_at = sent_at or datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    with w.sessions() as s:
        c = Campaign(client_id=w.client_id, channel="voice", agent_id=w.agent_id, name="V", status="done",
                     concurrency=1, followup={
                         "after": ["no_answer"], "account_id": w.account_id, "template_name": "demo",
                         "template_language": "es_AR", "template_body": "Hola {{1}}, no pudimos hablar.",
                         "template_params": 1, "params": ["nombre"], "agent_id": agent_id})
        s.add(c)
        s.flush()
        contact = Contact(client_id=w.client_id, phone="+" + phone, name="Ana")
        r = CampaignContact(campaign_id=c.id, contact=contact, vars={"nombre": "Ana"}, status="done",
                            result="no_answer", attempts=1, followup_status="sent", followup_wamid="wamid.fu1",
                            followup_sent_at=sent_at)
        s.add(r)
        s.commit()
        return c.id, r.id


async def test_reply_to_the_followup_opens_a_whatsapp_conversation(sessions):
    w = make_wa(sessions, llm=FakeLLM(), graph=CampaignGraph())
    from .test_whatsapp_service import reply
    w.llm.turns.append(reply("Hola Ana, ¿en qué te ayudo?"))
    cid, rid = seed_followup(w)
    with sessions() as s:       # el ultimo intento de voz tiene su propia conversacion
        r = s.get(CampaignContact, rid)
        r.conversation_id = None
    await send(w, text_payload("hola, me llamaron", "wamid.in1"))
    (conv,) = conversations(sessions)
    assert [(m["role"], m["text"]) for m in conv.messages][:2] == [
        ("assistant", "Hola Ana, no pudimos hablar."), ("user", "hola, me llamaron")]
    assert conv.channel == "whatsapp" and conv.agent_id == w.agent_id
    with sessions() as s:
        r = s.get(CampaignContact, rid)
        assert r.replied_at is not None and r.followup_conversation_id == conv.id
        assert r.conversation_id is None                  # lo de la llamada no se pisa
        assert wa.is_campaign_conversation(s, conv.id)
        counts = common.followup_counts(s, [cid])[cid]
    assert counts == {"pending": 0, "sent": 1, "replied": 1, "failed": 0, "skipped": 0}


async def test_followup_reply_uses_the_followup_agent(sessions):
    from app.agents.templates import reference_data
    from app.models import Client
    from app.services import agents as agent_service
    w = make_wa(sessions, llm=FakeLLM(), graph=CampaignGraph())
    with sessions() as s:
        other = agent_service.create_agent(s, s.get(Client, w.client_id), name="Cobros", slug="cobros", description="",
                                           definition=reference_data("demo_booking_classic"), template_id=None,
                                           user_id=None)
        s.commit()
        other_id = other.id
    seed_followup(w, agent_id=other_id)
    from .test_whatsapp_service import reply
    w.llm.turns.append(reply("Hola"))
    await send(w, text_payload("hola", "wamid.in1"))
    (conv,) = conversations(sessions)
    assert conv.agent_id == other_id


async def test_followup_reply_window_and_optout(sessions):
    w = make_wa(sessions, llm=FakeLLM(), graph=CampaignGraph())
    old = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(days=settings.wa_campaign_reply_days + 1)
    seed_followup(w, sent_at=old)
    with sessions() as s:
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        assert wa.reply_target(s, w.account_id, WA_ID, now) is None         # vencido
        assert wa.got_campaign(s, w.account_id, WA_ID)                      # pero la baja por texto vale
    # "No me interesa" despues de recibir el seguimiento: baja de WhatsApp.
    await send(w, text_payload("No me interesa", "wamid.in1"))
    with sessions() as s:
        assert s.get(ContactOptout, (w.client_id, "+" + WA_ID, "whatsapp")).source == "keyword"
    assert conversations(sessions) == []


async def test_latest_template_wins_between_a_whatsapp_campaign_and_a_followup(sessions):
    from .test_whatsapp_campaigns import make_campaign, sender_for
    from .test_whatsapp_service import reply
    w = make_wa(sessions, llm=FakeLLM(), graph=CampaignGraph())
    seed_followup(w, sent_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(hours=2))
    make_campaign(w, WA_ID)
    await sender_for(w).tick()           # la plantilla de la campaña de WhatsApp es mas nueva
    w.llm.turns.append(reply("Hola"))
    await send(w, text_payload("hola", "wamid.in1"))
    (conv,) = conversations(sessions)
    assert conv.messages[0]["text"].startswith("Hola Ana0, probá gratis")


# ---------- webhook (seccion 8) ----------

SECRET = "s3cr3t-de-prueba-largo"


@pytest.fixture
def private_hooks(monkeypatch):
    """Los tests entregan a un host de mentira: se permite http y cualquier host."""
    monkeypatch.setattr(settings, "campaign_callback_allow_private", True)


def hook_body(agent, **extra):
    return voice_body(agent, **{"tags": ["mora"], "window_start": 0, "window_end": 24, "concurrency": 5,
                                "rate_per_minute": 600, "callback_url": "http://hooks.example.test/campanas",
                                "callback_secret": SECRET, **extra})


def test_webhook_url_is_validated(api, voice, monkeypatch):  # noqa: F811
    user, agent, _ = voice
    monkeypatch.setattr(settings, "campaign_callback_allow_private", False)
    url = f"{V1}/campaigns"
    for bad in ("http://example.com/x", "ftp://example.com", "https://", "https://user:pw@example.com/x",
                "https://127.0.0.1/x", "https://localhost/hook", "https://[::1]/hook", "https://10.0.0.5/x",
                "https://169.254.169.254/latest", "https://192.168.1.10:8011/x", "no es una url"):
        r = user.post(url, json=voice_body(agent, callback_url=bad))
        assert r.status_code == 422, bad
    assert user.get(url).json() == []
    # Un host que resuelve a una IP privada tampoco.
    monkeypatch.setattr(campaign_callbacks.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.1.2.3", 443))])
    assert user.post(url, json=voice_body(agent, callback_url="https://hooks.example.com/x")).status_code == 422
    monkeypatch.setattr(campaign_callbacks.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    ok = user.post(url, json=voice_body(agent, callback_url="https://hooks.example.com/x"))
    assert ok.status_code == 201


def test_webhook_dns_check_does_not_block_the_event_loop(api, voice, monkeypatch):  # noqa: F811
    """Crear o editar con callback_url resuelve el DNS en un thread, no en el event loop de la API."""
    import asyncio
    user, agent, _ = voice
    monkeypatch.setattr(settings, "campaign_callback_allow_private", False)
    where = []

    def getaddrinfo(*a, **k):
        try:
            asyncio.get_running_loop()
            where.append("loop")
        except RuntimeError:
            where.append("thread")
        return [(2, 1, 6, "", ("93.184.216.34", 443))]

    monkeypatch.setattr(campaign_callbacks.socket, "getaddrinfo", getaddrinfo)
    r = user.post(f"{V1}/campaigns", json=voice_body(agent, callback_url="https://hooks.example.com/x"))
    assert r.status_code == 201, r.text
    cid = r.json()["campaign"]["id"]
    assert user.patch(f"{V1}/campaigns/{cid}", json={"callback_url": "https://otro.example.com/y"}).status_code == 200
    assert where and set(where) == {"thread"}
    # Una URL que no pasa la validacion se rechaza igual, sin llegar a guardarse.
    monkeypatch.setattr(campaign_callbacks.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.1.2.3", 443))])
    assert user.patch(f"{V1}/campaigns/{cid}", json={"callback_url": "https://interno.example.com/z"}).status_code == 422
    assert user.get(f"{V1}/campaigns/{cid}").json()["callback_url"] == "https://otro.example.com/y"


def test_webhook_secret_is_generated_once_and_stored_encrypted(api, voice, private_hooks, monkeypatch):  # noqa: F811
    from cryptography.fernet import Fernet
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    user, agent, _ = voice
    r = user.post(f"{V1}/campaigns", json=voice_body(agent, callback_url="http://hooks.example.test/c"))
    assert r.status_code == 201, r.text
    camp = r.json()["campaign"]
    secret = camp["callback_secret"]
    assert secret and len(secret) >= 32 and camp["callback_url"] == "http://hooks.example.test/c"
    again = user.get(f"{V1}/campaigns/{camp['id']}").json()
    assert again["callback_secret"] is None and again["callback_url"] == "http://hooks.example.test/c"
    with api.sessions() as s:
        stored = s.get(Campaign, camp["id"]).callback_secret
        assert stored.startswith("fernet:") and secret not in stored
        assert campaign_callbacks.secret_of(s.get(Campaign, camp["id"])) == secret
    # Rotar el secreto, cambiar la URL y apagar el webhook.
    url = f"{V1}/campaigns/{camp['id']}"
    rotated = user.patch(url, json={"callback_secret": SECRET}).json()
    assert rotated["callback_secret"] is None
    with api.sessions() as s:
        assert campaign_callbacks.secret_of(s.get(Campaign, camp["id"])) == SECRET
    assert user.patch(url, json={"callback_secret": "corto"}).status_code == 422
    moved = user.patch(url, json={"callback_url": "http://otro.example.test/c"}).json()
    assert moved["callback_url"] == "http://otro.example.test/c" and moved["callback_secret"] is None
    off = user.patch(url, json={"callback_url": None}).json()
    assert off["callback_url"] is None
    with api.sessions() as s:
        assert s.get(Campaign, camp["id"]).callback_secret is None
    assert user.patch(url, json={"callback_secret": SECRET}).status_code == 422       # sin URL no hay secreto


def test_webhook_secret_needs_the_token_key(api, voice, private_hooks, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "wa_token_key", "")
    user, agent, _ = voice
    r = user.post(f"{V1}/campaigns", json=voice_body(agent, callback_url="http://hooks.example.test/c"))
    assert r.status_code == 503 and "WA_TOKEN_KEY" in r.json()["detail"]


def hook_env(api, voice_env, monkeypatch, n=2, **extra):
    """Una campaña de voz en curso con webhook, y su usuario."""
    from cryptography.fernet import Fernet
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    user, agent, _ = voice_env
    load_contacts(user, [{"phone": f"351 555-100{i}", "name": f"Ana{i}", "tags": ["mora"]} for i in range(1, n + 1)])
    camp = user.post(f"{V1}/campaigns", json=hook_body(agent, **extra)).json()["campaign"]
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    return user, camp


def events(api, campaign_id=None) -> list[CampaignCallback]:
    with api.sessions() as s:
        q = select(CampaignCallback).order_by(CampaignCallback.created_at, CampaignCallback.id)
        if campaign_id:
            q = q.where(CampaignCallback.campaign_id == campaign_id)
        rows = list(s.scalars(q))
        for r in rows:
            s.expunge(r)
        return rows


async def test_events_are_queued_per_contact_and_when_the_campaign_ends(api, voice, private_hooks, monkeypatch):  # noqa: F811
    _, camp = hook_env(api, voice, monkeypatch, n=2, max_attempts=1)
    assert events(api) == []
    await dialer_for(api).tick()
    a, b = members(api, camp["id"])
    close(api, a.id, "answered")
    assert [(e.event, e.campaign_contact_id) for e in events(api)] == [("contact.finished", a.id)]
    close(api, b.id, "busy")        # sin mas intentos: termino; con ello, la campaña
    assert [(e.event, e.campaign_contact_id) for e in events(api)] == [
        ("contact.finished", a.id), ("contact.finished", b.id), ("campaign.finished", None)]
    assert {e.status for e in events(api)} == {"pending"}


async def test_a_retry_is_not_a_finished_contact(api, voice, private_hooks, monkeypatch):  # noqa: F811
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=2)
    await dialer_for(api).tick()
    (a,) = members(api, camp["id"])
    close(api, a.id, "no_answer")
    assert states(api, camp["id"]) == [("retry", "no_answer", 1)] and events(api) == []


async def test_cancel_and_archived_contacts_notify(api, voice, private_hooks, monkeypatch):  # noqa: F811
    user, camp = hook_env(api, voice, monkeypatch, n=3)
    with api.sessions() as s:       # uno de los pendientes se archiva antes de marcarlo
        contact = s.scalar(select(Contact).where(Contact.phone == "+5493515551001"))
    assert user.post(f"{V1}/contacts/{contact.id}/archive").status_code == 200
    archived = next(m for m in members(api, camp["id"]) if m.status == "skipped")
    assert [(e.event, e.campaign_contact_id) for e in events(api)] == [("contact.finished", archived.id)]
    assert user.post(f"{V1}/campaigns/{camp['id']}/pause").status_code == 200
    # Cancelar saltea los pendientes en bloque (sin un evento por cada uno) y avisa que termino.
    assert user.post(f"{V1}/campaigns/{camp['id']}/cancel").json()["status"] == "cancelled"
    assert [e.event for e in events(api)] == ["contact.finished", "campaign.finished"]


async def test_dialer_skips_notify_the_contact(api, voice, private_hooks, monkeypatch):  # noqa: F811
    user, camp = hook_env(api, voice, monkeypatch, n=2)
    assert user.post(f"{V1}/contacts/optouts", json={"phone": "351 555-1001", "channel": "voice"}).status_code == 201
    await dialer_for(api).tick()
    skipped = [m for m in members(api, camp["id"]) if m.status == "skipped"]
    assert len(skipped) == 1
    assert [(e.event, e.campaign_contact_id) for e in events(api)] == [("contact.finished", skipped[0].id)]


async def test_no_webhook_no_events(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, n=1, concurrency=1, max_attempts=1)
    await dialer_for(api).tick()
    (a,) = members(api, camp["id"])
    close(api, a.id, "answered")
    assert events(api) == []


async def test_whatsapp_sender_queues_events_and_followup_ones(api, both, private_hooks, monkeypatch):
    user, acc, _ = both
    camp = voice_with_followup(user, acc, n=2, callback_url="http://hooks.example.test/c", callback_secret=SECRET)
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    await dialer_for(api).tick()
    a, b = members(api, camp["id"])
    close(api, a.id, "no_answer")
    close(api, b.id, "answered")
    sender, _ = wa_sender(api)
    assert await sender.tick() == 1
    assert [(e.event, e.campaign_contact_id) for e in events(api)] == [
        ("contact.finished", a.id), ("contact.finished", b.id), ("campaign.finished", None),
        ("contact.followup", a.id)]
    # Una campaña de WhatsApp: un evento por envio y otro al terminar.
    wa_camp = user.post(f"{V1}/campaigns", json={
        "channel": "whatsapp", "account_id": acc["id"], "template_name": "demo", "name": "W", "param_names": ["nombre"],
        "contacts": [{"phone": "351 555-3001", "name": "Eva"}], "callback_url": "http://hooks.example.test/w",
        "callback_secret": SECRET, "window_start": 0, "window_end": 24}).json()["campaign"]
    assert user.post(f"{V1}/campaigns/{wa_camp['id']}/start").status_code == 200
    clock = Clock()
    sender, _ = wa_sender(api, clock=clock)
    await sender.tick()
    clock.t += 60
    await sender.tick()
    assert [e.event for e in events(api, wa_camp["id"])] == ["contact.finished", "campaign.finished"]


# --- entrega ---

def make_dispatcher(api, handler, now=None, **kw) -> CallbackDispatcher:
    transport = httpx.MockTransport(handler)
    return CallbackDispatcher(api.sessions, definitions=lambda: api.engine.definitions, now=now or Now(),
                              client_factory=lambda: httpx.AsyncClient(transport=transport), **kw)


class Receiver:
    def __init__(self, status=200):
        self.status = status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status)


def signed_ok(request: httpx.Request, secret=SECRET) -> dict:
    expected = "sha256=" + hmac.new(secret.encode(), request.content, hashlib.sha256).hexdigest()
    assert request.headers["x-atentina-signature"] == expected
    return json.loads(request.content)


async def test_delivery_is_signed_and_has_the_report_fields(api, voice, private_hooks, monkeypatch):  # noqa: F811
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1)
    await dialer_for(api).tick()
    (a,) = members(api, camp["id"])
    close(api, a.id, "busy")
    rx = Receiver()
    now = Now()
    d = make_dispatcher(api, rx, now=now)
    now.advance(seconds=1)
    assert await d.tick() == 2
    by_event = {r.headers["x-atentina-event"]: r for r in rx.requests}
    assert set(by_event) == {"contact.finished", "campaign.finished"}
    req = by_event["contact.finished"]
    assert str(req.url) == "http://hooks.example.test/campanas" and req.headers["content-type"] == "application/json"
    body = signed_ok(req)
    assert body["event"] == "contact.finished" and body["delivery_id"] == req.headers["x-atentina-delivery"]
    assert body["campaign"]["id"] == camp["id"] and body["campaign"]["channel"] == "voice"
    contact = body["contact"]
    assert (contact["telefono"], contact["nombre"], contact["estado"], contact["resultado"], contact["intentos"]) == (
        "+5493515551001", "Ana1", "done", "busy", 1)
    assert contact["campaign_contact_id"] == a.id and contact["conversation_id"] == a.conversation_id
    assert set(contact) >= {"external_id", "telefono", "nombre", "vars", "estado", "resultado", "intentos",
                            "ultimo_intento", "duracion_segundos", "outcome", "objetivo", "campos", "seguimiento",
                            "error", "conversation_id", "link"}
    done = signed_ok(by_event["campaign.finished"])
    assert done["campaign"]["status"] == "done" and done["campaign"]["total"] == 1
    assert done["campaign"]["progress"]["done"] == 1 and done["campaign"]["stats"]["results"]["busy"] == 1
    assert "contact" not in done
    assert {e.status for e in events(api)} == {"sent"} and events(api)[0].delivered_at is not None
    assert await make_dispatcher(api, rx, now=now).tick() == 0       # nada mas que entregar


async def test_delivery_retries_with_backoff_and_gives_up(api, voice, private_hooks, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "campaign_callback_max_attempts", 3)
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1)
    await dialer_for(api).tick()
    (a,) = members(api, camp["id"])
    close(api, a.id, "answered")
    rx = Receiver(status=500)
    now = Now()
    d = make_dispatcher(api, rx, now=now)
    now.advance(seconds=1)
    assert await d.tick() == 0 and len(rx.requests) == 2
    first = events(api)[0]
    assert (first.status, first.attempts, first.last_status_code, first.last_error) == (
        "pending", 1, 500, "El webhook respondió 500")
    assert first.next_attempt_at == now.t + backoff(1)
    # Antes del plazo no se vuelve a probar.
    now.advance(seconds=10)
    await d.tick()
    assert len(rx.requests) == 2
    # El mismo delivery_id en los reintentos.
    now.advance(seconds=30)
    await d.tick()
    assert len(rx.requests) == 4
    assert rx.requests[0].headers["x-atentina-delivery"] == rx.requests[2].headers["x-atentina-delivery"]
    now.advance(hours=1)
    await d.tick()
    rows = events(api)
    assert {r.status for r in rows} == {"failed"} and {r.attempts for r in rows} == {3}
    now.advance(days=1)
    await d.tick()
    assert len(rx.requests) == 6         # ya no insiste
    # Un webhook que vuelve: lo nuevo se entrega (los fallidos quedan registrados).
    rx.status = 200
    close(api, members(api, camp["id"])[0].id, "answered")      # ya cerrado: no hay evento nuevo
    assert await d.tick() == 0


async def test_delivery_recovers_after_a_failure(api, voice, private_hooks, monkeypatch):  # noqa: F811
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1)
    await dialer_for(api).tick()
    close(api, members(api, camp["id"])[0].id, "answered")
    rx = Receiver(status=503)
    now = Now()
    d = make_dispatcher(api, rx, now=now)
    now.advance(seconds=1)
    await d.tick()
    rx.status = 204
    now.advance(minutes=3)
    assert await d.tick() == 2
    assert {(r.status, r.attempts, r.last_error) for r in events(api)} == {("sent", 2, None)}


async def test_delivery_network_error_and_claim_lease(api, voice, private_hooks, monkeypatch):  # noqa: F811
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1)
    await dialer_for(api).tick()
    close(api, members(api, camp["id"])[0].id, "answered")

    def boom(request):
        raise httpx.ConnectError("connection refused")

    now = Now()
    d = make_dispatcher(api, boom, now=now)
    now.advance(seconds=1)
    assert await d.tick() == 0
    assert {r.last_error[:13] for r in events(api)} == {"ConnectError:"} and {r.attempts for r in events(api)} == {1}
    # Un evento reclamado queda en el futuro: otra copia de la app no lo toma al mismo tiempo.
    assert len(await __import__("asyncio").to_thread(d._claim)) == 0
    now.advance(minutes=1)
    claimed = await __import__("asyncio").to_thread(d._claim)
    assert len(claimed) == 2
    assert await __import__("asyncio").to_thread(d._claim) == []


async def test_delivery_pins_the_resolved_ip(api, voice, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "campaign_callback_allow_private", False)
    monkeypatch.setattr(campaign_callbacks.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1,
                          callback_url="https://hooks.example.com:8443/campanas?x=1")
    await dialer_for(api).tick()
    close(api, members(api, camp["id"])[0].id, "answered")
    rx = Receiver()
    now = Now()
    d = make_dispatcher(api, rx, now=now, resolve=lambda host, port: "93.184.216.34")
    now.advance(seconds=1)
    assert await d.tick() == 2
    req = rx.requests[0]
    assert (req.url.host, req.url.port, req.url.path, req.url.query) == ("93.184.216.34", 8443, "/campanas", b"x=1")
    assert req.headers["host"] == "hooks.example.com:8443"
    assert req.extensions["sni_hostname"] == "hooks.example.com"
    signed_ok(req)


async def test_delivery_refuses_a_host_that_turned_private(api, voice, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "campaign_callback_allow_private", False)
    monkeypatch.setattr(campaign_callbacks.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1, callback_url="https://hooks.example.com/c")
    await dialer_for(api).tick()
    close(api, members(api, camp["id"])[0].id, "answered")

    def rebound(host, port):
        raise ValueError("apunta a una red privada o interna")

    rx = Receiver()
    now = Now()
    d = make_dispatcher(api, rx, now=now, resolve=rebound)
    now.advance(seconds=1)
    assert await d.tick() == 0 and rx.requests == []
    assert all("red privada" in r.last_error for r in events(api))


async def test_delivery_stops_when_the_webhook_is_removed(api, voice, private_hooks, monkeypatch):  # noqa: F811
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1)
    await dialer_for(api).tick()
    close(api, members(api, camp["id"])[0].id, "answered")
    with api.sessions() as s:       # lo apagaron mientras habia eventos sin entregar
        s.get(Campaign, camp["id"]).callback_url = None
        s.commit()
    rx = Receiver()
    now = Now()
    d = make_dispatcher(api, rx, now=now)
    now.advance(seconds=1)
    assert await d.tick() == 0 and rx.requests == []
    assert {(r.status, r.last_error) for r in events(api)} == {("failed", "La campaña ya no tiene webhook")}


async def test_delivery_without_the_token_key_fails_cleanly(api, voice, private_hooks, monkeypatch):  # noqa: F811
    _, camp = hook_env(api, voice, monkeypatch, n=1, max_attempts=1)
    await dialer_for(api).tick()
    close(api, members(api, camp["id"])[0].id, "answered")
    from cryptography.fernet import Fernet
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())      # otra clave: no descifra
    rx = Receiver()
    now = Now()
    d = make_dispatcher(api, rx, now=now)
    now.advance(seconds=1)
    assert await d.tick() == 0 and rx.requests == []
    assert all(r.status == "failed" and "descifrar" in r.last_error for r in events(api))


def test_backoff_grows_and_caps():
    assert [backoff(n).total_seconds() for n in (1, 2, 3, 4, 5, 6, 9)] == [30, 120, 600, 3600, 21600, 21600, 21600]
