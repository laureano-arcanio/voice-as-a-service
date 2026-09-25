#!/usr/bin/env python3
"""Analisis del test de capacidad (docs/CAPACITY_TEST_PLAN.md, secciones 7 y 8).

Cruza el run del cliente (run.py: run.json, calls.csv, turns.csv, client.csv)
con el monitor del server (monitor.py: sampler/, mem.csv, procmem.csv,
gpumem.csv, cpu.csv, agentlog.csv) y calcula por escalon, sin el transitorio:
espera percibida y buckets, calidad por llamada, SLO, codo, cuello de botella,
recursos, cores y memoria por llamada y energia. La memoria de cada componente
se ajusta contra la concurrencia real (recta: base + MB por llamada).

Escribe en el directorio del run: summary.json (ficha de capacidad),
steps.csv, windows.csv (ventanas de 30 s), memoria.csv y report.html.

Uso (solo stdlib):
    python3 scripts/capacity/analyze.py <run cliente> [--monitor <dir monitor>] [--base <summary.json base>] [--md]
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

VENTANA_S = 30
# Ajuste memoria contra llamadas: por debajo de este r2 el componente "no escala".
R2_MIN = 0.5


# ---------- utilidades ----------

def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pct(v, p):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    k = (len(v) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def media(v):
    v = [x for x in v if x is not None]
    return st.fmean(v) if v else None


def r(x, n=3):
    return None if x is None else round(x, n)


def leer_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def recta(xs, ys):
    """Minimos cuadrados: (ordenada, pendiente, r2)."""
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 3:
        return None
    mx, my = st.fmean(p[0] for p in pts), st.fmean(p[1] for p in pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx == 0:
        return None
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    b = sxy / sxx
    a = my - b * mx
    syy = sum((p[1] - my) ** 2 for p in pts)
    r2 = (sxy * sxy / (sxx * syy)) if syy else 1.0
    return a, b, r2


# ---------- carga de datos ----------

class Run:
    def __init__(self, rundir: Path, mondir: Path | None, base: Path | None):
        self.dir = rundir
        self.run = json.loads((rundir / "run.json").read_text())
        self.perfil = self.run["perfil"]
        self.calls = leer_csv(rundir / "calls.csv")
        self.turns = leer_csv(rundir / "turns.csv")
        self.client = leer_csv(rundir / "client.csv")
        self.hw_cliente = self._json(rundir / "hw_cliente.json")
        self.mon = mondir
        self.hw_server = self._json(mondir / "hw_server.json") if mondir else None
        self.base = json.loads(base.read_text()) if base else None
        for c in self.calls:
            for k in ("t_inicio", "t_fin", "saludo_s", "mic_lag_max_s", "wer", "t_conectado"):
                c[k] = fnum(c.get(k))
        for t in self.turns:
            for k in ("t_fin_envio", "t_resp", "espera_s", "resp_s", "cortes_n", "cortes_s", "wer",
                      "eou", "stt", "endpointing", "llm", "llm_total", "tts", "total", "e2e"):
                t[k] = fnum(t.get(k))
        # Serie de concurrencia real por segundo, desde las ventanas de vida de cada llamada.
        spans = [(c["t_inicio"], c["t_fin"]) for c in self.calls if c["t_inicio"] and c["t_fin"]]
        self.t_min = min((s for s, _ in spans), default=0)
        self.t_max = max((e for _, e in spans), default=0)
        self.conc = defaultdict(int)
        for s, e in spans:
            for sec in range(int(s), int(e) + 1):
                self.conc[sec] += 1
        self.mon_data = self._cargar_monitor() if mondir else {}

    @staticmethod
    def _json(p: Path):
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return None

    def _cargar_monitor(self) -> dict:
        m = self.mon
        s = m / "sampler"
        vllm = []
        if (s / "vllm.jsonl").exists():
            vllm = [json.loads(l) for l in open(s / "vllm.jsonl")]
        return {"sys": leer_csv(s / "sys.csv"), "cont": leer_csv(s / "cont.csv"), "gpu": leer_csv(s / "gpu.csv"),
                "vllm": vllm, "mem": leer_csv(m / "mem.csv"), "procmem": leer_csv(m / "procmem.csv"),
                "gpumem": leer_csv(m / "gpumem.csv"), "cpu": leer_csv(m / "cpu.csv"),
                "agentlog": leer_csv(m / "agentlog.csv")}

    def conc_media(self, a, b):
        v = [self.conc.get(sec, 0) for sec in range(int(a), int(b))]
        return (st.fmean(v), max(v)) if v else (0.0, 0)

    def en(self, filas, a, b, col="ts"):
        return [f for f in filas if (t := fnum(f.get(col))) is not None and a <= t < b]


# ---------- metricas por intervalo ----------

def bucket(espera, cortes, nombres):
    if espera is None:
        return "sin_respuesta"
    for c, n in zip(cortes, nombres):
        if espera < c:
            return n
    return nombres[-1]


def metricas_turnos(turns, perfil, piso):
    cortes, nombres = perfil["buckets_s"], perfil["buckets_nombres"]
    esperas = [t["espera_s"] for t in turns]
    validas = [e for e in esperas if e is not None]
    n = len(turns)
    bk = defaultdict(int)
    for t in turns:
        bk[bucket(t["espera_s"], cortes, nombres)] += 1
    slo = perfil["slo"]
    ok = sum(1 for e in esperas if e is not None and e <= slo["ok_s"])
    pesimo = sum(1 for e in esperas if e is None or e > cortes[-1])
    malos = sum(1 for e in esperas if e is None or e > cortes[-2])
    par = [t for t in turns if t["e2e"] is not None]
    resp = [t for t in turns if t["resp_s"]]
    out = {
        "turnos": n, "sin_respuesta": sum(1 for e in esperas if e is None),
        "espera_p50": r(pct(validas, .5)), "espera_p95": r(pct(validas, .95)), "espera_p99": r(pct(validas, .99)),
        "frac_ok": r(ok / n) if n else None, "frac_pesimo": r(pesimo / n) if n else None,
        "frac_malo_o_peor": r(malos / n) if n else None,
        "buckets": {k: r(bk[k] / n) if n else 0 for k in [*nombres, "sin_respuesta"]},
        "wer": r(media([t["wer"] for t in turns])),
        "cortes_por_resp": r(media([t["cortes_n"] for t in resp])),
        "frac_resp_con_cortes": r(sum(1 for t in resp if t["cortes_n"]) / len(resp)) if resp else None,
    }
    for k in ("eou", "stt", "llm", "llm_total", "tts", "e2e"):
        out[f"{k}_p50"] = r(pct([t[k] for t in par], .5))
        out[f"{k}_p95"] = r(pct([t[k] for t in par], .95))
    if piso is not None:
        out["agregada_p50"] = r(out["espera_p50"] - piso) if out["espera_p50"] is not None else None
        out["agregada_p95"] = r(out["espera_p95"] - piso) if out["espera_p95"] is not None else None
    return out


def metricas_llamadas(calls, perfil, cortes, nombres, turns_por_call):
    lb = perfil["llamada_buena"]
    n = len(calls)
    buenas = fallas = 0
    for c in calls:
        falla = bool(c.get("error")) or c.get("status") not in ("finalizada",) or c["saludo_s"] is None
        fallas += falla
        ts = turns_por_call.get(c["call_id"], [])
        bks = [bucket(t["espera_s"], cortes, nombres) for t in ts]
        buena = (not falla and c["saludo_s"] <= lb["saludo_max_s"] and "sin_respuesta" not in bks
                 and nombres[-1] not in bks and bks.count(nombres[-2]) <= lb["max_malos"])
        buenas += buena
    return {"llamadas": n, "frac_buenas": r(buenas / n) if n else None, "frac_fallas": r(fallas / n) if n else None,
            "saludo_p50": r(pct([c["saludo_s"] for c in calls], .5)), "saludo_p95": r(pct([c["saludo_s"] for c in calls], .95)),
            "mic_lag_p95": r(pct([c["mic_lag_max_s"] for c in calls], .95))}


def delta_media(vllm, svc, clave, a, b, suf=""):
    """Media de un histograma de vLLM en [a, b): delta sum / delta count.
    suf es la etapa de vLLM-Omni (@s0), que va despues de _sum/_count."""
    ks, kc = f"{clave}_sum{suf}", f"{clave}_count{suf}"
    f = [d for d in vllm if d["svc"] == svc and a <= d["ts"] < b and ks in d]
    if len(f) < 2:
        return None
    ds = f[-1][ks] - f[0][ks]
    dc = f[-1][kc] - f[0][kc]
    return ds / dc if dc > 0 else None


def recursos(R: Run, a, b, conc_media):
    m = R.mon_data
    if not m:
        return {}
    out = {}
    sys_ = R.en(m["sys"], a, b)
    busy = [fnum(s["total_busy_pct"]) for s in sys_]
    out["cpu_host_prom"], out["cpu_host_p95"] = r(media(busy), 1), r(pct(busy, .95), 1)
    ncpu = len([k for k in (sys_[0] if sys_ else {}) if k.startswith("cpu")])
    out["cpu_core_mas_cargado_p95"] = r(pct([max(fnum(s[f"cpu{i}"]) for i in range(ncpu)) for s in sys_], .95), 1) if ncpu else None
    ag = [fnum(c["cpu_cores"]) for c in R.en(m["cont"], a, b) if c["svc"] == "agent"]
    out["agente_cores_prom"], out["agente_cores_max"] = r(media(ag), 2), r(max(ag), 2) if ag else None
    out["cores_por_llamada"] = r(media(ag) / conc_media, 3) if ag and conc_media else None
    gpus = defaultdict(list)
    for g in R.en(m["gpu"], a, b):
        gpus[g["index"]].append(g)
    for gi, rows in sorted(gpus.items()):
        u = [fnum(g["utilization.gpu"]) for g in rows]
        out[f"gpu{gi}_uso"] = r(media(u), 1)
        out[f"gpu{gi}_seg95"] = r(sum(1 for x in u if x >= 95) / len(u), 3)
        out[f"gpu{gi}_vram_max_mib"] = max(fnum(g["memory.used"]) for g in rows)
        out[f"gpu{gi}_temp_max"] = max(fnum(g["temperature.gpu"]) for g in rows)
        out[f"gpu{gi}_throttle_termico"] = r(sum(1 for g in rows if int(g["clocks_throttle_reasons.active"], 16) & 0x60) / len(rows), 3)
        out[f"gpu{gi}_wh"] = r(sum(fnum(g["power.draw"]) for g in rows) / 3600, 3)
    for svc, pre in (("vllm-llm", "llm"), ("stt-parakeet", "stt"), ("vllm-tts", "tts")):
        suf = "@s0" if svc == "vllm-tts" else ""
        cola = delta_media(m["vllm"], svc, "request_queue_time_seconds", a, b, suf)
        out[f"{pre}_cola_ms"] = r(1000 * cola, 1) if cola is not None else None
        itl = delta_media(m["vllm"], svc, "inter_token_latency_seconds", a, b, suf)
        out[f"{pre}_entre_tokens_ms"] = r(1000 * itl, 1) if itl is not None else None
        f = [d for d in m["vllm"] if d["svc"] == svc and a <= d["ts"] < b]
        out[f"{pre}_en_vuelo_max"] = max((d.get("num_requests_running" + suf, 0) + d.get("num_requests_waiting" + suf, 0) for d in f), default=None)
        kv = [d.get("kv_cache_usage_perc" + suf) for d in f if d.get("kv_cache_usage_perc" + suf) is not None]
        out[f"{pre}_kv_max"] = r(max(kv), 3) if kv else None
        pre_ = [d.get("num_preemptions_total" + suf) for d in f if d.get("num_preemptions_total" + suf) is not None]
        out[f"{pre}_preemptions"] = (pre_[-1] - pre_[0]) if len(pre_) > 1 else None
    ttft = delta_media(m["vllm"], "vllm-llm", "time_to_first_token_seconds", a, b)
    out["llm_ttft_ms"] = r(1000 * ttft, 1) if ttft is not None else None
    cpu = R.en(m["cpu"], a, b)
    out["cpu_temp_max"] = max((fnum(c["temp_c"]) for c in cpu if fnum(c["temp_c"]) is not None), default=None)
    out["cpu_mhz_prom"] = r(media([fnum(c["freq_mhz_prom"]) for c in cpu]), 0)
    ev = defaultdict(int)
    for l in R.en(m["agentlog"], a, b):
        ev[l["evento"]] += int(l["cuenta"])
    out["agente_eventos"] = dict(ev)
    mem = defaultdict(list)
    for x in R.en(m["mem"], a, b):
        mem[x["componente"]].append(fnum(x["mem_gb"]))
    out["mem_gb_max"] = {k: r(max(v), 2) for k, v in mem.items() if v}
    return out


# ---------- escalones ----------

def ventanas_de_pasos(R: Run):
    desc = R.perfil.get("descartar_s", 0)
    out = []
    for p in R.run.get("pasos", []):
        if p["paso"] == "warmup":
            continue
        a = p["t0"] + (0 if p["modo"] == "cerrado" else desc)
        out.append((p, a, p["t1"]))
    return out


def analizar(R: Run) -> dict:
    perfil = R.perfil
    cortes, nombres = perfil["buckets_s"], perfil["buckets_nombres"]
    turns_por_call = defaultdict(list)
    for t in R.turns:
        turns_por_call[t["call_id"]].append(t)
    pasos = ventanas_de_pasos(R)
    # Piso: p50 de la espera con 1 llamada (este run si es `base`, o el summary de --base).
    piso = None
    if R.base:
        piso = R.base.get("piso_p50")
    elif perfil["nombre"] == "base":
        piso = pct([t["espera_s"] for t in R.turns], .5)

    filas = []
    for p, a, b in pasos:
        turns = [t for t in R.turns if t["t_fin_envio"] is not None and a <= t["t_fin_envio"] < b]
        calls = [c for c in R.calls if c["t_inicio"] is not None and a <= c["t_inicio"] < b]
        cm, cx = R.conc_media(a, b)
        cli = [fnum(x["cpu_pct"]) for x in R.client if a <= fnum(x["ts"]) < b]
        f = {"paso": p["paso"], "concurrencia_obj": p["concurrencia"], "desde": a, "hasta": b,
             "concurrencia_real": r(cm, 1), "concurrencia_max": cx,
             "llegadas_min": r(len(calls) / ((b - a) / 60), 2) if b > a else None,
             "completadas_min": r(sum(1 for c in R.calls if c["t_fin"] and a <= c["t_fin"] < b) / ((b - a) / 60), 2) if b > a else None,
             "cliente_cpu_p95": r(pct(cli, .95), 1)}
        f.update(metricas_turnos(turns, perfil, piso))
        f.update(metricas_llamadas(calls, perfil, cortes, nombres, turns_por_call))
        f.update(recursos(R, a, b, cm))
        call_min = sum(R.conc.get(s, 0) for s in range(int(a), int(b))) / 60
        wh = sum(v for k, v in f.items() if k.startswith("gpu") and k.endswith("_wh") and v)
        f["wh_gpu_por_llamada_min"] = r(wh / call_min, 4) if call_min else None
        cl = perfil["cliente"]
        f["cliente_sano"] = not ((f["mic_lag_p95"] or 0) > cl["mic_lag_p95_s"] or (f["cliente_cpu_p95"] or 0) > cl["cpu_p95_pct"])
        slo = perfil["slo"]
        f["cumple_slo"] = bool(f["turnos"] and f["cliente_sano"]
                               and f["frac_ok"] >= slo["p_ok"] and f["frac_pesimo"] <= slo["p_pesimo"]
                               and (f["frac_buenas"] or 0) >= slo["llamadas_buenas"] and (f["frac_fallas"] or 0) <= slo["fallas"])
        filas.append(f)

    sanos = [f for f in filas if f["cliente_sano"] and f["turnos"]]
    capacidad = max((f for f in sanos if f["cumple_slo"]), key=lambda f: f["concurrencia_real"], default=None)
    codo = None
    for f in sanos:
        if (f.get("agregada_p95") is not None and f["agregada_p95"] > 0.5) or (f["frac_malo_o_peor"] or 0) > 0.05:
            codo = f
            break
    # Carga maxima con la espera p95 bajo cada umbral (el SLO completo puede no cumplirse con el piso actual).
    por_umbral = {}
    for u in (2.0, 3.0, 4.0, 5.0):
        ok = [f for f in sanos if f["espera_p95"] is not None and f["espera_p95"] <= u and f["sin_respuesta"] == 0]
        por_umbral[f"p95<={u:g}s"] = max((f["concurrencia_real"] for f in ok), default=None)
    ref = codo or (sanos[-1] if sanos else None)
    duraciones = [c["t_fin"] - c["t_inicio"] for c in R.calls if c["t_fin"] and c["t_inicio"] and not c.get("error")]
    cpl = [f["cores_por_llamada"] for f in filas if f.get("cores_por_llamada")]
    wh = [f["wh_gpu_por_llamada_min"] for f in filas if f.get("wh_gpu_por_llamada_min")]
    ngpu = len((R.hw_server or {}).get("gpus") or []) or None
    summary = {
        "run": R.dir.name, "perfil": perfil["nombre"], "perfil_version": perfil.get("version"),
        "perfil_hash": R.run.get("perfil_hash"), "workflow": perfil["workflow"],
        "hw_id": (R.hw_server or {}).get("hw_id"), "config_id": (R.hw_server or {}).get("config_id"),
        "hw_id_cliente": (R.hw_cliente or {}).get("hw_id"),
        "piso_p50": r(piso), "duracion_llamada_s": r(media(duraciones), 1),
        "slo": perfil["slo"],
        "capacidad_simultaneas": capacidad["concurrencia_real"] if capacidad else None,
        "capacidad_por_min": capacidad["completadas_min"] if capacidad else None,
        "capacidad_paso": capacidad["paso"] if capacidad else None,
        "capacidad_por_umbral_p95": por_umbral,
        "codo_paso": codo["paso"] if codo else None,
        "codo_concurrencia": codo["concurrencia_real"] if codo else None,
        "cuello": cuello(ref) if ref else [],
        "cores_por_llamada": r(pct(cpl, .5), 3), "wh_gpu_por_llamada_min": r(pct(wh, .5), 4),
        "llamadas_por_gpu": r(capacidad["concurrencia_real"] / ngpu, 1) if capacidad and ngpu else None,
        "pasos_cliente_saturado": [f["paso"] for f in filas if not f["cliente_sano"]],
    }
    return {"summary": summary, "pasos": filas}


def cuello(f: dict) -> list[str]:
    """Recursos saturados en el escalon de referencia (seccion 7 del plan)."""
    out = []
    if (f.get("cpu_host_p95") or 0) >= 90 or (f.get("cpu_core_mas_cargado_p95") or 0) >= 95:
        out.append(f"CPU del host (p95 {f.get('cpu_host_p95')} %, core mas cargado {f.get('cpu_core_mas_cargado_p95')} %)")
    for k, v in f.items():
        if k.endswith("_seg95") and (v or 0) >= 0.9:
            out.append(f"{k.split('_')[0].upper()} con {v:.0%} de los segundos al >=95 %")
    for pre in ("llm", "stt", "tts"):
        if (f.get(f"{pre}_cola_ms") or 0) > 100:
            out.append(f"cola de {pre.upper()} {f[f'{pre}_cola_ms']} ms")
    if (f.get("tts_entre_tokens_ms") or 0) > 83:
        out.append(f"TTS {f['tts_entre_tokens_ms']} ms entre tokens (tope 83)")
    for pre in ("llm", "tts"):
        if (f.get(f"{pre}_kv_max") or 0) >= 0.95 or (f.get(f"{pre}_preemptions") or 0) > 0:
            out.append(f"KV de {pre.upper()} {f.get(f'{pre}_kv_max')} ({f.get(f'{pre}_preemptions')} preemptions)")
    if f.get("agente_eventos", {}).get("vad_slow"):
        out.append(f"agente: {f['agente_eventos']['vad_slow']} avisos de VAD atrasado")
    if not f.get("cliente_sano", True):
        out.append("cliente saturado (el escalon no vale)")
    return out


# ---------- memoria: como escala con las llamadas ----------

def memoria(R: Run) -> dict:
    """Por componente, recta memoria = base + pendiente x llamadas simultaneas,
    sobre ventanas de 30 s de todo el run (sin warm-up). RAM de mem.csv (GB),
    PSS del agente, y VRAM por componente de gpumem.csv (MiB)."""
    m = R.mon_data
    if not m or not R.calls:
        return {}
    ini = next((p["t1"] for p in R.run.get("pasos", []) if p["paso"] == "warmup"), R.t_min)
    fin = R.t_max
    vent = [(a, a + VENTANA_S) for a in range(int(ini), int(fin) - VENTANA_S + 1, VENTANA_S)]
    xs = [R.conc_media(a, b)[0] for a, b in vent]
    series = {}
    por_comp = defaultdict(list)
    for x in m["mem"]:
        por_comp[x["componente"]].append(x)
    for comp, rows in por_comp.items():
        for col, nombre in (("mem_gb", "ram"), ("pss_gb", "pss")):
            ys = []
            for a, b in vent:
                v = [fnum(x[col]) for x in rows if a <= fnum(x["ts"]) < b and fnum(x[col]) is not None]
                ys.append(media(v))
            if any(y is not None for y in ys):
                series[(comp, nombre, "GB")] = ys
    vram = defaultdict(lambda: defaultdict(float))
    for g in m["gpumem"]:
        vram[g["componente"]][int(fnum(g["ts"]))] += fnum(g["used_mib"]) or 0
    for comp, porseg in vram.items():
        ys = []
        for a, b in vent:
            v = [porseg[s] for s in range(a, b) if s in porseg]
            ys.append(media(v))
        series[(comp, "vram", "MiB")] = ys
    # Jobs del agente: cantidad de procesos y PSS medio por job.
    jobs = defaultdict(list)
    for p in m["procmem"]:
        if p["componente"] == "agent" and p["rol"] == "job" and fnum(p["pss_mb"]) is not None:
            jobs[int(fnum(p["ts"]))].append(fnum(p["pss_mb"]))
    filas = []
    for (comp, tipo, unidad), ys in sorted(series.items()):
        fit = recta(xs, ys)
        if not fit:
            continue
        a_, b_, r2 = fit
        esc = 1024 if unidad == "GB" else 1
        mx = max(y for y in ys if y is not None)
        # Sin relacion con las llamadas (r2 bajo) o pendiente despreciable: no
        # escala; se proyecta el maximo observado en vez de extrapolar ruido.
        escala = r2 >= R2_MIN and b_ * esc >= 1.0
        filas.append({"componente": comp, "medida": tipo, "unidad": unidad, "escala": escala,
                      "base": r(a_ if escala else mx, 3), "por_llamada_mb": r(b_ * esc, 2) if escala else 0.0,
                      "r2": r(r2, 3), "max": r(mx, 3),
                      "proyeccion_64": r(a_ + b_ * 64 if escala else mx, 3),
                      "proyeccion_128": r(a_ + b_ * 128 if escala else mx, 3)})
    pj = [v for vs in jobs.values() for v in vs]
    return {"ventanas": len(vent), "concurrencia_max": max(xs) if xs else 0, "filas": filas,
            "agente_job_pss_mb_p50": r(pct(pj, .5), 1), "agente_job_pss_mb_p95": r(pct(pj, .95), 1),
            "agente_jobs_max": max((len(v) for v in jobs.values()), default=None)}


# ---------- ventanas de 30 s (serie para el reporte) ----------

def ventanas(R: Run) -> list[dict]:
    out = []
    perfil = R.perfil
    for a in range(int(R.t_min), int(R.t_max), VENTANA_S):
        b = a + VENTANA_S
        ts = [t for t in R.turns if t["t_fin_envio"] and a <= t["t_fin_envio"] < b]
        cm, _ = R.conc_media(a, b)
        f = {"desde": a, "concurrencia": r(cm, 1), "turnos": len(ts),
             "espera_p50": r(pct([t["espera_s"] for t in ts], .5)), "espera_p95": r(pct([t["espera_s"] for t in ts], .95)),
             "sin_respuesta": sum(1 for t in ts if t["espera_s"] is None)}
        if R.mon_data:
            m = R.mon_data
            f["cpu_host"] = r(media([fnum(s["total_busy_pct"]) for s in R.en(m["sys"], a, b)]), 1)
            f["agente_cores"] = r(media([fnum(c["cpu_cores"]) for c in R.en(m["cont"], a, b) if c["svc"] == "agent"]), 2)
            for gi in ("0", "1"):
                f[f"gpu{gi}"] = r(media([fnum(g["utilization.gpu"]) for g in R.en(m["gpu"], a, b) if g["index"] == gi]), 1)
            mem = defaultdict(list)
            for x in R.en(m["mem"], a, b):
                mem[x["componente"]].append(fnum(x["mem_gb"]))
            for k, v in mem.items():
                f[f"mem_{k}"] = r(media(v), 2)
        out.append(f)
    return out


# ---------- reporte ----------

def svg_lineas(series: dict[str, list[tuple[float, float]]], titulo: str, ylab: str, w=720, h=260) -> str:
    pts = [p for s in series.values() for p in s if p[1] is not None]
    if not pts:
        return ""
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y1 = max(p[1] for p in pts) * 1.1 or 1
    x1 = x1 if x1 > x0 else x0 + 1
    L, B = 50, 30
    X = lambda x: L + (x - x0) / (x1 - x0) * (w - L - 10)
    Y = lambda y: h - B - y / y1 * (h - B - 20)
    colores = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#be185d", "#65a30d", "#475569", "#ca8a04"]
    g = [f'<text x="{L}" y="14" class="t">{html.escape(titulo)}</text>',
         f'<text x="4" y="{h/2}" class="l" transform="rotate(-90 10 {h/2})">{html.escape(ylab)}</text>']
    for k in range(5):
        yv = y1 * k / 4
        g.append(f'<line x1="{L}" x2="{w-10}" y1="{Y(yv):.1f}" y2="{Y(yv):.1f}" class="g"/>'
                 f'<text x="{L-4}" y="{Y(yv)+4:.1f}" class="a" text-anchor="end">{yv:.3g}</text>')
    for k in range(5):
        xv = x0 + (x1 - x0) * k / 4
        g.append(f'<text x="{X(xv):.1f}" y="{h-10}" class="a" text-anchor="middle">{xv:.3g}</text>')
    for i, (nom, s) in enumerate(series.items()):
        c = colores[i % len(colores)]
        d = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in s if y is not None)
        g.append(f'<polyline points="{d}" fill="none" stroke="{c}" stroke-width="2"/>')
        for x, y in s:
            if y is not None:
                g.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="2.5" fill="{c}"/>')
        g.append(f'<text x="{w-10}" y="{30+i*14}" class="a" text-anchor="end" fill="{c}">{html.escape(nom)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%">{"".join(g)}</svg>'


def tabla(filas: list[dict], cols: list[str]) -> str:
    th = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    tr = "".join("<tr>" + "".join(f"<td>{html.escape('' if f.get(c) is None else str(f.get(c)))}</td>" for c in cols) + "</tr>" for f in filas)
    return f"<table><tr>{th}</tr>{tr}</table>"


def reporte(R: Run, res: dict, mem: dict, vent: list[dict]) -> str:
    s, pasos = res["summary"], res["pasos"]
    nombres = R.perfil["buckets_nombres"] + ["sin_respuesta"]
    x = lambda f: f["concurrencia_real"]
    esperas = svg_lineas({"p50": [(x(f), f["espera_p50"]) for f in pasos], "p95": [(x(f), f["espera_p95"]) for f in pasos]},
                         "Espera percibida contra llamadas simultaneas (reales)", "s")
    etapas = svg_lineas({k: [(x(f), f.get(f"{k}_p50")) for f in pasos] for k in ("eou", "stt", "llm", "tts", "e2e")},
                        "Desglose por etapa (p50, server) contra llamadas simultaneas", "s")
    bk = svg_lineas({n: [(x(f), 100 * f["buckets"].get(n, 0)) for f in pasos] for n in nombres},
                    "% de turnos por bucket contra llamadas simultaneas", "%")
    t0 = vent[0]["desde"] if vent else 0
    linea = svg_lineas({"llamadas": [((v["desde"] - t0) / 60, v["concurrencia"]) for v in vent],
                        "CPU host %": [((v["desde"] - t0) / 60, v.get("cpu_host")) for v in vent],
                        "GPU0 %": [((v["desde"] - t0) / 60, v.get("gpu0")) for v in vent],
                        "GPU1 %": [((v["desde"] - t0) / 60, v.get("gpu1")) for v in vent]},
                       "Linea de tiempo (ventanas de 30 s)", "llamadas / %")
    comps = sorted({k[4:] for v in vent for k in v if k.startswith("mem_")} - {"host"})
    memsvg = svg_lineas({c: [((v["desde"] - t0) / 60, v.get(f"mem_{c}")) for v in vent] for c in comps},
                        "RAM por componente (GB) en el tiempo (min)", "GB")
    cols = ["paso", "concurrencia_obj", "concurrencia_real", "llegadas_min", "turnos", "espera_p50", "espera_p95",
            "espera_p99", "frac_ok", "frac_malo_o_peor", "sin_respuesta", "frac_buenas", "frac_fallas", "saludo_p95",
            "wer", "cortes_por_resp", "cumple_slo", "cliente_sano"]
    cols_r = ["paso", "concurrencia_real", "cpu_host_p95", "agente_cores_prom", "cores_por_llamada", "gpu0_uso", "gpu0_seg95",
              "gpu1_uso", "gpu1_seg95", "llm_cola_ms", "llm_en_vuelo_max", "llm_kv_max", "stt_cola_ms", "tts_entre_tokens_ms",
              "cpu_temp_max", "wh_gpu_por_llamada_min"]
    css = """:root{--bg:#fff;--fg:#111;--mut:#666;--ln:#ddd}@media(prefers-color-scheme:dark){:root{--bg:#111;--fg:#eee;--mut:#999;--ln:#333}}
body{background:var(--bg);color:var(--fg);font:14px system-ui;margin:16px;max-width:1100px}table{border-collapse:collapse;font-size:12px;display:block;overflow-x:auto}
td,th{border:1px solid var(--ln);padding:3px 6px;text-align:right}th{background:rgba(127,127,127,.1)}.t{font-weight:600;fill:var(--fg)}
.a,.l{font-size:11px;fill:var(--mut)}.g{stroke:var(--ln)}h1{font-size:20px}h2{font-size:16px;margin-top:28px}code{font-size:12px}"""
    ficha = {k: s[k] for k in ("hw_id", "config_id", "hw_id_cliente", "perfil", "perfil_version", "workflow", "piso_p50",
                               "duracion_llamada_s", "capacidad_simultaneas", "capacidad_por_min", "capacidad_por_umbral_p95",
                               "codo_concurrencia", "cuello", "cores_por_llamada", "wh_gpu_por_llamada_min", "llamadas_por_gpu")}
    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>Capacidad {html.escape(s['run'])}</title><style>{css}</style>
<h1>Test de capacidad: {html.escape(s['run'])}</h1>
<h2>Ficha de capacidad</h2><pre>{html.escape(json.dumps(ficha, indent=1, ensure_ascii=False))}</pre>
{esperas}{bk}{etapas}
<h2>Calidad por escalon</h2>{tabla(pasos, cols)}
<h2>Recursos por escalon</h2>{tabla(pasos, cols_r)}
{linea}
<h2>Memoria: como escala con las llamadas</h2>
<p>Recta por componente sobre {mem.get('ventanas', 0)} ventanas de 30 s: memoria = base + MB por llamada x llamadas simultaneas.
Jobs del agente: PSS p50 {mem.get('agente_job_pss_mb_p50')} MB, p95 {mem.get('agente_job_pss_mb_p95')} MB, hasta {mem.get('agente_jobs_max')} procesos.</p>
{tabla(mem.get('filas', []), ['componente', 'medida', 'unidad', 'escala', 'base', 'por_llamada_mb', 'r2', 'max', 'proyeccion_64', 'proyeccion_128'])}
{memsvg}
</html>"""


def markdown(res: dict, mem: dict) -> str:
    s, pasos = res["summary"], res["pasos"]
    L = [f"Capacidad al SLO: {s['capacidad_simultaneas']} simultaneas ({s['capacidad_por_min']}/min). "
         f"Por umbral de p95: {s['capacidad_por_umbral_p95']}. Codo: {s['codo_concurrencia']}. Cuello: {'; '.join(s['cuello']) or '-'}",
         "", "| Paso | Llamadas reales | Espera p50 / p95 | OK | Malo o peor | Sin resp. | Buenas | Fallas | CPU host p95 | Cores/llamada | GPU0 / GPU1 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in pasos:
        L.append(f"| {f['paso']} | {f['concurrencia_real']} | {f['espera_p50']} / {f['espera_p95']} s | {f['frac_ok']} | "
                 f"{f['frac_malo_o_peor']} | {f['sin_respuesta']} | {f['frac_buenas']} | {f['frac_fallas']} | "
                 f"{f.get('cpu_host_p95')} % | {f.get('cores_por_llamada')} | {f.get('gpu0_uso')} / {f.get('gpu1_uso')} % |")
    if mem.get("filas"):
        L += ["", "| Componente | Medida | Base | MB por llamada | r2 | Proyeccion 64 / 128 |", "|---|---|---|---|---|---|"]
        for m in sorted(mem["filas"], key=lambda m: -m["por_llamada_mb"]):
            L.append(f"| {m['componente']} | {m['medida']} ({m['unidad']}) | {m['base']} | {m['por_llamada_mb']} | {m['r2']} | "
                     f"{m['proyeccion_64']} / {m['proyeccion_128']} |")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="directorio del run del cliente (scripts/capacity/runs/...)")
    ap.add_argument("--monitor", type=Path, default=None, help="directorio de monitor.py del server")
    ap.add_argument("--base", type=Path, default=None, help="summary.json de un run `base` (piso de latencia)")
    ap.add_argument("--md", action="store_true", help="imprimir tablas markdown para el registro")
    a = ap.parse_args()
    R = Run(a.run, a.monitor, a.base)
    res = analizar(R)
    mem = memoria(R)
    res["summary"]["memoria"] = mem
    vent = ventanas(R)
    (a.run / "summary.json").write_text(json.dumps(res["summary"], indent=1, ensure_ascii=False))
    for nombre, filas in (("steps.csv", res["pasos"]), ("windows.csv", vent), ("memoria.csv", mem.get("filas", []))):
        if filas:
            cols = list(dict.fromkeys(k for f in filas for k in f if not isinstance(f[k], dict)))
            with open(a.run / nombre, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(filas)
    (a.run / "report.html").write_text(reporte(R, res, mem, vent))
    s = res["summary"]
    print(f"{s['run']}: capacidad {s['capacidad_simultaneas']} simultaneas, codo {s['codo_concurrencia']}, "
          f"piso p50 {s['piso_p50']} s, duracion media {s['duracion_llamada_s']} s")
    print(f"  cuello: {'; '.join(s['cuello']) or '-'}")
    print(f"  -> {a.run}/summary.json, steps.csv, windows.csv, memoria.csv, report.html")
    if a.md:
        print(markdown(res, mem))


if __name__ == "__main__":
    main()
