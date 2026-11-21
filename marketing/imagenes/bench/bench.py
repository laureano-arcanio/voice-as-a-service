#!/usr/bin/env python3
"""Benchmark de /v1/images/generations: guarda imagen, tiempos y metricas.

Uso: python bench.py --size 512x512 --steps 12 [--seed 1234] [--tag nombre]
Requiere el server de scratch/vllm-omni-qwen21/run.sh en :8210.
"""
import argparse, base64, json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(REPO, "scratch", "imagenes-bench")

ap = argparse.ArgumentParser()
ap.add_argument("--size", default="512x512")
ap.add_argument("--steps", type=int, default=12)
ap.add_argument("--seed", type=int, default=1234)
ap.add_argument("--tag", default=None)
ap.add_argument("--url", default="http://127.0.0.1:8210/v1/images/generations")
ap.add_argument("--model", default="/models/Qwen-Image-2.1")
ap.add_argument("--outdir", default=OUT)
args = ap.parse_args()

prompt = open(os.path.join(HERE, "prompt.txt")).read().strip()
tag = args.tag or f"{args.size.replace('x','-')}_{args.steps}st_s{args.seed}"

body = json.dumps({
    "model": args.model, "prompt": prompt, "size": args.size, "n": 1,
    "response_format": "b64_json", "num_inference_steps": args.steps,
    "seed": args.seed, "return_stage_metrics": True,
}).encode()

req = urllib.request.Request(args.url, data=body, headers={"Content-Type": "application/json"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=600) as r:
    out = json.loads(r.read())
wall = time.time() - t0

os.makedirs(os.path.join(args.outdir, "img"), exist_ok=True)
img = os.path.join(args.outdir, "img", tag + ".png")
open(img, "wb").write(base64.b64decode(out["data"][0]["b64_json"]))
m = out.get("metrics") or {}
sm = (m.get("stage_metrics") or {}).get("0", {})
row = {
    "tag": tag, "size": args.size, "steps": args.steps, "seed": args.seed,
    "wall_s": round(wall, 2),
    "gen_ms": round(m.get("stage_durations", {}).get("stage_0_gen_ms", 0)),
    "step_ms": round(sm.get("denoise_step_latency_ms", 0)),
    "peak_mb": m.get("peak_memory_mb"),
}
csv = os.path.join(args.outdir, "results.csv")
new = not os.path.exists(csv)
with open(csv, "a") as f:
    if new:
        f.write(",".join(row) + "\n")
    f.write(",".join(str(v) for v in row.values()) + "\n")
print(json.dumps(row))
