"""Estado del hardware y del servicio para el admin (docs/OBSERVABILIDAD.md): lo lee de
Prometheus (docker-compose.monitoring.yml) y lo agrupa por host.

- `now`: la foto actual (CPU, RAM, discos, red, cada GPU, servicios, sondas, SIP, saturación y alertas).
- `history`: series para los gráficos de una ventana (1 h a 7 d), con el máximo de cada paso en lo que
  tiene picos (GPU, potencia) para que una ventana larga no los promedie.
- `events`: cuándo estuvo activa cada alerta en la ventana (de la serie ALERTS de Prometheus).
- `peaks`: el máximo de cada día (resumen de picos).

Sin Prometheus (PROMETHEUS_URL vacía o caído) responde 503 `monitoring_off`/`monitoring_down`.
"""
import math
import time
from collections import defaultdict
from dataclasses import dataclass

import httpx

from ..config import settings
from .errors import ServiceError


class MonitoringUnavailable(ServiceError):
    status_code = 503
    default_code = "monitoring_down"


WINDOWS = {"1h": 3600, "6h": 6 * 3600, "24h": 86400, "7d": 7 * 86400}
POINTS = 240
FS = 'fstype=~"ext4|xfs|btrfs"'
# La temperatura de la CPU: el chip k10temp (AMD) o coretemp (Intel), por su nombre en node_hwmon_chip_names.
CPU_TEMP = ('max by (host) (node_hwmon_temp_celsius * on (host, chip) group_left '
            'node_hwmon_chip_names{chip_name=~"k10temp|coretemp"})')
THROTTLE_BAD = {"hw_slowdown", "hw_thermal", "sw_thermal", "hw_power_brake"}


@dataclass
class Sample:
    labels: dict
    value: float | None


class Prometheus:
    """Cliente mínimo de la API HTTP de Prometheus."""

    def __init__(self, url: str, timeout: float = 5.0, transport: httpx.BaseTransport | None = None):
        if not url:
            raise MonitoringUnavailable("El monitoreo no está configurado (PROMETHEUS_URL)", "monitoring_off")
        self.http = httpx.Client(base_url=url.rstrip("/"), timeout=timeout, transport=transport)

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            r = self.http.get(path, params=params)
            r.raise_for_status()
            body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise MonitoringUnavailable(f"Prometheus no responde: {type(e).__name__}") from e
        if body.get("status") != "success":
            raise MonitoringUnavailable(f"Prometheus: {body.get('error', 'error')}")
        return body["data"]

    def query(self, expr: str) -> list[Sample]:
        data = self._get("/api/v1/query", {"query": expr})
        if data.get("resultType") != "vector":
            return []
        return [Sample(r["metric"], _num(r["value"][1])) for r in data["result"]]

    def query_range(self, expr: str, start: float, end: float, step: float) -> list[tuple[dict, list]]:
        data = self._get("/api/v1/query_range", {"query": expr, "start": start, "end": end, "step": step})
        return [(r["metric"], [[float(t), _num(v)] for t, v in r["values"]]) for r in data["result"]]

    def alerts(self) -> list[dict]:
        return self._get("/api/v1/alerts").get("alerts", [])

    def close(self):
        self.http.close()


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def client(transport: httpx.BaseTransport | None = None) -> Prometheus:
    return Prometheus(settings.prometheus_url, transport=transport)


def _by(samples: list[Sample], *keys: str) -> dict:
    """{(host, *keys): valor}; host '' si la serie no lo trae."""
    return {(s.labels.get("host", ""), *(s.labels.get(k, "") for k in keys)): s.value for s in samples}


def _one(samples: list[Sample]) -> dict[str, float | None]:
    return {s.labels.get("host", ""): s.value for s in samples}


# --- Foto actual -------------------------------------------------------------------------------

NOW_QUERIES = {
    # Host
    "cpu_util": '1 - avg by (host) (rate(node_cpu_seconds_total{mode="idle"}[1m]))',
    "cpu_cores": 'count by (host) (node_cpu_seconds_total{mode="idle"})',
    "load1": "node_load1", "load5": "node_load5", "load15": "node_load15",
    "psi_cpu": "rate(node_pressure_cpu_waiting_seconds_total[1m])",
    "psi_mem": "rate(node_pressure_memory_waiting_seconds_total[1m])",
    "psi_io": "rate(node_pressure_io_waiting_seconds_total[1m])",
    "cpu_temp": CPU_TEMP,
    "cpu_power": "rate(atentina_cpu_energy_joules_total[1m])",
    "mem_total": "node_memory_MemTotal_bytes", "mem_avail": "node_memory_MemAvailable_bytes",
    "swap_total": "node_memory_SwapTotal_bytes", "swap_free": "node_memory_SwapFree_bytes",
    "oom_24h": "increase(node_vmstat_oom_kill[24h])",
    "uptime": "time() - node_boot_time_seconds",
    "ntp_offset": "node_timex_offset_seconds", "ntp_sync": "node_timex_sync_status",
    "collector_age": "time() - atentina_hostmon_last_run_timestamp_seconds",
    "udp_errors": "rate(node_netstat_Udp_RcvbufErrors[5m])",
    "public_ip_ok": "atentina_public_ip_ok", "internet_ok": "atentina_internet_ok",
    # Discos
    "fs_size": f"node_filesystem_size_bytes{{{FS}}}", "fs_avail": f"node_filesystem_avail_bytes{{{FS}}}",
    # La tendencia, recién con 6 h de datos (5 s: 4.320 muestras): con minutos da cualquier cosa.
    "fs_deriv": f"deriv(node_filesystem_avail_bytes{{{FS}}}[6h]) and count_over_time(node_filesystem_avail_bytes{{{FS}}}[6h]) > 4000",
    "disk_io": "rate(node_disk_io_time_seconds_total[1m])",
    "smart_ok": "atentina_disk_smart_ok", "smart_wear": "atentina_disk_wear_ratio",
    "smart_errors": "atentina_disk_media_errors", "smart_temp": "atentina_disk_temperature_celsius",
    # Red
    "net_rx": "rate(node_network_receive_bytes_total[1m])", "net_tx": "rate(node_network_transmit_bytes_total[1m])",
    "net_err": "rate(node_network_receive_errs_total[5m]) + rate(node_network_transmit_errs_total[5m])",
    "net_drop": "rate(node_network_receive_drop_total[5m]) + rate(node_network_transmit_drop_total[5m])",
    # GPU
    "gpu_util": "atentina_gpu_utilization_ratio", "gpu_mem_used": "atentina_gpu_memory_used_bytes",
    "gpu_mem_total": "atentina_gpu_memory_total_bytes", "gpu_power": "atentina_gpu_power_watts",
    "gpu_power_limit": "atentina_gpu_power_limit_watts", "gpu_temp": "atentina_gpu_temperature_celsius",
    "gpu_fan": "atentina_gpu_fan_ratio", "gpu_clock_sm": "atentina_gpu_clock_sm_mhz",
    "gpu_clock_mem": "atentina_gpu_clock_mem_mhz", "gpu_pcie_gen": "atentina_gpu_pcie_gen",
    "gpu_pcie_gen_max": "atentina_gpu_pcie_gen_max", "gpu_pcie_width": "atentina_gpu_pcie_width",
    "gpu_pcie_width_max": "atentina_gpu_pcie_width_max", "gpu_throttle": "atentina_gpu_throttle == 1",
    "gpu_proc": "atentina_gpu_process_memory_bytes",
    "gpu_xid_24h": "increase(atentina_gpu_xid_errors_total[24h])",
    # Servicios y sondas
    "svc_up": "atentina_container_up", "svc_healthy": "atentina_container_healthy",
    "svc_restarts": "atentina_container_restarts", "svc_cpu": "rate(atentina_container_cpu_seconds_total[1m])",
    "svc_mem": "atentina_container_memory_bytes",
    "probe_ok": "probe_success", "probe_time": "probe_duration_seconds",
    "sip": "atentina_sip_registered",
    # Saturación
    "inf_running": 'vllm:num_requests_running{job=~"llm|stt|tts"}',
    "inf_waiting": 'vllm:num_requests_waiting{job=~"llm|stt|tts"}',
    "kv_cache": 'vllm:kv_cache_usage_perc{job="llm"}',
    "calls_active": "sum by (host) (atentina_calls_active)",
    "anura_busy": "atentina_anura_channels_busy", "anura_total": "atentina_anura_channels_total",
    "turn_p95": "atentina_turn_latency_p95_seconds",
}


def _host(r: dict[str, list[Sample]], host: str) -> dict:
    one = {k: _one(v).get(host) for k, v in r.items() if k in {
        "cpu_util", "cpu_cores", "load1", "load5", "load15", "psi_cpu", "psi_mem", "psi_io", "cpu_temp",
        "cpu_power", "mem_total", "mem_avail", "swap_total", "swap_free", "oom_24h", "uptime", "ntp_offset",
        "ntp_sync", "collector_age", "udp_errors", "public_ip_ok", "internet_ok"}}
    disks = []
    size, avail, deriv = _by(r["fs_size"], "mountpoint", "device"), _by(r["fs_avail"], "mountpoint", "device"), \
        _by(r["fs_deriv"], "mountpoint", "device")
    for (h, mp, dev), sz in sorted(size.items(), key=lambda kv: kv[0][1]):
        if h != host or not sz:
            continue
        av = avail.get((h, mp, dev))
        d = deriv.get((h, mp, dev))
        days = av / -d / 86400 if av is not None and d is not None and d < 0 else None
        disks.append({"mountpoint": mp, "device": dev, "size_bytes": sz, "avail_bytes": av,
                      "used_ratio": 1 - av / sz if av is not None else None,
                      "days_to_full": round(days, 1) if days is not None and days < 365 else None})
    io = {dev: v for (h, dev), v in _by(r["disk_io"], "device").items() if h == host and not dev.startswith(("loop", "dm-"))}
    smart = []
    for (h, dev, model), ok in _by(r["smart_ok"], "device", "model").items():
        if h != host:
            continue
        key = (h, dev, model)
        smart.append({"device": dev, "model": model, "ok": bool(ok), "io_busy_ratio": io.get(dev),
                      "wear_ratio": _by(r["smart_wear"], "device", "model").get(key),
                      "media_errors": _by(r["smart_errors"], "device", "model").get(key),
                      "temperature_c": _by(r["smart_temp"], "device", "model").get(key)})
    net = []
    rx, tx = _by(r["net_rx"], "device"), _by(r["net_tx"], "device")
    err, drop = _by(r["net_err"], "device"), _by(r["net_drop"], "device")
    for (h, dev), v in sorted(rx.items()):
        if h == host:
            net.append({"iface": dev, "rx_bytes_s": v, "tx_bytes_s": tx.get((h, dev)),
                        "errors_s": err.get((h, dev)), "drops_s": drop.get((h, dev))})
    gpus = _gpus(r, host)
    gpu_power = sum(g["power_w"] or 0 for g in gpus)
    mt, ma = one["mem_total"], one["mem_avail"]
    st, sf = one["swap_total"], one["swap_free"]
    return {
        "host": host,
        "collector_age_s": one["collector_age"],
        "uptime_s": one["uptime"],
        "cpu": {"util_ratio": one["cpu_util"], "cores": one["cpu_cores"], "load1": one["load1"],
                "load5": one["load5"], "load15": one["load15"], "pressure_ratio": one["psi_cpu"],
                "temperature_c": one["cpu_temp"], "power_w": one["cpu_power"]},
        "memory": {"total_bytes": mt, "available_bytes": ma,
                   "used_ratio": 1 - ma / mt if mt and ma is not None else None,
                   "swap_total_bytes": st, "swap_used_bytes": st - sf if st is not None and sf is not None else None,
                   "pressure_ratio": one["psi_mem"], "oom_kills_24h": one["oom_24h"]},
        "io_pressure_ratio": one["psi_io"],
        "disks": disks, "smart": smart, "network": net,
        "udp_rcvbuf_errors_s": one["udp_errors"],
        "gpus": gpus,
        "power": {"gpus_w": gpu_power if gpus else None, "cpu_w": one["cpu_power"],
                  # Estimado (sin medidor de pared): GPUs + paquete de la CPU.
                  "estimated_w": gpu_power + (one["cpu_power"] or 0) if gpus else None},
        "clock": {"offset_s": one["ntp_offset"], "synced": bool(one["ntp_sync"]) if one["ntp_sync"] is not None
                  else None},
        "connectivity": {"internet_ok": _bool(one["internet_ok"]), "public_ip_ok": _bool(one["public_ip_ok"]),
                         "sip": [{"registration": reg, "ok": bool(v)}
                                 for (h, reg), v in sorted(_by(r["sip"], "registration").items()) if h == host]},
        "services": _services(r, host),
        "probes": _probes(r, host),
        "saturation": _saturation(r, host),
    }


def _bool(v):
    return None if v is None else bool(v)


def _gpus(r, host) -> list[dict]:
    def get(key):
        return {k[1]: v for k, v in _by(r[key], "gpu").items() if k[0] == host}
    names = {s.labels.get("gpu"): s.labels for s in r["gpu_util"] + r["gpu_mem_total"]
             if s.labels.get("host", "") == host}
    vals = {k: get(k) for k in ("gpu_util", "gpu_mem_used", "gpu_mem_total", "gpu_power", "gpu_power_limit",
                                "gpu_temp", "gpu_fan", "gpu_clock_sm", "gpu_clock_mem", "gpu_pcie_gen",
                                "gpu_pcie_gen_max", "gpu_pcie_width", "gpu_pcie_width_max", "gpu_xid_24h")}
    throttle = defaultdict(list)
    for s in r["gpu_throttle"]:
        if s.labels.get("host", "") == host:
            throttle[s.labels.get("gpu")].append(s.labels.get("reason"))
    procs = defaultdict(list)
    for s in r["gpu_proc"]:
        if s.labels.get("host", "") == host:
            procs[s.labels.get("gpu")].append({"service": s.labels.get("service"), "memory_bytes": s.value})
    out = []
    for idx in sorted(names, key=lambda i: int(i) if str(i).isdigit() else 99):
        lab = names[idx]
        reasons = sorted(throttle.get(idx, []))
        out.append({
            "index": int(idx) if str(idx).isdigit() else idx, "name": lab.get("name", ""), "bus": lab.get("bus", ""),
            "util_ratio": vals["gpu_util"].get(idx), "memory_used_bytes": vals["gpu_mem_used"].get(idx),
            "memory_total_bytes": vals["gpu_mem_total"].get(idx), "power_w": vals["gpu_power"].get(idx),
            "power_limit_w": vals["gpu_power_limit"].get(idx), "temperature_c": vals["gpu_temp"].get(idx),
            "fan_ratio": vals["gpu_fan"].get(idx), "clock_sm_mhz": vals["gpu_clock_sm"].get(idx),
            "clock_mem_mhz": vals["gpu_clock_mem"].get(idx),
            "pcie": {"gen": vals["gpu_pcie_gen"].get(idx), "gen_max": vals["gpu_pcie_gen_max"].get(idx),
                     "width": vals["gpu_pcie_width"].get(idx), "width_max": vals["gpu_pcie_width_max"].get(idx)},
            "throttle": reasons, "throttle_bad": any(x in THROTTLE_BAD for x in reasons),
            "xid_errors_24h": vals["gpu_xid_24h"].get(idx),
            "processes": sorted(procs.get(idx, []), key=lambda p: -(p["memory_bytes"] or 0)),
        })
    return out


def _services(r, host) -> list[dict]:
    up = _by(r["svc_up"], "service")
    healthy, restarts = _by(r["svc_healthy"], "service"), _by(r["svc_restarts"], "service")
    cpu, mem = _by(r["svc_cpu"], "service"), _by(r["svc_mem"], "service")
    out = []
    for (h, svc), v in sorted(up.items(), key=lambda kv: kv[0][1]):
        if h != host:
            continue
        k = (h, svc)
        out.append({"service": svc, "up": bool(v), "healthy": healthy.get(k), "restarts": restarts.get(k),
                    "cpu_cores": cpu.get(k), "memory_bytes": mem.get(k)})
    return out


def _probes(r, host) -> list[dict]:
    t = {(s.labels.get("host", ""), s.labels.get("probe")): s.value for s in r["probe_time"]}
    out = []
    for s in r["probe_ok"]:
        h = s.labels.get("host", "")
        if h != host:
            continue
        name = s.labels.get("probe", s.labels.get("instance", ""))
        out.append({"name": name, "kind": s.labels.get("kind", ""), "target": s.labels.get("instance", ""),
                    "ok": bool(s.value), "duration_s": t.get((h, name))})
    return sorted(out, key=lambda p: (p["kind"], p["name"]))


def _saturation(r, host) -> dict:
    run, wait = _by(r["inf_running"], "job"), _by(r["inf_waiting"], "job")
    inference = {job: {"running": run.get((host, job)), "waiting": wait.get((host, job))}
                 for job in ("llm", "stt", "tts")}
    return {"inference": inference, "llm_kv_cache_ratio": _one(r["kv_cache"]).get(host),
            "calls_active": _one(r["calls_active"]).get(host),
            "anura_channels_busy": _one(r["anura_busy"]).get(host),
            "anura_channels_total": _one(r["anura_total"]).get(host),
            "turn_latency_p95_s": _one(r["turn_p95"]).get(host)}


def now(prom: Prometheus) -> dict:
    r = {k: prom.query(q) for k, q in NOW_QUERIES.items()}
    hosts = sorted({s.labels.get("host", "") for k in ("cpu_util", "gpu_util", "svc_up") for s in r[k]})
    alerts = [{"name": a["labels"].get("alertname", ""), "severity": a["labels"].get("severity", ""),
               "state": a.get("state", ""), "summary": a.get("annotations", {}).get("summary", ""),
               "since": a.get("activeAt"), "host": a["labels"].get("host", "")}
              for a in prom.alerts() if a["labels"].get("alertname") != "PruebaDeAlerta"]
    alerts.sort(key=lambda a: (a["severity"] != "critical", a["state"] != "firing", a["since"] or ""))
    return {"generated_at": time.time(), "hosts": [_host(r, h) for h in hosts], "alerts": alerts}


# --- Historia, eventos y picos -----------------------------------------------------------------

def _step(seconds: int) -> int:
    return max(15, seconds // POINTS)


def _history_queries(step: int) -> dict[str, tuple[str, str]]:
    """{serie: (expr, etiqueta que separa las líneas)}. Lo que tiene picos, con el máximo del paso."""
    w = f"{step}s"
    return {
        "cpu_util": (f'1 - avg by (host) (rate(node_cpu_seconds_total{{mode="idle"}}[{max(step, 60)}s]))', ""),
        "memory_used": ("1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes", ""),
        "gpu_util": (f"max_over_time(atentina_gpu_utilization_ratio[{w}])", "gpu"),
        "gpu_memory": ("atentina_gpu_memory_used_bytes / atentina_gpu_memory_total_bytes", "gpu"),
        "gpu_power": (f"max_over_time(atentina_gpu_power_watts[{w}])", "gpu"),
        "gpu_temp": (f"max_over_time(atentina_gpu_temperature_celsius[{w}])", "gpu"),
        # Sin RAPL (colector sin root) queda solo lo de las GPUs, en vez de no dar nada.
        "power_total": ((f"sum by (host) (max_over_time(atentina_gpu_power_watts[{w}])) + on (host) "
                         f"(sum by (host) (rate(atentina_cpu_energy_joules_total[{max(step, 60)}s])) "
                         f"or sum by (host) (max_over_time(atentina_gpu_power_watts[{w}])) * 0)"), ""),
        "calls_active": (f"max_over_time(sum by (host) (atentina_calls_active)[{w}:15s])", ""),
        "llm_kv_cache": (f'max_over_time(vllm:kv_cache_usage_perc{{job="llm"}}[{w}])', ""),
        "net_rx": (f"sum by (host) (rate(node_network_receive_bytes_total[{max(step, 60)}s]))", ""),
        "net_tx": (f"sum by (host) (rate(node_network_transmit_bytes_total[{max(step, 60)}s]))", ""),
    }


def history(prom: Prometheus, window: str) -> dict:
    seconds = WINDOWS[window]
    step = _step(seconds)
    end = time.time()
    start = end - seconds
    series = {}
    for name, (expr, by) in _history_queries(step).items():
        series[name] = [{"host": lab.get("host", ""), "label": lab.get(by, "") if by else "", "points": pts}
                        for lab, pts in prom.query_range(expr, start, end, step)]
    return {"window": window, "step_s": step, "start": start, "end": end, "series": series}


DETAIL_LABELS = ("gpu", "service", "probe", "mountpoint", "device", "registration", "job", "reason", "xid")


def events(prom: Prometheus, window: str) -> list[dict]:
    """Tramos en que cada alerta estuvo disparada, del más nuevo al más viejo."""
    seconds = WINDOWS[window]
    step = 60 if seconds > 3600 else 15
    end = time.time()
    out = []
    for lab, pts in prom.query_range('ALERTS{alertstate="firing"}', end - seconds, end, step):
        if lab.get("alertname") == "PruebaDeAlerta":
            continue
        detail = ", ".join(f"{k} {lab[k]}" for k in DETAIL_LABELS if lab.get(k))
        seg_start = prev = None
        for t, _ in pts:
            if seg_start is None:
                seg_start = t
            elif t - prev > step * 1.5:
                out.append(_event(lab, detail, seg_start, prev, step, end))
                seg_start = t
            prev = t
        if seg_start is not None:
            out.append(_event(lab, detail, seg_start, prev, step, end))
    out.sort(key=lambda e: -e["start"])
    return out


def _event(lab, detail, start, last, step, end) -> dict:
    ongoing = end - last <= step * 1.5
    return {"name": lab.get("alertname", ""), "severity": lab.get("severity", ""), "host": lab.get("host", ""),
            "detail": detail, "start": start, "end": None if ongoing else last + step}


PEAK_QUERIES = {
    "cpu_util_max": "max_over_time((1 - avg by (host) (rate(node_cpu_seconds_total{mode=\"idle\"}[1m])))[1d:1m])",
    "memory_used_max": "max_over_time((1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)[1d:1m])",
    "gpu_power_max_w": "max_over_time((sum by (host) (atentina_gpu_power_watts))[1d:15s])",
    "gpu_temp_max_c": "max by (host) (max_over_time(atentina_gpu_temperature_celsius[1d]))",
    "gpu_util_max": "max by (host) (max_over_time(atentina_gpu_utilization_ratio[1d]))",
    "llm_kv_cache_max": 'max by (host) (max_over_time(vllm:kv_cache_usage_perc{job="llm"}[1d]))',
    "calls_active_max": "max_over_time((sum by (host) (atentina_calls_active))[1d:15s])",
    "alerts_critical": 'count by (host) (max_over_time(ALERTS{alertstate="firing",severity="critical"}[1d]))',
}


def peaks(prom: Prometheus, days: int, tz_offset_s: int = -3 * 3600) -> list[dict]:
    """Un renglón por día (cerrando a medianoche local) con el máximo de cada métrica."""
    day = 86400
    now_s = time.time()
    end = (now_s + tz_offset_s) // day * day + day - tz_offset_s  # próxima medianoche local
    start = end - days * day
    rows: dict[tuple[str, float], dict] = {}
    for name, expr in PEAK_QUERIES.items():
        for lab, pts in prom.query_range(expr, start + day, end, day):
            for t, v in pts:
                row = rows.setdefault((lab.get("host", ""), t), {"host": lab.get("host", ""), "day_end": t})
                row[name] = v
    return sorted(rows.values(), key=lambda r: (-r["day_end"], r["host"]))
