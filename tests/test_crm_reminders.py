# ruff: noqa: F811 (los fixtures vienen de test_crm)
"""CRM: recordatorios y reuniones (crm/services/reminders.py) y su evento en Google Calendar (gcal.py)."""
import os

# Antes de cargar crm.config, como en test_crm (el orden de la coleccion no importa)
os.environ["CRM_API_KEY"] = "user-key"
os.environ["CRM_AGENT_API_KEY"] = "agent-key"
os.environ["CRM_LOOPS"] = "false"
os.environ["CRM_RESEND_API_KEY"] = "re_test"

import pytest

from crm.config import settings
from crm.services import gcal as GC
from tests.test_crm import USER, api, db, lead  # noqa: F401


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body, self.text = status, body or {}, ""

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def no_cal(monkeypatch):
    """Sin el calendario del .env real: cada test que lo necesita usa `cal`."""
    monkeypatch.setattr(settings, "gcal_calendar_id", "")


@pytest.fixture
def cal(monkeypatch):
    """Calendar falso: guarda los pedidos y responde lo que se le cargue en `next`."""
    calls, nxt = [], []

    def fake(method, path, body=None):
        calls.append((method, path, body))
        return nxt.pop(0) if nxt else Resp(200, {"id": "ev1"})

    monkeypatch.setattr(settings, "gcal_calendar_id", "cal@group.calendar.google.com")
    monkeypatch.setattr(settings, "ga_credentials", "x.json")
    monkeypatch.setattr(GC, "_call", fake)
    return calls, nxt


def person_id(api, a):
    return api.get(f"/api/leads/{a['id']}", headers=USER).json()["people"][0]["id"]


def test_recordatorio_solo_fecha_va_a_las_10_y_es_la_proxima_accion(api):
    a = lead(api)
    r = api.post(f"/api/leads/{a['id']}/reminders", json={"starts_at": "2026-10-26", "person_id": person_id(api, a)},
                 headers=USER)
    assert r.status_code == 201, r.text
    r = r.json()
    assert r["title"] == "Llamar a Pablo Pérez (Empresa SA)" and r["duration_min"] == 15
    assert r["starts_at"] == "2026-10-26T13:00:00"            # 10:00 en Argentina
    assert r["gcal_state"] == "off"                            # sin calendario: queda en el CRM
    l = api.get(f"/api/leads/{a['id']}", headers=USER).json()
    assert l["next_action"] == r["title"] and l["next_action_at"] == "2026-10-26"
    assert api.post(f"/api/leads/{a['id']}/reminders", json={"starts_at": "el lunes"},
                    headers=USER).status_code == 422
    # Cancelado: se limpia la proxima accion
    api.post(f"/api/reminders/{r['id']}/cancel", headers=USER)
    assert api.get(f"/api/leads/{a['id']}", headers=USER).json()["next_action"] is None
    assert api.post(f"/api/reminders/{r['id']}/cancel", headers=USER).status_code == 409


def test_reunion_agendada_y_hecha_mueve_la_etapa(api):
    a = lead(api)
    m = api.post(f"/api/leads/{a['id']}/reminders", json={"kind": "meeting", "starts_at": "2026-10-27T11:00",
                                                           "location": "https://meet.google.com/abc"},
                 headers=USER).json()
    assert m["title"] == "Reunión: Empresa SA" and m["duration_min"] == 30 and m["starts_at"] == "2026-10-27T14:00:00"
    assert api.get(f"/api/leads/{a['id']}", headers=USER).json()["stage"] == "charla_agendada"
    assert [x["id"] for x in api.get("/api/reminders", headers=USER).json()] == [m["id"]]
    r = api.post(f"/api/reminders/{m['id']}/done", json={"outcome": "Quieren un piloto"}, headers=USER).json()
    assert r["status"] == "done"
    l = api.get(f"/api/leads/{a['id']}", headers=USER).json()
    assert l["stage"] == "charla_hecha" and l["next_action"] is None
    tl = api.get(f"/api/leads/{a['id']}/timeline", headers=USER).json()
    assert {"reminder", "activity"} <= {x["type"] for x in tl}
    assert any("Quieren un piloto" in x["data"].get("text", "") for x in tl if x["type"] == "activity")
    assert api.get("/api/reminders", headers=USER).json() == []


def test_calendar_crea_reprograma_marca_y_borra(api, cal):
    calls, nxt = cal
    a = lead(api)
    r = api.post(f"/api/leads/{a['id']}/reminders", json={"starts_at": "2026-10-26T15:30", "notes": "Pidió que lo llame"},
                 headers=USER).json()
    assert r["gcal_state"] == "ok"
    method, _, body = calls[-1]
    assert method == "POST" and body["summary"] == "Llamar a Empresa SA"
    assert body["start"]["dateTime"] == "2026-10-26T15:30:00-03:00" and body["end"]["dateTime"].startswith("2026-10-26T15:45")
    assert body["reminders"]["overrides"] == [{"method": "popup", "minutes": 0}]
    assert "Pidió que lo llame" in body["description"] and f"/#/leads/{a['id']}" in body["description"]
    api.patch(f"/api/reminders/{r['id']}", json={"starts_at": "2026-10-27T10:00"}, headers=USER)
    assert calls[-1][:2] == ("PUT", "/ev1") and calls[-1][2]["start"]["dateTime"].startswith("2026-10-27T10:00")
    # Borrado a mano en Calendar: se recrea
    nxt += [Resp(404), Resp(200, {"id": "ev2"})]
    api.post(f"/api/reminders/{r['id']}/done", json={}, headers=USER)
    assert [c[0] for c in calls[-2:]] == ["PUT", "POST"] and calls[-1][2]["summary"] == "✓ Llamar a Empresa SA"
    r2 = api.post(f"/api/leads/{a['id']}/reminders", json={"starts_at": "2026-10-28"}, headers=USER).json()
    api.post(f"/api/reminders/{r2['id']}/cancel", headers=USER)
    assert calls[-1][:2] == ("DELETE", "/ev1")


def test_calendar_caido_se_reintenta(api, db, cal):
    _, nxt = cal
    a = lead(api)
    nxt.append(Resp(500))
    r = api.post(f"/api/leads/{a['id']}/reminders", json={"starts_at": "2026-10-26"}, headers=USER).json()
    assert r["gcal_state"] == "error"                          # el recordatorio queda igual
    with db() as s:
        assert GC.sync_pending(s) == 1
    assert api.get("/api/reminders", headers=USER).json()[0]["gcal_state"] == "ok"
