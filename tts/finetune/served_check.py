"""Verificacion del checkpoint servido por vllm-tts (ver docs/TTS_FINETUNE.md).

Manda las oraciones de eval_llamada.json a /v1/audio/speech (una request por oracion, como
el agente), --reps veces, y mide pausas internas y silencio entre oraciones del mismo turno.
Uso: NET=host GPU=none VLLM_API_KEY=... ./run.sh python /code/served_check.py --voice arf_03034
"""
import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

import numpy as np

from silences import sil

SENTS = json.load(open(Path(__file__).with_name("eval_llamada.json"), encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8103/v1/audio/speech")
    ap.add_argument("--model", default="arf_03034-ft", help="--served-model-name de vllm-tts")
    ap.add_argument("--voice", required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default="/work/served_check")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    key = os.environ.get("VLLM_API_KEY", "not-needed")

    res, t_first = {}, []
    for rep in range(args.reps):
        for n, text in SENTS:
            req = urllib.request.Request(args.url, method="POST", data=json.dumps(
                {"model": args.model, "voice": args.voice, "input": text, "response_format": "wav"}).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            t0 = time.time()
            body = urllib.request.urlopen(req, timeout=60).read()
            t_first.append(time.time() - t0)
            path = f"{args.out}/{n}_r{rep}.wav"
            Path(path).write_bytes(body)
            res[(rep, n)] = sil(path)

    gaps = [res[(r, n)][1] + res[(r, m)][0] for r in range(args.reps)
            for (n, _), (m, _) in zip(SENTS, SENTS[1:]) if n[:3] == m[:3]]
    inner = [v[2] for v in res.values()]
    g, i = np.array(gaps), np.array(inner)
    print(f"{len(i)} oraciones ({args.reps} reps) | entre oraciones p50 {np.median(g):.2f} s, max {g.max():.2f}, "
          f">1 s: {(g > 1).sum()}/{len(g)} | pausa interna p50 {np.median(i):.2f} s, max {i.max():.2f}, "
          f">0,7 s: {(i > 0.7).sum()}/{len(i)} | request completa p50 {np.median(t_first):.2f} s")
    worst = sorted(((v[2], r, n) for (r, n), v in res.items()), reverse=True)[:3]
    for p, r, n in worst:
        print(f"  pausa {p:.2f} s: {n}_r{r}.wav | {dict(SENTS)[n]}")


if __name__ == "__main__":
    main()
