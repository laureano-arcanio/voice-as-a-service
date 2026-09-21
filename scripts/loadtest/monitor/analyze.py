#!/usr/bin/env python3
"""Resumen de un run del sampler. Uso: analyze.py <rundir> [t0 t1]"""
import csv, json, sys, collections, statistics as st
R = sys.argv[1]
T0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0
T1 = float(sys.argv[3]) if len(sys.argv) > 3 else 9e18
def q(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))] if v else 0
def desc(v): return f"avg={st.mean(v):7.2f} p50={q(v,.5):7.2f} p95={q(v,.95):7.2f} max={max(v):7.2f}" if v else "n/a"
def rows(n): return [r for r in csv.DictReader(open(f"{R}/{n}")) if T0 <= float(r["ts"]) <= T1]

# ventana activa = segundos con requests in-flight
vl = [json.loads(l) for l in open(f"{R}/vllm.jsonl")]
vl = [r for r in vl if T0 <= r["ts"] <= T1]
infl = collections.defaultdict(float); ptok = {}
for r in vl:
    tok = sum(v for k, v in r.items() if "tokens_total" in k)
    infl[round(r["ts"])] += tok != ptok.get(r["svc"], tok); ptok[r["svc"]] = tok
busy = sorted(t for t, v in infl.items() if v > 0)
# activo = a <=5s de un segundo con avance de tokens (tapa huecos entre turnos)
act = {t for t in infl if any(abs(t - b) <= 5 for b in busy)} if len(busy) < 5000 else set(infl)
A = lambda r: round(float(r["ts"])) in act
print(f"ventana: {len(infl)}s muestreados, {len(act)}s activos\n")

print("== HOST CPU (solo segundos activos)")
s = [r for r in rows("sys.csv") if A(r)]
for k in ("total_busy_pct", "cores_gt90", "cores_gt50", "load1", "iowait_pct", "mem_used_gb", "swap_used_gb"):
    print(f"  {k:16s} {desc([float(r[k]) for r in s])}")
ncpu = len([k for k in s[0] if k.startswith("cpu")]) if s else 0
print("  por cpu logico (avg/p95): " + " ".join(f"{i}:{st.mean([float(r[f'cpu{i}']) for r in s]):.0f}/{q([float(r[f'cpu{i}']) for r in s],.95):.0f}" for i in range(ncpu)))

print("\n== CONTENEDORES (cores = CPUs logicas equivalentes)")
c = collections.defaultdict(list)
for r in rows("cont.csv"):
    if A(r): c[r["svc"]].append(r)
for svc, v in c.items():
    print(f"  {svc:10s} cpu   {desc([float(r['cpu_cores']) for r in v])}  sys%={100*sum(float(r['sys_cores']) for r in v)/max(1e-9,sum(float(r['cpu_cores']) for r in v)):.0f}")
    print(f"  {'':9s} runT  {desc([float(r['running_threads']) for r in v])}  nthreads={v[-1]['nthreads']}")
    print(f"  {'':9s} memGB {desc([float(r['mem_gb']) for r in v])}  anon_max={max(float(r['anon_gb']) for r in v):.2f}")

print("\n== THREADS (por svc/comm: nro de threads distintos, suma de cores)")
th = collections.defaultdict(lambda: collections.defaultdict(float)); tids = collections.defaultdict(set); hot = collections.defaultdict(list)
nsec = max(1, len(act))
for r in rows("threads.csv"):
    if not A(r): continue
    k = (r["svc"], r["comm"]); p = float(r["cpu_pct"])
    th[k][round(float(r["ts"]))] += p / 100; tids[k].add(r["tid"]); hot[(r["svc"], r["comm"], r["tid"])].append(p)
for k, d in sorted(th.items(), key=lambda x: -sum(x[1].values()))[:25]:
    v = list(d.values()) + [0] * (nsec - len(d))
    print(f"  {k[0]:10s} {k[1]:16s} tids={len(tids[k]):3d} cores {desc(v)}")
print("  -- threads individuales mas calientes (posible cuello single-thread):")
for k, v in sorted(hot.items(), key=lambda x: -sum(x[1]))[:12]:
    vv = v + [0] * (nsec - len(v))
    print(f"  {k[0]:10s} {k[1]:16s} tid={k[2]:8s} avg={st.mean(vv):5.1f}% p95={q(vv,.95):5.1f}% secs>=90%={sum(x>=90 for x in v)}")

print("\n== GPU")
g = collections.defaultdict(list)
for r in rows("gpu.csv"):
    if A(r): g[r["index"]].append(r)
for i, v in g.items():
    print(f"  GPU{i} util%  {desc([float(r['utilization.gpu']) for r in v])}  secs>=95%: {sum(float(r['utilization.gpu'])>=95 for r in v)}/{len(v)}")
    print(f"       membw% {desc([float(r['utilization.memory']) for r in v])}")
    print(f"       memMiB {desc([float(r['memory.used']) for r in v])}")
    print(f"       powerW {desc([float(r['power.draw']) for r in v])}  tempmax={max(float(r['temperature.gpu']) for r in v):.0f}C throttle={sorted({r['clocks_throttle_reasons.active'] for r in v})}")
pm = collections.defaultdict(lambda: [[], []])
try:
    for l in open(f"{R}/gpu_pmon.log"):
        f = l.split()
        if l.startswith("#") or len(f) < 12 or f[4] == "-": continue
        pm[(f[1], f[2], f[-1])][0].append(float(f[4])); pm[(f[1], f[2], f[-1])][1].append(float(f[10]))
    print("  por proceso (toda la corrida, sm%):")
    for k, (sm, fb) in sorted(pm.items()):
        print(f"    GPU{k[0]} pid={k[1]:8s} {k[2]:16s} sm {desc(sm)}  fbMB_max={max(fb):.0f}")
except OSError: pass

print("\n== vLLM")
bs = collections.defaultdict(list)
for r in vl: bs[r["svc"]].append(r)
for svc, v in bs.items():
    a, b = v[0], v[-1]; dur = max(1, len(act))
    print(f"  {svc}")
    for k in sorted(a):
        if k.startswith(("num_requests", "kv_cache")) and "by_reason" not in k:
            print(f"    {k:34s} {desc([r.get(k,0) for r in v if round(r['ts']) in act])}")
    for k in sorted(a):
        if k.endswith("_total") or "_total@" in k:
            d = b.get(k, 0) - a[k]
            if d: print(f"    {k:34s} +{d:.0f}  ({d/dur:.1f}/s activo)")
    for k in sorted(a):
        if k.endswith("_seconds_sum") or "_seconds_sum@" in k:
            kc = k.replace("_seconds_sum", "_seconds_count"); n = b.get(kc, 0) - a.get(kc, 0)
            if n > 0: print(f"    {k.replace('_seconds_sum',''):34s} media={(b[k]-a[k])/n*1000:9.1f} ms  n={n:.0f}")
