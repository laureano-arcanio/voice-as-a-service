#!/usr/bin/env python3
"""Linea de tiempo de un run del sampler, para ubicar las fases del loadtest
(ej. la tanda de 16 y la de 32) antes de pasarle la ventana a analyze.py.

Por bucket de N s: segundos con trafico (avance de contadores de tokens) y
maximo de requests en vuelo (running + waiting) por servicio vLLM.
Los t0/t1 que imprime son epoch, listos para `analyze.py <run> t0 t1`.

Uso: timeline.py <rundir> [bucket_s=20]"""
import collections, json, sys

R = sys.argv[1]
B = int(sys.argv[2]) if len(sys.argv) > 2 else 20
act = collections.defaultdict(int); ptok = {}
mx = collections.defaultdict(lambda: collections.defaultdict(float))
svcs = []
for l in open(f"{R}/vllm.jsonl"):
    r = json.loads(l); t = round(r["ts"]); s = r["svc"]
    if s not in svcs: svcs.append(s)
    tok = sum(v for k, v in r.items() if "tokens_total" in k)
    act[t] += tok != ptok.get(s, tok); ptok[s] = tok
    mx[t][s] = sum(v for k, v in r.items() if k.startswith(("num_requests_running", "num_requests_waiting")) and "by_reason" not in k)
ts = sorted(act)
print(f"{R}: {ts[0]} -> {ts[-1]} ({ts[-1] - ts[0]} s). Solo buckets con trafico.")
for b in range(ts[0], ts[-1] + 1, B):
    w = [t for t in ts if b <= t < b + B]
    a = sum(act[t] > 0 for t in w)
    if a:
        print(f"t0={b} +{b - ts[0]:5d}s activos={a:2d}/{B} " + " ".join(f"{s}={max(mx[t].get(s, 0) for t in w):.0f}" for s in svcs))
