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
from crm.services import ga as GA
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
    assert api.get("/api/messages?status=canceled", headers=USER).json()["total"] == 1
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


def test_descartar_borradores_en_lote(api, db, sent):
    a = lead(api)
    c, t, fu = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    _send_queued(db, 1e10, datetime.datetime(2026, 10, 1, 12), "<orig@ses>")  # noqa: DTZ001
    f = api.post("/api/followups/drafts", json={"lead_ids": [a["id"]], "template_id": fu["id"]},
                 headers=USER).json()["created"][0]
    # Uno ya enviado: no se descarta ninguno
    assert api.post("/api/messages/cancel", json={"ids": [f["id"], d["id"]]}, headers=USER).status_code == 409
    r = api.post("/api/messages/cancel", json={"ids": [f["id"]]}, headers=USER)
    assert [m["status"] for m in r.json()] == ["canceled"]
    # Vuelve a tocarle el seguimiento, para armarlo con otra plantilla
    assert api.get("/api/leads?pending=follow_up", headers=USER).json()["total"] == 1


def test_ga_sitio_solo_argentina(api, monkeypatch):
    calls = []

    class R:
        status_code = 200

        def __init__(self, reports):
            self.reports = reports

        def json(self):
            return {"reports": [{"rows": [{"dimensionValues": [{"value": v} for v in d],
                                           "metricValues": [{"value": str(v)} for v in m]} for d, m in rows]}
                                for rows in self.reports]}

    def post(url, json, headers, timeout):
        calls.append(json["requests"])
        if len(json["requests"]) == 5:
            return R([[(["actual"], [10, 8, 12, 30, 0.5, 90.5]), (["anterior"], [5, 5, 6, 10, 0.4, 60])],
                      [(["20261022"], [4, 5, 9])], [(["Email"], [7, 6])], [(["/"], [20, 9])], [(["Cordoba"], [3])]])
        return R([[(["email / (not set)"], [7, 6])], [(["desktop"], [7])], [([], [40])]])

    monkeypatch.setattr(settings, "ga_property_id", "1")
    monkeypatch.setattr(settings, "ga_credentials", "x.json")
    monkeypatch.setattr(GA, "_token", lambda: "t")
    monkeypatch.setattr(GA.httpx, "post", post)
    monkeypatch.setattr(GA, "local_today", lambda: datetime.date(2026, 10, 23))
    GA._site_cache.clear()
    r = api.get("/api/ga/site?days=7", headers=USER).json()
    assert r["totals"]["users"] == 10 and r["previous"]["views"] == 10 and r["all_users"] == 40
    assert r["start"] == "2026-10-17" and len(r["by_day"]) == 7
    assert r["by_day"][5] == {"day": "2026-10-22", "users": 4, "sessions": 5, "views": 9}
    assert r["channels"] == [{"channel": "Email", "sessions": 7, "users": 6}]
    # Todo filtrado por pais salvo el total de todos los paises, y con el periodo anterior de igual largo
    flt = [q.get("dimensionFilter") for b in calls for q in b]
    assert flt.count({"filter": {"fieldName": "country", "stringFilter": {"value": "Argentina"}}}) == 7
    assert flt[-1] is None
    assert calls[0][0]["dateRanges"][1] == {"startDate": "2026-10-10", "endDate": "2026-10-16", "name": "anterior"}
    # Cache: el segundo pedido no consulta GA; refresh si
    api.get("/api/ga/site?days=7", headers=USER)
    assert len(calls) == 2
    api.get("/api/ga/site?days=7&refresh=true", headers=USER)
    assert len(calls) == 4


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
    assert set(today) == {"follow_ups_due", "drafts", "tasks", "replies", "next_actions", "queue", "reply_rates", "agenda",
                         "inbox"}
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


def _send_queued(db, now, sent_at, message_id):
    with db() as s:
        m = sending.tick(s, now=now)
        assert m.status == "sent"
        m.sent_at, m.message_id = sent_at, message_id
        s.commit()
        return m.id


def test_secuencia_de_dos_seguimientos(api, db, sent, monkeypatch):
    a = lead(api)
    c, t, fu = campaign_and_template(api)
    fu2 = api.post("/api/templates", json={"name": "ultimo", "kind": "follow_up", "subject": "x",
                                           "body": "Hola:\n\nÚltimo mensaje, no insisto más."}, headers=USER).json()
    r = api.patch(f"/api/campaigns/{c['id']}", json={"sequence": [
        {"days": 4, "template_id": fu["id"]}, {"days": 5, "template_id": fu2["id"]}]}, headers=USER)
    assert r.status_code == 200 and len(r.json()["sequence"]) == 2
    r = api.patch(f"/api/campaigns/{c['id']}", json={"sequence": [{"days": 4, "template_id": t["id"]}]},
                  headers=USER)
    assert r.status_code == 422                       # plantilla de primer mail
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    assert d["step"] == 0
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    _send_queued(db, 1e10, datetime.datetime(2026, 10, 1, 12), "<orig@ses>")

    def today(d):
        monkeypatch.setattr(M, "local_today", lambda: d)

    today(datetime.date(2026, 10, 6))
    with db() as s:
        assert M.auto_followups(s) == 0
    today(datetime.date(2026, 10, 7))
    with db() as s:
        assert M.auto_followups(s) == 1 and M.auto_followups(s) == 0   # el segundo ya esta pendiente
    f1 = api.get("/api/messages?status=draft", headers=USER).json()["items"][0]
    assert f1["step"] == 1 and f1["created_by"] == "sistema" and f1["in_reply_to"] == "<orig@ses>"
    api.post("/api/messages/approve", json={"ids": [f1["id"]]}, headers=USER)
    _send_queued(db, 2e10, datetime.datetime(2026, 10, 8, 12), "<fu1@ses>")
    assert api.get(f"/api/leads/{a['id']}", headers=USER).json()["stage"] == "seguimiento"

    today(datetime.date(2026, 10, 14))                 # 4 dias habiles: el paso 2 pide 5
    with db() as s:
        assert M.followups_due(s) == []
    today(datetime.date(2026, 10, 15))
    due = api.get("/api/today", headers=USER).json()["follow_ups_due"]
    assert [(x["step"], x["template_id"], x["business_days"]) for x in due] == [(2, fu2["id"], 5)]
    # La tabla de leads sabe a quien le toca y que borradores tiene (para elegir y aprobar desde ahi)
    r = api.get("/api/leads?pending=follow_up", headers=USER).json()
    assert [(x["id"], x["follow_up_step"], x["draft_ids"]) for x in r["items"]] == [(a["id"], 2, [])]
    r = api.post("/api/followups/drafts", json={"lead_ids": [a["id"]]}, headers=AGENT).json()
    f2 = r["created"][0]
    assert api.get("/api/leads?pending=follow_up", headers=USER).json()["total"] == 0
    r = api.get("/api/leads?pending=draft", headers=USER).json()["items"]
    assert [(x["id"], x["draft_ids"], x["follow_up_step"]) for x in r] == [(a["id"], [f2["id"]], None)]
    st = api.get("/api/stats", headers=USER).json()
    assert st["by_campaign"] == [{"slug": c["slug"], "reached": 1, "replied": 0, "clicked": 0}]
    assert len(st["sent_by_day"]) == 30
    assert f2["step"] == 2 and f2["subject"] == "Re: Llamadas de voz para Empresa SA"
    assert f2["in_reply_to"] == "<fu1@ses>" and "no insisto" in f2["text"]
    api.post("/api/messages/approve", json={"ids": [f2["id"]]}, headers=USER)
    _send_queued(db, 3e10, datetime.datetime(2026, 10, 15, 12), "<fu2@ses>")
    today(datetime.date(2026, 11, 30))
    with db() as s:
        assert M.followups_due(s) == []                  # termino la secuencia


def test_seguimiento_sin_plantilla_en_la_secuencia(api, db, sent, monkeypatch):
    a = lead(api)
    c, t, fu = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    _send_queued(db, 1e10, datetime.datetime(2026, 10, 1, 12), "<orig@ses>")
    monkeypatch.setattr(M, "local_today", lambda: datetime.date(2026, 10, 7))
    with db() as s:
        assert M.auto_followups(s) == 0                  # sin secuencia no se arma solo
    r = api.post("/api/followups/drafts", json={"lead_ids": [a["id"]]}, headers=USER).json()
    assert r["created"] == [] and "plantilla" in r["skipped"][0]["reason"]
    r = api.post("/api/followups/drafts", json={"lead_ids": [a["id"]], "template_id": fu["id"]},
                 headers=USER).json()
    assert r["created"][0]["step"] == 1


def test_boton_de_eventos(api, monkeypatch):
    calls = []
    monkeypatch.setattr(sending, "check_events_now", lambda: calls.append(1))
    assert api.post("/api/events/check", headers=AGENT).status_code == 403
    assert api.post("/api/events/check", headers=USER).json()["started"] is True and calls == [1]
    q = api.get("/api/queue", headers=USER).json()
    assert q["events_running"] is False and q["events_last"] == {}


def test_etapa_seguimiento_cuenta_como_un_seguimiento(api, db, sent, monkeypatch):
    a = lead(api)
    c, t, _ = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [a["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    _send_queued(db, 1e10, datetime.datetime(2026, 10, 1, 12), "<orig@ses>")
    api.patch(f"/api/leads/{a['id']}", json={"stage": "seguimiento"}, headers=USER)   # mandado a mano
    monkeypatch.setattr(M, "local_today", lambda: datetime.date(2026, 10, 20))
    with db() as s:
        assert M.followups_due(s) == []


def test_respuesta_por_telefono_solo_con_nombre(api):
    a = lead(api)
    r = api.post(f"/api/leads/{a['id']}/inbound", json={"channel": "phone", "from_addr": "Marta",
                                                      "text": "Llamó, quiere una demo"}, headers=USER)
    assert r.status_code == 201
    m = r.json()
    assert m["channel"] == "phone" and m["from_addr"] == "Marta" and m["to_addr"] == "" and m["subject"] == ""
    r = api.post(f"/api/leads/{a['id']}/inbound", json={"channel": "agent"}, headers=USER).json()
    assert r["channel"] == "agent" and r["from_addr"] is None
    assert api.get(f"/api/leads/{a['id']}", headers=USER).json()["stage"] == "respondio"
    assert api.post(f"/api/leads/{a['id']}/inbound", json={"channel": "fax"}, headers=USER).status_code == 422


def test_editar_respuesta_cargada(api):
    a = lead(api)
    m = api.post(f"/api/leads/{a['id']}/inbound", json={"from_addr": "pablo@empresa.com.ar", "subject": "Re: x",
                                                      "text": "Sí"}, headers=USER).json()
    r = api.patch(f"/api/messages/{m['id']}", json={"channel": "phone", "from_addr": "Pablo", "subject": "",
                                                    "text": "Llamó: quiere demo",
                                                    "at": "2026-10-22T11:05:00-03:00"}, headers=AGENT)
    assert r.status_code == 200
    r = r.json()
    assert (r["channel"], r["from_addr"], r["to_addr"], r["subject"], r["text"]) == \
        ("phone", "Pablo", "", "", "Llamó: quiere demo")
    assert r["sent_at"].startswith("2026-10-22T14:05")
    r = api.patch(f"/api/messages/{m['id']}", json={"from_addr": ""}, headers=USER).json()
    assert r["from_addr"] is None and r["text"] == "Llamó: quiere demo"
    # Lo que salio (o esta en la cola) no se edita
    b = lead(api, name="Otra SA", website="https://otra.com.ar",
             contacts=[{"kind": "email", "value": "ana@otra.com.ar", "is_primary": True, "source_url": SRC}])
    c, t, _ = campaign_and_template(api)
    d = api.post(f"/api/campaigns/{c['id']}/drafts", json={"lead_ids": [b["id"]], "template_id": t["id"]},
                 headers=USER).json()["created"][0]
    api.post("/api/messages/approve", json={"ids": [d["id"]]}, headers=USER)
    assert api.patch(f"/api/messages/{d['id']}", json={"text": "otro"}, headers=USER).status_code == 409


def test_reply_rate_por_nivel(api, db):
    c, _, _ = campaign_and_template(api)
    ids = [lead(api, name=f"Empresa {i}", website=f"https://e{i}.com.ar/", contacts=[])["id"] for i in range(4)]
    d = lambda day: datetime.datetime(2026, 10, day, 12)
    with db() as s:
        def out(lid, kind, step, day, status="sent"):
            s.add(models.Message(lead_id=lid, campaign_id=c["id"], kind=kind, step=step, direction="out",
                                 to_addr="x@y.com", subject="s", status=status, sent_at=d(day)))
        for lid in ids[:2]:
            out(lid, "first", 0, 1)
        out(ids[2], "first", 0, 1, status="bounced")                  # rebotado: no cuenta como alcanzado
        s.add(models.Message(lead_id=ids[0], direction="in", kind="other", to_addr="nos", subject="r",
                             status="received", sent_at=d(2)))       # responde al primer mail
        out(ids[1], "follow_up", 1, 8)
        out(ids[3], "first", 0, 1)
        out(ids[3], "follow_up", 1, 8)
        out(ids[3], "follow_up", 2, 15)
        # Respondio por telefono: solo el cambio de etapa, entre el seguimiento 1 y el 2 (el 2 salio igual)
        s.get(models.Lead, ids[3]).stage = "charla_agendada"
        s.add(models.Activity(lead_id=ids[3], kind="stage_change", at=d(10), data={"to": "respondio"}))
        s.add(models.Message(lead_id=ids[1], direction="in", kind="other", to_addr="nos", subject="r",
                             status="received", sent_at=d(9)))       # responde al seguimiento 1
        s.commit()
        rates = M.reply_rates(s)
    total = {r["step"]: (r["reached"], r["replied"], r["rate"]) for r in rates if r["campaign_slug"] is None}
    assert total == {0: (3, 1, 0.3333), 1: (2, 2, 1.0), 2: (1, 0, 0.0)}
    assert {r["step"] for r in rates if r["campaign_slug"] == "canales9"} == {0, 1, 2}
    assert api.get("/api/today", headers=USER).json()["reply_rates"][0] == {
        "campaign_slug": None, "step": 0, "reached": 3, "replied": 1, "rate": 0.3333}
