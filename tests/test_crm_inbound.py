# ruff: noqa: F811, DTZ001 (los fixtures vienen de test_crm; fechas UTC sin zona como en la base)
"""CRM: respuestas recibidas por Resend (crm/services/inbound.py): asociar, clasificar, aplicar y avisar."""
import datetime
import os

# Antes de cargar crm.config, como en test_crm (el orden de la coleccion no importa)
os.environ["CRM_API_KEY"] = "user-key"
os.environ["CRM_AGENT_API_KEY"] = "agent-key"
os.environ["CRM_LOOPS"] = "false"
os.environ["CRM_RESEND_API_KEY"] = "re_test"

import pytest

from crm.config import settings
from crm.models import InboundEmail
from crm.services import inbound as INB
from crm.services import resend
from tests.test_crm import (  # noqa: F401
    USER,
    _send_queued,
    api,
    campaign_and_template,
    db,
    lead,
    sent,
)


def llm(intencion="interesado", **kw):
    return {"intencion": intencion, "resumen": kw.pop("resumen", "Quiere saber más."), "proxima_accion": "",
            "fecha": "", "contacto_nombre": "", "contacto_cargo": "", "contacto_email": "", "confianza": 1.0} | kw


@pytest.fixture
def env(api, db, sent, monkeypatch):
    """Un lead con el primer mail enviado (Message-ID <orig@ses>) y un seguimiento en borrador."""
    monkeypatch.setattr(settings, "notify_to", "admin@example.com")
    monkeypatch.setattr(INB, "classify", lambda subject, text: llm())
    a = lead(api)
    c, t, fu = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    _send_queued(db, 1e10, datetime.datetime(2026, 10, 1, 12), "<orig@ses>")
    f = api.post("/api/followups/drafts", json={"lead_ids": [a["id"]], "template_id": fu["id"]},
                 headers=USER).json()["created"][0]
    sent.clear()
    return {"lead": a, "draft": f}


def received(rid="r1", frm="Pablo Pérez <pablo@empresa.com.ar>", text="Me interesa, contame más.", **headers):
    return {"id": rid, "from": frm, "to": ["crm@in.atentina.net"], "subject": "Re: Llamadas de voz",
            "text": text, "html": None, "created_at": "2026-10-22T15:00:00.000Z", "headers": headers}


def ingest(db, data):
    with db() as s:
        ib = INB.ingest(s, data)
        s.commit()
        return ib


def get_lead(api, env):
    return api.get(f"/api/leads/{env['lead']['id']}", headers=USER).json()


def test_respuesta_por_el_hilo_se_clasifica_y_avisa(api, db, env, sent, monkeypatch):
    monkeypatch.setattr(INB, "classify", lambda subject, text: llm(
        "agendar", proxima_accion="Confirmar la charla", fecha="2026-10-27T11:00:00"))
    # Viene de otra direccion (gmail): la asocia el hilo
    ib = ingest(db, received(frm="Marta <marta.x@gmail.com>", text="¿El martes 27 a las 11?\n\nEl mié, 1 oct "
                             "2026 a las 9:00, Laureano escribió:\n> Hola", **{"In-Reply-To": "<orig@ses>"}))
    assert ib.status == "assigned" and ib.reason == "hilo"
    a = get_lead(api, env)
    assert a["stage"] == "respondio" and a["next_action"] == "Confirmar la charla"
    assert a["next_action_at"] == "2026-10-27"
    msgs = api.get(f"/api/messages?lead_id={a['id']}", headers=USER).json()["items"]
    inbound = next(m for m in msgs if m["direction"] == "in")
    assert inbound["analysis"]["intencion"] == "agendar" and inbound["analysis"]["matched_by"] == "hilo"
    assert next(m for m in msgs if m["id"] == env["draft"]["id"])["status"] == "canceled"
    assert len(sent) == 1 and sent[0]["to"] == "admin@example.com"
    assert sent[0]["subject"] == "Respondió Empresa SA: Quiere hablar"
    assert "¿El martes 27 a las 11?" in sent[0]["text"] and "> Hola" not in sent[0]["text"]
    # El mismo recibido no se procesa dos veces
    with db() as s:
        assert s.query(InboundEmail).count() == 1


def test_baja_no_contactar_y_blocklist(api, db, env, monkeypatch):
    monkeypatch.setattr(INB, "classify", lambda subject, text: llm("baja"))
    ingest(db, received(text="No nos escriban más."))
    a = get_lead(api, env)
    assert a["stage"] == "no_interesa" and a["do_not_contact"] is True
    r = api.get("/api/leads/check?email=pablo@empresa.com.ar", headers=USER).json()
    assert r["blocked"] == "opt_out"


def test_derivado_suma_el_contacto(api, db, env, monkeypatch):
    monkeypatch.setattr(INB, "classify", lambda subject, text: llm(
        "derivado", contacto_nombre="Juan Pérez", contacto_cargo="Gerente comercial",
        contacto_email="juan.perez@empresa.com.ar", proxima_accion="Escribirle a Juan"))
    ingest(db, received(frm="info@empresa.com.ar", text="Escribile a Juan Pérez."))
    a = get_lead(api, env)
    assert "juan.perez@empresa.com.ar" in {c["value"] for c in a["contacts"]}
    assert {"name": "Juan Pérez", "title": "Gerente comercial"}.items() <= next(
        p for p in a["people"] if p["name"] == "Juan Pérez").items()


def test_autorespuesta_no_cambia_nada_ni_avisa(api, db, env, sent):
    ib = ingest(db, received(text="Fuera de la oficina.", **{"Auto-Submitted": "auto-replied"}))
    assert ib.status == "assigned"
    a = get_lead(api, env)
    assert a["stage"] == "contactado"
    msgs = api.get(f"/api/messages?lead_id={a['id']}&status=draft", headers=USER).json()["items"]
    assert [m["id"] for m in msgs] == [env["draft"]["id"]]
    assert sent == []


def test_sin_llm_o_dudoso_queda_respondio_para_revisar(api, db, env, monkeypatch):
    def boom(subject, text):
        raise RuntimeError("vllm caido")
    monkeypatch.setattr(INB, "classify", boom)
    ingest(db, received())
    a = get_lead(api, env)
    assert a["stage"] == "respondio"
    m = next(x for x in api.get(f"/api/messages?lead_id={a['id']}", headers=USER).json()["items"]
             if x["direction"] == "in")
    assert m["analysis"]["status"] == "error"
    monkeypatch.setattr(INB, "classify", lambda subject, text: llm("no_interesa", confianza=0.4))
    ingest(db, received(rid="r2"))
    assert get_lead(api, env)["stage"] == "respondio"      # con poca confianza no lo cierra


def test_copias_nuestras_se_ignoran_y_sin_lead_va_a_la_bandeja(api, db, env, sent):
    assert ingest(db, received(rid="r1", frm="Laureano <laureano@atentina.net>")).status == "ignored"
    assert ingest(db, received(rid="r2", frm="MAILER-DAEMON@mx.example.com")).status == "ignored"
    ib = ingest(db, received(rid="r3", frm="alguien@gmail.com", text="Hola, ¿qué es esto?"))
    assert ib.status == "unassigned"
    assert sent[-1]["subject"] == "Respuesta sin asignar de alguien@gmail.com"
    box = api.get("/api/today", headers=USER).json()["inbox"]
    assert [x["id"] for x in box] == [ib.id]
    r = api.post(f"/api/inbox/{ib.id}/assign", json={"lead_id": env["lead"]["id"]}, headers=USER)
    assert r.status_code == 200 and r.json()["analysis"]["matched_by"] == "a mano"
    assert get_lead(api, env)["stage"] == "respondio"
    assert api.post(f"/api/inbox/{ib.id}/assign", json={"lead_id": env["lead"]["id"]},
                    headers=USER).status_code == 409
    assert api.get("/api/today", headers=USER).json()["inbox"] == []


def test_poll_lee_solo_lo_nuevo(db, env, monkeypatch):
    pages = {None: {"data": [{"id": "r3", "created_at": "3"}, {"id": "r2", "created_at": "2"}], "has_more": True},
             "r2": {"data": [{"id": "r1", "created_at": "1"}], "has_more": False}}
    monkeypatch.setattr(resend, "list_received", lambda after=None: pages[after])
    monkeypatch.setattr(resend, "get_received", lambda rid: received(rid=rid))
    monkeypatch.setattr(INB.time, "sleep", lambda _: None)
    with db() as s:
        assert INB.poll(s) == 3
        assert INB.poll(s) == 0


def test_strip_quoted():
    t = ("Dale, hablemos.\nSaludos\n\nEl jue, 22 oct 2026 a las 10:00, Laureano Arcanio (<\n"
         "laureano@atentina.net>) escribió:\n> Hola:\n> ¿Les sirve?")
    assert INB.strip_quoted(t) == "Dale, hablemos.\nSaludos"
    assert INB.strip_quoted("Ok\n\n-----Mensaje original-----\nDe: x") == "Ok"
    assert INB.strip_quoted("Gracias\n> citado") == "Gracias"
