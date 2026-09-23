"""Pausas sobre el set "llamada" y pagina para escuchar A/B (ver docs/TTS_FINETUNE.md).

Entrada: carpetas de gen.py --set llamada con nombre <etiqueta>_s<semilla> bajo --root.
- Por oracion: silencio inicial, final y pausa interna mas larga (silences.sil).
- Entre oraciones del mismo turno: final de una + inicio de la siguiente (el agente manda
  una request por oracion y las reproduce seguidas).
Con --a y --b arma <out>/index.html: turnos completos (semilla 0) y las 8 peores pausas de A
contra la misma oracion y semilla en B.

Criterio de aceptacion (datos limpios, medido en arf_03034): pausas internas >0,7 s en
<=1 de 84 oraciones y silencio entre oraciones <1 s en todas.
"""
import argparse
import glob
import json
import os
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

from silences import sil

SENTS = json.load(open(Path(__file__).with_name("eval_llamada.json"), encoding="utf-8"))
TEXT = dict((n, t) for n, t in SENTS)


def load(root, label):
    runs = {}
    for d in sorted(glob.glob(f"{root}/{label}_s*")):
        runs[d.rsplit("_s", 1)[1]] = {n: sil(f"{d}/{n}.wav") for n, _ in SENTS}
    return runs


def stats(runs):
    gaps, inner = [], []
    for r in runs.values():
        gaps += [r[n][1] + r[m][0] for (n, _), (m, _) in zip(SENTS, SENTS[1:]) if n[:3] == m[:3]]
        inner += [v[2] for v in r.values()]
    g, i = np.array(gaps), np.array(inner)
    return dict(n=len(i), n_gap=len(g), gap_p50=np.median(g), gap_max=g.max(), gap_gt1=int((g > 1).sum()),
                in_p50=np.median(i), in_max=i.max(), in_gt07=int((i > 0.7).sum()))


def page(root, a, b, runs, out, table):
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(f"{out}/turnos")
    os.makedirs(f"{out}/peores")
    html = ["<meta charset=utf-8><title>A/B TTS</title><style>body{font-family:sans-serif;max-width:1100px;"
            "margin:24px auto;padding:0 16px}td{padding:6px;vertical-align:top}audio{width:300px}</style>",
            f"<h2>A = {a} / B = {b}</h2><pre>{table}</pre>",
            "<h3>Turnos de la llamada, oraciones seguidas como las reproduce el agente (semilla 0)</h3><table>"]
    for turn in sorted({n[:3] for n, _ in SENTS}):
        row = [f"<tr><td>{' '.join(t for n, t in SENTS if n.startswith(turn))}</td>"]
        for tag, lab in (("A", a), ("B", b)):
            ys = [sf.read(f"{root}/{lab}_s0/{n}.wav") for n, _ in SENTS if n.startswith(turn)]
            f = f"turnos/{turn}_{tag}.wav"
            sf.write(f"{out}/{f}", np.concatenate([y for y, _ in ys]), ys[0][1])
            row.append(f"<td>{tag}<br><audio controls src='{f}'></audio></td>")
        html.append("".join(row) + "</tr>")
    html.append("</table><h3>Peores pausas de A (misma oracion y semilla en B)</h3><table>")
    worst = sorted(((r[n][2], seed, n) for seed, r in runs[a].items() for n, _ in SENTS), reverse=True)[:8]
    for p, seed, n in worst:
        row = [f"<tr><td>{TEXT[n]}<br><small>pausa A {p:.2f} s / B {runs[b][seed][n][2]:.2f} s</small></td>"]
        for tag, lab in (("A", a), ("B", b)):
            f = f"peores/{n}_s{seed}_{tag}.wav"
            shutil.copy(f"{root}/{lab}_s{seed}/{n}.wav", f"{out}/{f}")
            row.append(f"<td>{tag}<br><audio controls src='{f}'></audio></td>")
        html.append("".join(row) + "</tr>")
    html.append("</table>")
    Path(f"{out}/index.html").write_text("\n".join(html), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="carpeta con <etiqueta>_s<semilla>/")
    ap.add_argument("--a", help="etiqueta A (antes)")
    ap.add_argument("--b", help="etiqueta B (despues)")
    ap.add_argument("--out", help="carpeta de la pagina A/B")
    args = ap.parse_args()

    labels = sorted({os.path.basename(d).rsplit("_s", 1)[0] for d in glob.glob(f"{args.root}/*_s*")})
    runs = {lab: load(args.root, lab) for lab in labels}
    lines = ["| Sistema | Semillas | Oraciones | Entre oraciones p50 / max | >1 s | Pausa interna p50 / max | >0,7 s |",
             "|---|---|---|---|---|---|---|"]
    for lab in labels:
        st = stats(runs[lab])
        lines.append(f"| {lab} | {len(runs[lab])} | {st['n']} | {st['gap_p50']:.2f} / {st['gap_max']:.2f} s | "
                     f"{st['gap_gt1']}/{st['n_gap']} | {st['in_p50']:.2f} / {st['in_max']:.2f} s | "
                     f"{st['in_gt07']}/{st['n']} |")
    table = "\n".join(lines)
    print(table)
    Path(args.root, "pauses.md").write_text(table + "\n", encoding="utf-8")
    if args.a and args.b:
        page(args.root, args.a, args.b, runs, args.out or f"{args.root}/ab_{args.a}_vs_{args.b}", table)
        print(f"pagina: {args.out or f'{args.root}/ab_{args.a}_vs_{args.b}'}/index.html")


if __name__ == "__main__":
    main()
