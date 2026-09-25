#!/usr/bin/env python3
"""Resumen de un run del sampler en una ventana de tiempo (una fase del
loadtest; ubicarlas con timeline.py).

Solo cuenta los segundos "activos": a <=5 s de un segundo con avance de
contadores de tokens en algun vLLM (tapa los huecos entre turnos).

Uso: analyze.py <rundir> [t0 t1] [--md]
  sin --md: reporte completo (host, contenedores, threads, GPU, vLLM)
  con --md: tablas markdown para el registro (docs/archive/experiments/)"""
import csv, json, sys, collections, statistics as st
from datetime import datetime

MD = "--md" in sys.argv
argv = [a for a in sys.argv[1:] if a != "--md"]
R = argv[0]
T0 = float(argv[1]) if len(argv) > 1 else 0
T1 = float(argv[2]) if len(argv) > 2 else 9e18
def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))] if v else 0
def desc(v): return f"avg={st.mean(v):7.2f} p50={q(v,.5):7.2f} p95={q(v,.95):7.2f} max={max(v):7.2f}" if v else "n/a"
def rows(n): return [r for r in csv.DictReader(open(f"{R}/{n}")) if T0 <= float(r["ts"]) <= T1]

vl = [json.loads(l) for l in open(f"{R}/vllm.jsonl")]
vl = [r for r in vl if T0 <= r["ts"] <= T1]
infl = collections.defaultdict(float); ptok = {}
for r in vl:
    tok = sum(v for k, v in r.items() if "tokens_total" in k)
    infl[round(r["ts"])] += tok != ptok.get(r["svc"], tok); ptok[r["svc"]] = tok
busy = sorted(t for t, v in infl.items() if v > 0)
act = {t for t in infl if any(abs(t - b) <= 5 for b in busy)} if len(busy) < 5000 else set(infl)
A = lambda r: round(float(r["ts"])) in act
nsec = max(1, len(act))

# --- carga de datos ------------------------------------------------------
sysr = [r for r in rows("sys.csv") if A(r)]
cont = collections.defaultdict(list)
for r in rows("cont.csv"):
    if A(r): cont[r["svc"]].append(r)
th = collections.defaultdict(lambda: collections.defaultdict(float)); tids = collections.defaultdict(set); hot = collections.defaultdict(list)
for r in rows("threads.csv"):
    if not A(r): continue
    k = (r["svc"], r["comm"]); p = float(r["cpu_pct"])
    th[k][round(float(r["ts"]))] += p / 100; tids[k].add(r["tid"]); hot[(r["svc"], r["comm"], r["tid"])].append(p)
# Procesos con >=20% de un core (runs desde 2026-09-22); "ajeno:*" = fuera del stack.
prc = collections.defaultdict(list)
try:
    for r in rows("procs.csv"):
        if A(r): prc[(r["comm"], r["cgroup"])].append(float(r["cpu_pct"]))
except OSError:
    pass
ext = sorted(((k, v + [0] * (nsec - len(v))) for k, v in prc.items() if k[1].startswith("ajeno:")), key=lambda x: -q(x[1], .95))
gpu = collections.defaultdict(list)
for r in rows("gpu.csv"):
    if A(r): gpu[r["index"]].append(r)

# nvidia-smi pmon: "-o T" (runs viejos, solo hora) o "-o DT" (fecha + hora).
pm = collections.defaultdict(lambda: [[], []])
day = datetime.fromtimestamp(min(act) if act else T0).strftime("%Y%m%d")
try:
    cols = None
    for l in open(f"{R}/gpu_pmon.log"):
        f = l.split()
        if l.startswith("#"):
            cols = cols or l.lstrip("#").lower().split()
            continue
        if not cols or len(f) < len(cols): continue
        c = {n: f[i] for i, n in enumerate(cols[:-1])}
        t = round(datetime.strptime(c.get("date", day) + c["time"], "%Y%m%d%H:%M:%S").timestamp())
        if t not in act or c["sm"] == "-": continue
        k = (c["gpu"], c["pid"], " ".join(f[len(cols) - 1:]))
        pm[k][0].append(float(c["sm"])); pm[k][1].append(float(c["fb"]))
except (OSError, ValueError):
    pass

vs = collections.defaultdict(list)
for r in vl: vs[r["svc"]].append(r)

def rate(v, k):
    return (v[-1].get(k, 0) - v[0].get(k, 0)) / nsec
def mean_ms(v, k):
    kc = k.replace("_seconds_sum", "_seconds_count"); n = v[-1].get(kc, 0) - v[0].get(kc, 0)
    return (v[-1][k] - v[0].get(k, 0)) / n * 1000 if n > 0 else None
def stages(v):
    """Stages de vLLM-Omni (TTS: s0 = talker, s1 = Code2Wav); [""] si no tiene."""
    return sorted({p for k in v[0] for p in k.split("@")[1:] if p[1:].isdigit() and p[0] == "s"}) or [""]
def key(base, s):
    return base + (f"@{s}" if s else "")

if MD:
    f = lambda x, d=0: "—" if x is None else f"{x:.{d}f}"
    print(f"Ventana `{T0:.0f}`–`{T1:.0f}`: {nsec} s activos.\n")
    print("| Servicio | req/s | TTFT ms | entre tokens ms | inferencia ms | cola ms | en vuelo prom / máx | KV máx % | preempt. |")
    print("|---|---|---|---|---|---|---|---|---|")
    for svc, v in vs.items():
        for s in stages(v):
            infl_ = [r.get(key("num_requests_running", s), 0) + r.get(key("num_requests_waiting", s), 0) for r in v if round(r["ts"]) in act]
            ok = sum(rate(v, k) for k in v[0] if k.startswith(key("request_success_total", s) + "@"))
            kv = [r.get(key("kv_cache_usage_perc", s), 0) for r in v if round(r["ts"]) in act]
            pre = v[-1].get(key("num_preemptions_total", s), 0) - v[0].get(key("num_preemptions_total", s), 0)
            print(f"| {svc}{' ' + s if s else ''} | {ok:.1f} | {f(mean_ms(v, key('time_to_first_token_seconds_sum', s)))} "
                  f"| {f(mean_ms(v, key('inter_token_latency_seconds_sum', s)), 1)} | {f(mean_ms(v, key('request_inference_time_seconds_sum', s)))} "
                  f"| {f(mean_ms(v, key('request_queue_time_seconds_sum', s)))} | {st.mean(infl_) if infl_ else 0:.1f} / {max(infl_, default=0):.0f} "
                  f"| {100 * max(kv, default=0):.0f} | {pre:.0f} |")
    print("\n| GPU | uso prom. | seg. ≥95% | VRAM máx MiB | potencia prom. / máx W | temp. máx | procesos (sm% prom., VRAM MiB) |")
    print("|---|---|---|---|---|---|---|")
    for i, v in gpu.items():
        u = [float(r["utilization.gpu"]) for r in v]; pw = [float(r["power.draw"]) for r in v]
        procs = ", ".join(f"{k[2]} {st.mean(sm):.0f}% {max(fb):.0f}" for k, (sm, fb) in sorted(pm.items(), key=lambda x: -max(x[1][1])) if k[0] == i and st.mean(sm) >= 3)
        print(f"| {i} | {st.mean(u):.0f}% | {100 * sum(x >= 95 for x in u) / len(u):.0f}% | {max(float(r['memory.used']) for r in v):.0f} "
              f"| {st.mean(pw):.0f} / {max(pw):.0f} | {max(float(r['temperature.gpu']) for r in v):.0f} °C | {procs} |")
    if sysr:
        print(f"\nHost: CPU {st.mean(float(r['total_busy_pct']) for r in sysr):.0f}% prom. / {max(float(r['total_busy_pct']) for r in sysr):.0f}% máx; "
              f"cores >90%: máx {max(int(r['cores_gt90']) for r in sysr)}; RAM usada máx {max(float(r['mem_used_gb']) for r in sysr):.1f} GB; "
              f"swap máx {max(float(r['swap_used_gb']) for r in sysr):.1f} GB"
              + (f"; proceso ajeno más cargado: {ext[0][0][0]} ({ext[0][0][1][6:]}) p95 {q(ext[0][1], .95):.0f}% de un core" if ext else "") + ".\n")
    print("| Contenedor | CPU cores p95 / máx | RAM máx GB | thread más cargado (p95 % de un core) |")
    print("|---|---|---|---|")
    for svc in vs:
        v = cont.get(svc)
        if not v: continue
        c = [float(r["cpu_cores"]) for r in v]
        h = [(k, x + [0] * (nsec - len(x))) for k, x in hot.items() if k[0] == svc]
        hk, hv = max(h, key=lambda y: q(y[1], .95), default=(("", "-", ""), [0]))
        print(f"| {svc} | {q(c, .95):.2f} / {max(c):.2f} | {max(float(r['mem_gb']) for r in v):.1f} | {hk[1]} {q(hv, .95):.0f}% |")
    sys.exit()

# --- reporte completo ------------------------------------------------------
print(f"ventana: {len(infl)}s muestreados, {len(act)}s activos\n")
print("== HOST CPU (solo segundos activos)")
for k in ("total_busy_pct", "cores_gt90", "cores_gt50", "load1", "iowait_pct", "mem_used_gb", "swap_used_gb"):
    print(f"  {k:16s} {desc([float(r[k]) for r in sysr])}")
ncpu = len([k for k in sysr[0] if k.startswith("cpu")]) if sysr else 0
print("  por cpu logico (avg/p95): " + " ".join(f"{i}:{st.mean([float(r[f'cpu{i}']) for r in sysr]):.0f}/{q([float(r[f'cpu{i}']) for r in sysr],.95):.0f}" for i in range(ncpu)))

print("\n== CONTENEDORES (cores = CPUs logicas equivalentes)")
for svc, v in cont.items():
    print(f"  {svc:13s} cpu   {desc([float(r['cpu_cores']) for r in v])}  sys%={100*sum(float(r['sys_cores']) for r in v)/max(1e-9,sum(float(r['cpu_cores']) for r in v)):.0f}")
    print(f"  {'':13s} runT  {desc([float(r['running_threads']) for r in v])}  nthreads={v[-1]['nthreads']}")
    print(f"  {'':13s} memGB {desc([float(r['mem_gb']) for r in v])}  anon_max={max(float(r['anon_gb']) for r in v):.2f}")

print("\n== THREADS (por svc/comm: nro de threads distintos, suma de cores)")
for k, d in sorted(th.items(), key=lambda x: -sum(x[1].values()))[:25]:
    v = list(d.values()) + [0] * (nsec - len(d))
    print(f"  {k[0]:13s} {k[1]:16s} tids={len(tids[k]):3d} cores {desc(v)}")
print("  -- threads individuales mas calientes (posible cuello single-thread):")
for k, v in sorted(hot.items(), key=lambda x: -sum(x[1]))[:12]:
    vv = v + [0] * (nsec - len(v))
    print(f"  {k[0]:13s} {k[1]:16s} tid={k[2]:8s} avg={st.mean(vv):5.1f}% p95={q(vv,.95):5.1f}% secs>=90%={sum(x>=90 for x in v)}")

if prc:
    print("  -- procesos del host >=20% de un core (ajeno:* = fuera del stack):")
    for k, v in sorted(prc.items(), key=lambda x: -sum(x[1]))[:10]:
        vv = v + [0] * (nsec - len(v))
        print(f"  {k[0]:16s} {k[1][:40]:40s} avg={st.mean(vv):5.1f}% p95={q(vv,.95):5.1f}% max={max(v):5.1f}%")

print("\n== GPU")
for i, v in gpu.items():
    print(f"  GPU{i} util%  {desc([float(r['utilization.gpu']) for r in v])}  secs>=95%: {sum(float(r['utilization.gpu'])>=95 for r in v)}/{len(v)}")
    print(f"       membw% {desc([float(r['utilization.memory']) for r in v])}")
    print(f"       memMiB {desc([float(r['memory.used']) for r in v])}")
    print(f"       powerW {desc([float(r['power.draw']) for r in v])}  tempmax={max(float(r['temperature.gpu']) for r in v):.0f}C throttle={sorted({r['clocks_throttle_reasons.active'] for r in v})}")
if pm:
    print("  por proceso (segundos activos, sm%):")
    for k, (sm, fb) in sorted(pm.items()):
        print(f"    GPU{k[0]} pid={k[1]:8s} {k[2]:16s} sm {desc(sm)}  fbMB_max={max(fb):.0f}")

print("\n== vLLM")
for svc, v in vs.items():
    a, b = v[0], v[-1]
    print(f"  {svc}")
    for k in sorted(a):
        if k.startswith(("num_requests", "kv_cache")) and "by_reason" not in k:
            print(f"    {k:34s} {desc([r.get(k,0) for r in v if round(r['ts']) in act])}")
    for k in sorted(a):
        if k.endswith("_total") or "_total@" in k:
            d = b.get(k, 0) - a[k]
            if d: print(f"    {k:34s} +{d:.0f}  ({d/nsec:.1f}/s activo)")
    for k in sorted(a):
        if k.endswith("_seconds_sum") or "_seconds_sum@" in k:
            m = mean_ms(v, k)
            if m is not None:
                kc = k.replace("_seconds_sum", "_seconds_count")
                print(f"    {k.replace('_seconds_sum',''):34s} media={m:9.1f} ms  n={b.get(kc,0)-a.get(kc,0):.0f}")
