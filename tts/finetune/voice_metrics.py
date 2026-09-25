"""Metricas por voz del checkpoint servido, para voces.tsv (sirven de filtro al elegir voz).

Lee los score_<ckpt>.json que deja score.py (work/eval/<id>/eval/) y, por voz, junta todas
las semillas de un sistema (ej. multi41_ep2_s0, _s1). Recalcula el WER con el wer() actual
de score.py sin volver a correr el ASR (usa las transcripciones guardadas).

- wer: WER de las 24 frases de dominio, en %.
- car_s: caracteres por segundo en esas frases (grabacion real de OpenSLR: 14 a 21).

Uso: GPU=none ./run.sh python /code/voice_metrics.py --system multi41_ep2 --out /work/voces.tsv
     y copiar work/voces.tsv sobre voces.tsv (/code es de solo lectura).
"""
import argparse
import csv
import json
import re
from pathlib import Path

from score import wer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="/code/voces.tsv")
    ap.add_argument("--eval", default="/work/eval")
    ap.add_argument("--score", default="score_multi41.json", help="nombre del json de score.py por voz")
    ap.add_argument("--system", required=True, help="prefijo del sistema, sin _s<semilla>")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.catalog, encoding="utf-8"), delimiter="\t"))
    pat = re.compile(re.escape(args.system) + r"_s\d+$")
    for r in rows:
        systems = json.loads((Path(args.eval) / r["openslr"] / "eval" / args.score).read_text(encoding="utf-8"))
        items = [i for name, its in systems.items() if pat.match(name) for i in its if i["name"].startswith("dom_")]
        if not items:
            raise SystemExit(f"{r['nombre']}: no hay {args.system}_s* en {args.score}")
        err, nw = map(sum, zip(*(wer(i["text"], i["hyp"]) for i in items)))
        r["wer"] = f"{err / nw * 100:.1f}"
        r["car_s"] = f"{sum(len(i['text']) for i in items) / sum(i['dur'] for i in items):.1f}"
        print(f"{r['nombre']:<10} {r['openslr']}  WER {r['wer']:>4}%  {r['car_s']} car/s  ({len(items)} frases)")

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["nombre", "openslr", "genero", "wer", "car_s"], delimiter="\t",
                           lineterminator="\n")
        w.writeheader()
        w.writerows({k: r[k] for k in w.fieldnames} for r in rows)


if __name__ == "__main__":
    main()
