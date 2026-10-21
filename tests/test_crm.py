"""CRM de ventas (crm/, docs/CRM_PLAN.md): API, plantillas, cola de envio, eventos, GA y seguimientos."""
import datetime
import os

os.environ["CRM_API_KEY"] = "user-key"
os.environ["CRM_AGENT_API_KEY"] = "agent-key"
os.environ["CRM_LOOPS"] = "false"
os.environ["CRM_RESEND_API_KEY"] = "re_test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from crm import models
from crm.config import settings
from crm.db import Base, get_session
from crm.main import create_app
from crm.services import messages as M
from crm.services import resend, sending

USER = {"Authorization": "Bearer user-key"}
AGENT = {"Authorization": "Bearer agent-key"}
SRC = "https://empresa.com.ar/contacto"


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'crm.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def api(db):
    app = create_app()

    def session():
        with db() as s:
            yield s

    app.dependency_overrides[get_session] = session
    return TestClient(app)


@pytest.fixture
def sent(monkeypatch):
    """Resend falso: guarda lo que se manda."""
    out = []

    def fake_send(**kw):
        out.append(kw)
        return f"rs-{len(out)}"

    monkeypatch.setattr(resend, "send", fake_send)
    monkeypatch.setattr(sending, "in_hours", lambda now=None: True)
    return out


def lead(api, **kw):
    body = {"name": "Empresa SA", "website": "https://www.empresa.com.ar/", "industry": "software",
            "contacts": [{"kind": "email", "value": "Pablo@Empresa.com.ar", "label": "persona",
                          "person": "Pablo Pérez", "is_primary": True, "source_url": SRC},
                         {"kind": "email", "value": "info@empresa.com.ar", "label": "atencion",
                          "source_url": SRC}]} | kw
    r = api.post("/api/leads", json=body, headers=USER)
    assert r.status_code in (200, 201), r.text
    return r.json()["lead"]


def campaign_and_template(api):
    c = api.post("/api/campaigns", json={"slug": "canales9", "name": "Canales 9"}, headers=USER).json()
    t = api.post("/api/templates", json={
        "name": "primer", "subject": "Llamadas de voz para {{empresa}}",
        "body": "{{saludo}}\n\n¿Les sirve?\n\n{{link}}\n\nSaludos,\nLaureano",
        "body_personal": "{{saludo}}\n\n¿Te sirve?\n\n{{link}}\n\nSaludos,\nLaureano"}, headers=USER).json()
    fu = api.post("/api/templates", json={
        "name": "seguimiento", "kind": "follow_up", "subject": "x",
        "body": "Hola:\n\n¿Les parece una llamada de 5 minutos?\n\n{{link}}"}, headers=USER).json()
    return c, t, fu


def test_auth_y_problem_json(api):
    r = api.get("/api/leads")
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")
    r = api.post("/api/leads", json={"website": "x.com"}, headers=USER)
    assert r.status_code == 422 and r.json()["field"] == "name"


def test_upsert_por_dominio_suma_sin_borrar(api):
    a = lead(api)
    assert a["domain"] == "empresa.com.ar" and a["slug"] == "empresa-sa"
    assert a["primary_email"] == "pablo@empresa.com.ar"
    r = api.post("/api/leads", json={"website": "empresa.com.ar", "people": [{"name": "Ana", "title": "CEO"}],
                                     "tags": ["salud"]}, headers=USER)
    assert r.status_code == 200 and r.json()["result"] == "updated"
    b = r.json()["lead"]
    assert b["id"] == a["id"] and len(b["contacts"]) == 2 and {p["name"] for p in b["people"]} == {"Pablo Pérez", "Ana"}
    assert api.get("/api/leads/check?email=otro@empresa.com.ar", headers=AGENT).json()["lead"]["id"] == a["id"]


def test_agente_necesita_fuente_y_no_aprueba(api):
    r = api.post("/api/leads", json={"name": "Otra", "website": "otra.com",
                                     "contacts": [{"kind": "email", "value": "a@otra.com"}]}, headers=AGENT)
    assert r.status_code == 422 and r.json()["field"] == "source_url"
    a = lead(api)
    c, t, _ = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=AGENT).json()["created"][0]
    r = api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=AGENT)
    assert r.status_code == 403


def test_plantilla_tutea_a_una_persona_y_arma_el_link(api):
    a = lead(api)
    c, t, _ = campaign_and_template(api)
    p = api.post(f"/api/templates/{t['id']}/preview", json={"lead_id": a["id"], "campaign_id": c["id"]},
                 headers=USER).json()
    assert p["to"] == "pablo@empresa.com.ar"
    assert p["text"].startswith("Hola, Pablo:\n\n¿Te sirve?")
    assert "utm_campaign=canales9&utm_content=empresa-sa" in p["text"]
    r = api.post("/api/templates", json={"name": "mala", "subject": "x", "body": "{{cargo}}"}, headers=USER)
    assert r.status_code == 422


def test_envio_seguimiento_en_hilo_y_rebote(api, db, sent):
    a = lead(api)
    c, t, fu = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    with db() as s:
        m = sending.tick(s, now=1e10)
        assert m.status == "sent" and m.lead.stage == "contactado"
        assert sending.tick(s, now=1e10) is None          # la ventana todavia no paso
        m.message_id = "<orig@ses>"
        m.sent_at = datetime.datetime(2026, 10, 1, 12)
        s.commit()
    assert sent[0]["to"] == "pablo@empresa.com.ar" and sent[0]["in_reply_to"] is None

    with db() as s:
        due = M.followups_due(s, today=datetime.date(2026, 10, 7))
        assert [x["lead"].id for x in due] == [a["id"]] and due[0]["business_days"] == 4
        assert M.followups_due(s, today=datetime.date(2026, 10, 6)) == []

    r = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": fu["id"],
                                                             "kind": "follow_up"}, headers=USER).json()
    f = r["created"][0]
    assert f["subject"] == "Re: Llamadas de voz para Empresa SA" and f["in_reply_to"] == "<orig@ses>"
    assert "utm_campaign=follow_up_canales_9" in f["text"]
    # Duplicado: se saltea con motivo
    r2 = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": fu["id"],
                                                              "kind": "follow_up"}, headers=USER).json()
    assert r2["created"] == [] and "ya tiene" in r2["skipped"][0]["reason"]

    with db() as s:
        m = s.get(models.Message, d["id"])
        M.mark_event(s, m, "bounced")
        s.commit()
        lead_row = s.get(models.Lead, a["id"])
        assert lead_row.stage == "contactado"          # queda info@: no se descarta
        assert s.query(models.Block).filter_by(value="pablo@empresa.com.ar").one().reason == "bounce"


def test_respuesta_cambia_etapa_y_cancela_la_cola(api, db, sent):
    a = lead(api)
    c, t, _ = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    r = api.post(f"/api/leads/{a['id']}/inbound", json={"from_addr": "pablo@empresa.com.ar", "text": "Sí, llamame"},
                 headers=AGENT)
    assert r.status_code == 201
    assert api.get(f"/api/leads/{a['id']}", headers=USER).json()["stage"] == "respondio"
    assert api.get(f"/api/messages?status=canceled", headers=USER).json()["total"] == 1
    with db() as s:
        assert sending.tick(s, now=1e10) is None and sent == []


def test_blocklist_frena_borradores(api):
    a = lead(api)
    c, t, _ = campaign_and_template(api)
    api.post("/api/blocklist", json={"value": "empresa.com.ar", "reason": "opt_out"}, headers=USER)
    r = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()
    assert r["created"] == [] and "blocklist" in r["skipped"][0]["reason"]


def test_ga_cruza_por_utm(api):
    a = lead(api)
    campaign_and_template(api)
    r = api.post("/api/ga/visits", json=[
        {"date": "2026-10-21", "utm_campaign": "canales9", "utm_content": "empresa-sa", "active_users": 3},
        {"date": "2026-10-21", "utm_campaign": "follow_up_canales_9", "utm_content": "empresa-sa", "active_users": 1},
        {"date": "2026-10-21", "utm_campaign": "(not set)", "utm_content": "(not set)", "active_users": 5}],
        headers=USER).json()
    assert r == {"rows": 3, "matched": 2}
    assert api.get(f"/api/leads/{a['id']}", headers=USER).json()["ga_users"] == 4
    assert api.get("/api/leads?has_clicks=true", headers=USER).json()["total"] == 1
    v = api.get(f"/api/ga/visits?lead_id={a['id']}", headers=USER).json()
    assert sorted(x["follow_up"] for x in v) == [False, True] and all(x["campaign_id"] for x in v)


def test_importar_historial_y_hoy(api):
    a = lead(api)
    c, _, _ = campaign_and_template(api)
    r = api.post("/api/messages/import", json={"lead_id": a["id"], "campaign_id": c["id"], "to_addr": "info@empresa.com.ar",
                                               "subject": "Consulta", "status": "bounced", "resend_id": "r1",
                                               "sent_at": "2026-10-05T10:00:00-03:00"}, headers=USER)
    assert r.status_code == 201 and r.json()["sent_at"].startswith("2026-10-05T13:00")
    assert api.post("/api/messages/import", json={"lead_id": a["id"], "to_addr": "x@y.com", "subject": "s",
                                                  "resend_id": "r1", "sent_at": "2026-10-05T10:00:00Z"},
                    headers=USER).status_code == 409
    assert api.post("/api/messages/import", json={"lead_id": a["id"], "to_addr": "x@y.com", "subject": "s",
                                                  "sent_at": "2026-10-05T10:00:00Z"}, headers=AGENT).status_code == 403
    today = api.get("/api/today", headers=USER).json()
    assert set(today) == {"follow_ups_due", "drafts", "tasks", "replies", "next_actions", "queue"}
    assert settings.send_daily_max == today["queue"]["daily_max"]


def test_horas_con_zona_pasan_a_utc_y_patch_de_borrador(api):
    a = lead(api)
    r = api.post(f"/api/leads/{a['id']}/activities", json={"kind": "call", "text": "x",
                                                         "at": "2026-10-22T11:00:00-03:00"}, headers=USER)
    assert r.json()["at"].startswith("2026-10-22T14:00")
    r = api.post(f"/api/leads/{a['id']}/inbound", json={"from_addr": "pablo@empresa.com.ar",
                                                      "at": "2026-10-22T11:05:00-03:00"}, headers=USER).json()
    assert r["sent_at"].startswith("2026-10-22T14:05") and "<" not in r["to_addr"]
    d = api.post("/api/messages", json={"lead_id": a["id"], "subject": "s", "text": "t"}, headers=USER).json()
    r = api.patch(f"/api/messages/{d['id']}", json={"text": "nuevo"}, headers=USER)
    assert r.status_code == 200 and r.json()["text"] == "nuevo"


def test_hosts_compartidos_y_dominio_repetido(api):
    r = api.post("/api/leads", json={"name": "Solo Facebook", "website": "https://www.facebook.com/algo"},
                 headers=USER).json()["lead"]
    assert r["domain"] is None
    a = lead(api)
    r = api.patch(f"/api/leads/{r['id']}", json={"website": "https://empresa.com.ar"}, headers=USER)
    assert r.status_code == 409 and str(a["id"]) in r.json()["detail"]
    api.patch(f"/api/leads/{a['id']}", json={"stage": "charla_hecha"}, headers=USER)
    assert api.get("/api/stats", headers=USER).json()["replied"] == 1
