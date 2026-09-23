"""Dataset de fine-tuning de Qwen3-TTS para una voz de OpenSLR 61 (ver docs/TTS_FINETUNE.md).

- Transcripcion: la del dataset (line_index*.tsv), no ASR: es el texto leido, con
  puntuacion y numeros en palabras.
- Audio: 48 kHz -> 24 kHz mono (el entrenamiento exige 24 kHz), limpieza "v2":
  descarta ruidos cortos aislados en los bordes y acorta las pausas internas a --max-gap.
  Muchas grabaciones de OpenSLR terminan con un click 2-3 s despues de la ultima palabra;
  con un recorte simple (v1) el 27% de los clips de arf_03034 quedaba con 1-3 s de
  silencio + click y el modelo aprendio a quedarse callado ~2 s tras las preguntas.
- Separa --n-eval frases que no se entrenan (hay grabacion real para comparar).
- ref.wav: el clip de train mas cercano a 6 s (el speaker embedding sale de ahi).
- Al final reporta cuantos clips quedan con pausas >0,7 s: tiene que ser ~0.

Salida: /work/data/<voz>/{wav24k/, train_raw.jsonl, eval.jsonl, ref.wav, ref.txt}
Uso: ./run.sh python /code/prep.py --speaker arf_03034
"""
import argparse
import json
import random
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from silences import sil

SR = 24000


def clean_v2(y, top_db, max_gap, pad):
    iv = [list(x) for x in librosa.effects.split(y, top_db=top_db, frame_length=1024, hop_length=256)]
    # ruidos cortos (<150 ms) separados >300 ms del resto, en cualquiera de los bordes
    short, far = int(0.15 * SR), int(0.3 * SR)
    while len(iv) > 1 and iv[0][1] - iv[0][0] < short and iv[1][0] - iv[0][1] > far:
        iv.pop(0)
    while len(iv) > 1 and iv[-1][1] - iv[-1][0] < short and iv[-1][0] - iv[-2][1] > far:
        iv.pop()
    half = int(max_gap * SR / 2)
    out = [y[max(0, iv[0][0] - pad):iv[0][0]]]
    for (a, b), (c, _) in zip(iv, iv[1:] + [[None, None]]):
        out.append(y[a:b])
        if c is None:
            break
        gap = y[b:c]
        out.append(gap if len(gap) <= 2 * half else np.concatenate([gap[:half], gap[-half:]]))
    out.append(y[iv[-1][1]:iv[-1][1] + pad])
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/src", help="carpeta con es_ar_female/ y/o es_ar_male/")
    ap.add_argument("--speaker", required=True, help="prefijo de OpenSLR 61, ej. arf_03034")
    ap.add_argument("--out", default="/work/data")
    ap.add_argument("--n-eval", type=int, default=8)
    ap.add_argument("--top-db", type=float, default=40)
    ap.add_argument("--max-gap", type=float, default=0.3, help="pausa interna maxima, s")
    ap.add_argument("--ref-dur", type=float, default=6.0, help="duracion buscada para ref.wav, s")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out) / args.speaker
    wav_dir = out / "wav24k"
    wav_dir.mkdir(parents=True, exist_ok=True)

    texts = {}
    for tsv in src.glob("*/line_index*.tsv"):
        for line in tsv.read_text(encoding="utf-8").splitlines():
            utt, text = line.split("\t", 1)
            if utt.startswith(args.speaker + "_"):
                texts[utt] = (text.strip(), tsv.parent)
    if not texts:
        raise SystemExit(f"no hay frases de {args.speaker} en {src}/*/line_index*.tsv")

    rows, pad = [], int(0.1 * SR)
    for utt, (text, d) in sorted(texts.items()):
        f = d / f"{utt}.wav"
        if not f.exists():
            print(f"falta audio: {utt}")
            continue
        y, _ = librosa.load(f, sr=SR, mono=True)
        y = clean_v2(y, args.top_db, args.max_gap, pad)
        y = y / max(1e-6, np.abs(y).max()) * 0.9
        dst = wav_dir / f"{utt}.wav"
        sf.write(dst, y, SR, subtype="PCM_16")
        rows.append({"utt": utt, "audio": str(dst), "text": text, "dur": len(y) / SR})

    random.Random(0).shuffle(rows)
    ev, tr = rows[: args.n_eval], rows[args.n_eval:]
    ref = min(tr, key=lambda r: abs(r["dur"] - args.ref_dur))
    ref_path = out / "ref.wav"
    ref_path.write_bytes(Path(ref["audio"]).read_bytes())
    (out / "ref.txt").write_text(ref["text"], encoding="utf-8")

    for name, part in (("train_raw.jsonl", tr), ("eval.jsonl", ev)):
        with open(out / name, "w", encoding="utf-8") as fh:
            for r in part:
                fh.write(json.dumps({"audio": r["audio"], "text": r["text"], "ref_audio": str(ref_path),
                                     "utt": r["utt"], "dur": round(r["dur"], 2)}, ensure_ascii=False) + "\n")

    inner = [(sil(r["audio"])[2], r["text"]) for r in tr]
    long_ = sorted([x for x in inner if x[0] > 0.7], reverse=True)
    print(f"{args.speaker}: {len(rows)} frases, train {len(tr)} ({sum(r['dur'] for r in tr)/60:.1f} min), "
          f"eval {len(ev)}, ref {ref['utt']} ({ref['dur']:.1f} s): {ref['text']}")
    print(f"clips de train con pausa interna >0,7 s: {len(long_)}" +
          "".join(f"\n  {p:.2f} s | {t}" for p, t in long_[:5]))


if __name__ == "__main__":
    main()
