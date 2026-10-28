"""Observabilidad del hardware (docs/OBSERVABILIDAD.md): la API /system contra un Prometheus
falso, /internal/metrics, el colector del host (deploy/monitoring/hostmon.py) y la config generada."""
import datetime
import importlib.util
import json
import urllib.parse
import uuid
from pathlib import Path

import httpx
import pytest

from app.config import settings
from app.db import utcnow
from app.models import CallRow, ConversationRow
from app.services import system_status

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401  (admin: fixture)

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"deploy/monitoring/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hostmon = _load("hostmon")
render = _load("render")

H = {"host": "srv"}
GPU0 = {**H, "gpu": "0", "name": "NVIDIA GeForce RTX 3090", "bus": "04:00.0"}
GPU1 = {**H, "gpu": "1", "name": "NVIDIA GeForce RTX 3090", "bus": "07:00.0"}
FS = {**H, "mountpoint": "/home", "device": "/dev/nvme1n1p2"}

# Lo que devuelve el Prometheus falso, por nombre de consulta de NOW_QUERIES.
NOW = {
    "cpu_util": [(H, 0.25)], "cpu_cores": [(H, 16)], "load1": [(H, 2.5)], "cpu_temp": [(H, 61)],
    "cpu_power": [(H, 45)], "mem_total": [(H, 64e9)], "mem_avail": [(H, 16e9)], "swap_total": [(H, 8e9)],
    "swap_free": [(H, 6e9)], "ntp_sync": [(H, 1)], "collector_age": [(H, 3)], "internet_ok": [(H, 1)],
    "fs_size": [(FS, 1000e9)], "fs_avail": [(FS, 100e9)], "fs_deriv": [(FS, -100e9 / 86400 / 4)],
    "gpu_util": [(GPU1, 0.6), (GPU0, 0.9)], "gpu_mem_total": [(GPU0, 24e9), (GPU1, 24e9)],
    "gpu_mem_used": [(GPU0, 21e9), (GPU1, 15e9)], "gpu_power": [(GPU0, 250), (GPU1, 150)],
    "gpu_power_limit": [(GPU0, 280), (GPU1, 280)],
    "gpu_throttle": [({**GPU0, "reason": "sw_power_cap"}, 1), ({**GPU1, "reason": "hw_thermal"}, 1)],
    "gpu_proc": [({**H, "gpu": "1", "service": "stt-parakeet"}, 1.6e9),
                 ({**H, "gpu": "1", "service": "vllm-tts"}, 13e9)],
    "svc_up": [({**H, "service": "vllm-llm"}, 0), ({**H, "service": "app"}, 1)],
    "svc_healthy": [({**H, "service": "app"}, 1)],
    "probe_ok": [({**H, "probe": "LLM", "kind": "interna", "instance": "http://vllm-llm:8000/health"}, 0)],
    "sip": [({**H, "registration": "anura"}, 1)],
    "inf_waiting": [({**H, "job": "llm"}, 2)], "kv_cache": [({**H, "job": "llm"}, 0.4), ({**H, "job": "tts", "stage": "0"}, 0.1)],
    "kv_config": [({**H, "job": "llm", "kv_cache_size_tokens": "63013"}, 1)],
    "calls_active": [(H, 7)], "anura_busy": [(H, 3)], "anura_total": [(H, 10)],
}
ALERTS = [
    {"labels": {"alertname": "InferenciaConCola", "severity": "warning", "host": "srv"}, "state": "firing",
     "annotations": {"summary": "llm: 2 pedidos esperando"}, "activeAt": "2026-10-28T10:00:00Z"},
    {"labels": {"alertname": "ContenedorCaido", "severity": "critical", "host": "srv"}, "state": "firing",
     "annotations": {"summary": "Servicio vllm-llm sin correr"}, "activeAt": "2026-10-28T10:05:00Z"},
    {"labels": {"alertname": "PruebaDeAlerta", "severity": "warning"}, "state": "firing", "annotations": {}},
]
EXPR_TO_NAME = {expr: name for name, expr in system_status.NOW_QUERIES.items()}


def fake_prometheus(ranges=None, fail=False):
    """Transporte de httpx que responde como la API de Prometheus."""
    def handler(request: httpx.Request) -> httpx.Response:
        if fail:
            raise httpx.ConnectError("caído")
        q = dict(urllib.parse.parse_qsl(request.url.query.decode()))
        if request.url.path == "/api/v1/alerts":
            return httpx.Response(200, json={"status": "success", "data": {"alerts": ALERTS}})
        if request.url.path == "/api/v1/query":
            rows = NOW.get(EXPR_TO_NAME.get(q["query"], ""), [])
            result = [{"metric": lab, "value": [0, str(v)]} for lab, v in rows]
            return httpx.Response(200, json={"status": "success", "data": {"resultType": "vector", "result": result}})
        if request.url.path == "/api/v1/query_range":
            rows = (ranges or {}).get(q["query"], [])
            result = [{"metric": lab, "values": [[t, str(v)] for t, v in pts]} for lab, pts in rows]
            return httpx.Response(200, json={"status": "success", "data": {"resultType": "matrix", "result": result}})
        return httpx.Response(404)
    return httpx.MockTransport(handler)


@pytest.fixture
def prom(monkeypatch):
    state = {"ranges": {}, "fail": False}
    monkeypatch.setattr(system_status, "client",
                        lambda: system_status.Prometheus("http://prom", transport=fake_prometheus(
                            state["ranges"], state["fail"])))
    return state


def test_now_groups_host_gpus_services_and_alerts(api, admin, prom):
    r = admin.get(f"{V1}/system/now")
    assert r.status_code == 200, r.text
    out = r.json()
    [host] = out["hosts"]
    assert host["host"] == "srv"
    assert host["cpu"]["util_ratio"] == 0.25 and host["cpu"]["cores"] == 16
    assert host["memory"]["used_ratio"] == 0.75 and host["memory"]["swap_used_bytes"] == 2e9
    # Las GPUs ordenadas por índice, con su recorte y sus procesos
    assert [g["index"] for g in host["gpus"]] == [0, 1]
    g0, g1 = host["gpus"]
    assert (g0["throttle"], g0["throttle_bad"]) == (["sw_power_cap"], False)
    assert (g1["throttle"], g1["throttle_bad"]) == (["hw_thermal"], True)
    assert [p["service"] for p in g1["processes"]] == ["vllm-tts", "stt-parakeet"]
    assert host["power"] == {"gpus_w": 400, "cpu_w": 45, "estimated_w": 445}
    # Disco: 100 GB libres que bajan 25 GB por día → 4 días
    [disk] = host["disks"]
    assert disk["used_ratio"] == pytest.approx(0.9) and disk["days_to_full"] == 4.0
    assert {s["service"]: s["up"] for s in host["services"]} == {"app": True, "vllm-llm": False}
    assert host["probes"][0]["ok"] is False and host["connectivity"]["sip"] == [{"registration": "anura", "ok": True}]
    sat = host["saturation"]
    assert sat["inference"]["llm"]["waiting"] == 2 and sat["llm_kv_cache_ratio"] == 0.4
    # KV cache por motor: el total del LLM sale de la etiqueta; el TTS no lo publica y el STT no tiene
    llm, tts, stt = (sat["inference"][j] for j in ("llm", "tts", "stt"))
    assert (llm["kv_cache_tokens"], llm["kv_cache_used_tokens"]) == (63013, 25205)
    assert (tts["kv_cache_ratio"], tts["kv_cache_tokens"], tts["kv_cache_used_tokens"]) == (0.1, None, None)
    assert stt["kv_cache_ratio"] is None
    assert (sat["calls_active"], sat["anura_channels_busy"], sat["anura_channels_total"]) == (7, 3, 10)
    # Las críticas primero y sin la alerta de prueba
    assert [a["name"] for a in out["alerts"]] == ["ContenedorCaido", "InferenciaConCola"]


def test_system_is_admin_only(api, admin, prom):
    acme = client_user(api, admin, make_client(admin))
    for path in ("now", "history", "events", "peaks"):
        assert acme.get(f"{V1}/system/{path}").status_code == 403
    assert api.client.get(f"{V1}/system/now").status_code == 401


def test_prometheus_down_or_off_is_503(api, admin, prom, monkeypatch):
    prom["fail"] = True
    r = admin.get(f"{V1}/system/now")
    assert (r.status_code, r.json()["code"]) == (503, "monitoring_down")
    monkeypatch.setattr(system_status, "client", lambda: system_status.Prometheus(""))
    r = admin.get(f"{V1}/system/now")
    assert (r.status_code, r.json()["code"]) == (503, "monitoring_off")


def test_history_series_by_gpu_and_window(api, admin, prom):
    step = system_status._step(system_status.WINDOWS["1h"])
    expr = system_status._history_queries(step)["gpu_power"][0]
    prom["ranges"][expr] = [(GPU0, [(100, 250), (115, 260)]), (GPU1, [(100, 150)])]
    out = admin.get(f"{V1}/system/history", params={"window": "1h"}).json()
    assert out["step_s"] == 15
    assert [(s["label"], s["points"]) for s in out["series"]["gpu_power"]] == [
        ("0", [[100, 250], [115, 260]]), ("1", [[100, 150]])]
    assert out["series"]["cpu_util"] == []
    assert admin.get(f"{V1}/system/history", params={"window": "3d"}).status_code == 422


def test_events_split_on_gaps_and_mark_ongoing(prom, monkeypatch):
    monkeypatch.setattr(system_status.time, "time", lambda: 10_000.0)
    lab = {"alertname": "GpuCaliente", "severity": "critical", "host": "srv", "gpu": "1", "alertstate": "firing"}
    test = {"alertname": "PruebaDeAlerta", "severity": "warning"}
    prom["ranges"]['ALERTS{alertstate="firing"}'] = [
        (lab, [(9000, 1), (9015, 1), (9030, 1), (9600, 1), (9990, 1)]), (test, [(9990, 1)])]
    out = system_status.events(system_status.client(), "1h")
    assert [(e["start"], e["end"]) for e in out] == [(9990, None), (9600, 9615), (9000, 9045)]
    assert out[0]["detail"] == "gpu 1"


def test_peaks_one_row_per_day(prom):
    prom["ranges"][system_status.PEAK_QUERIES["gpu_power_max_w"]] = [(H, [(86400, 520), (172800, 430)])]
    prom["ranges"][system_status.PEAK_QUERIES["calls_active_max"]] = [(H, [(172800, 12)])]
    rows = system_status.peaks(system_status.client(), 2)
    assert [(r["day_end"], r.get("gpu_power_max_w"), r.get("calls_active_max")) for r in rows] == [
        (172800, 430, 12), (86400, 520, None)]


# --- /internal/metrics ---------------------------------------------------------------------------

def test_internal_metrics_needs_token_and_no_tunnel(api, admin, monkeypatch):
    acme = make_client(admin)
    agent = make_agent(admin, acme)
    now = utcnow()
    with api.sessions() as s:
        for mode, status, latency in (("entrante", "en_curso", None), ("saliente", "sonando", None),
                                      ("entrante", "finalizada", {"turns": [{"total": t} for t in (1, 2, 3, 4)]})):
            cid = str(uuid.uuid4())
            s.add(ConversationRow(id=cid, client_id=acme["id"], agent_id=agent["id"], agent_version=1,
                                  channel="voice", status="active", fields={}, messages=[], progress={}))
            s.flush()
            s.add(CallRow(conversation_id=cid, client_id=acme["id"], mode=mode, status=status, latency=latency,
                          created_at=now, ended_at=now - datetime.timedelta(minutes=5) if latency else None))
        s.commit()
    monkeypatch.setattr(settings, "monitoring_token", "")
    assert api.client.get("/internal/metrics", headers={"Authorization": "Bearer x"}).status_code == 404
    monkeypatch.setattr(settings, "monitoring_token", "secreto")
    assert api.client.get("/internal/metrics", headers={"Authorization": "Bearer otro"}).status_code == 404
    assert api.client.get("/internal/metrics", headers={"Authorization": "Bearer secreto",
                                                        "CF-Connecting-IP": "1.2.3.4"}).status_code == 404
    r = api.client.get("/internal/metrics", headers={"Authorization": "Bearer secreto"})
    assert r.status_code == 200
    lines = r.text.splitlines()
    assert 'atentina_calls_active{mode="entrante"} 1' in lines
    assert 'atentina_calls_active{mode="saliente"} 1' in lines
    assert "atentina_anura_channels_busy 2" in lines and "atentina_anura_channels_total 10" in lines
    assert "atentina_turn_latency_p95_seconds 3.850" in lines


# --- Colector del host -----------------------------------------------------------------------------

def test_hostmon_parses_nvidia_smi_and_throttle():
    row = ("0, NVIDIA GeForce RTX 3090, 00000000:04:00.0, 37, 21000, 24576, 250.5, 280.00, 70, 45, 1695, 9501, "
           "3, 3, 4, 16, 0x0000000000000060")
    [g] = hostmon.parse_gpus(row + "\nbasura, sin, campos")
    m = hostmon.Metrics()
    hostmon.gpu_metrics(m, [g])
    text = m.render()
    lab = 'bus="04:00.0",gpu="0",name="NVIDIA GeForce RTX 3090"'
    assert f"atentina_gpu_utilization_ratio{{{lab}}} 0.37" in text
    assert f"atentina_gpu_memory_used_bytes{{{lab}}} {21000 * 1024 * 1024}" in text
    assert f'atentina_gpu_throttle{{{lab},reason="sw_thermal"}} 1' in text   # 0x20
    assert f'atentina_gpu_throttle{{{lab},reason="hw_thermal"}} 1' in text   # 0x40
    assert f'atentina_gpu_throttle{{{lab},reason="sw_power_cap"}} 0' in text
    assert "atentina_gpu_count 2" not in text and "atentina_gpu_count 1" in text
    assert text.count("# TYPE atentina_gpu_throttle gauge") == 1
    assert hostmon.throttle_reasons("[N/A]") == {}


def test_hostmon_keeps_full_precision():
    """Un timestamp con 6 cifras (1.79319e+09) quedaba hasta 500 s corrido y disparaba ColectorDelHostCaido."""
    m = hostmon.Metrics()
    m.add("atentina_hostmon_last_run_timestamp_seconds", 1793190178.521)
    m.add("atentina_container_cpu_seconds_total", 1234567.25, {"service": "app"})
    text = m.render()
    assert "atentina_hostmon_last_run_timestamp_seconds 1793190178.521" in text
    assert 'atentina_container_cpu_seconds_total{service="app"} 1234567.25' in text


def test_hostmon_parses_sip_smart_and_xid():
    regs = (" <Registration/ServerURI....>  <Auth....>  <Status.......>\n====\n\n"
            " anura/sip:larcanio.grancentral.com.ar:55090   anura-auth   Registered        (exp. 27s)\n"
            " meta/sip:wa.meta.vc:5061   meta-auth   Rejected\n")
    assert hostmon.parse_registrations(regs) == {"anura": 1, "meta": 0}
    smart = {"smart_status": {"passed": True}, "temperature": {"current": 41},
             "nvme_smart_health_information_log": {"percentage_used": 7, "media_errors": 0, "available_spare": 100}}
    assert hostmon.parse_smart(smart) == {"ok": True, "wear": 7, "media_errors": 0, "spare": 100, "temp": 41}
    journal = "oct 28 kernel: NVRM: Xid (PCI:0000:07:00): 79, pid=123, GPU has fallen off the bus."
    assert hostmon.parse_xid(journal) == [("0000:07:00", "79")]


def test_hostmon_containers_skip_migrate_and_report_missing(monkeypatch):
    monkeypatch.setattr(hostmon, "cgroup_usage", lambda cid: (12.5, 3e8))
    def c(svc, status, health=None, restarts=0):
        state = {"Status": status, "StartedAt": "2026-10-28T10:00:00.123Z", "OOMKilled": False}
        if health:
            state["Health"] = {"Status": health}
        return {"Id": svc * 3, "RestartCount": restarts, "State": state,
                "Config": {"Labels": {"com.docker.compose.service": svc}}}
    m = hostmon.Metrics()
    ids = hostmon.container_metrics(m, [c("app", "running", "healthy"), c("migrate", "exited"),
                                        c("vllm-tts", "running", "unhealthy", 2)], {"app", "vllm-tts", "tunnel"})
    text = m.render()
    assert set(ids.values()) == {"app", "vllm-tts"}
    assert 'atentina_container_up{service="tunnel"} 0' in text and "migrate" not in text
    assert 'atentina_container_healthy{service="vllm-tts"} 0' in text
    assert 'atentina_container_restarts{service="vllm-tts"} 2' in text
    assert 'atentina_container_cpu_seconds_total{service="app"} 12.5' in text


# --- Config generada -------------------------------------------------------------------------------

def test_render_alertmanager_by_severity():
    assert render.alertmanager_config("")["receivers"] == [{"name": "nada"}]
    cfg = render.alertmanager_config("atentina-abc")
    routes = {r["receiver"]: r["matchers"] for r in cfg["route"]["routes"]}
    assert routes == {"ntfy-alta": ['severity="critical"'], "ntfy-baja": ['severity="warning"']}
    urls = {r["name"]: r["webhook_configs"][0]["url"] for r in cfg["receivers"] if r["name"] != "nada"}
    for name, prio in (("ntfy-alta", "high"), ("ntfy-baja", "low")):
        u = urllib.parse.urlparse(urls[name])
        q = dict(urllib.parse.parse_qsl(u.query))
        assert u.path == "/atentina-abc" and q["p"] == prio and q["tpl"] == "1"
        assert "{{range .alerts}}" in q["m"]


def test_render_prometheus_jobs_and_probes():
    cfg = render.prometheus_config("srv", True)
    jobs = {j["job_name"]: j for j in cfg["scrape_configs"]}
    assert {"node", "llm", "stt", "tts", "app", "sonda_interna_http_2xx", "sonda_externa_icmp"} <= set(jobs)
    assert jobs["app"]["authorization"] == {"credentials_file": "/etc/prometheus/app_token"}
    probes = [t for j in jobs.values() if j["job_name"].startswith("sonda_")
              for t in j["static_configs"]]
    assert all(t["labels"]["host"] == "srv" and t["labels"]["kind"] in {"interna", "externa"} for t in probes)
    json.dumps(cfg)  # se escribe como JSON (YAML válido)
