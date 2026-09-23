"""Puntua carpetas de gen.py --set eval (ver docs/TTS_FINETUNE.md).

Incluye la grabacion real de las frases de eval como fila "real" (techo de similitud).

- WER: Qwen3-ASR-1.7B contra el texto pedido (minusculas, sin tildes ni puntuacion).
- Similitud de voz: coseno entre el embedding del speaker encoder de Qwen3-TTS-1.7B-Base
  y el centroide de las grabaciones reales de train de la misma voz. Ojo: es el mismo
  encoder que da el embedding del checkpoint, favorece al fine-tuning.
- Velocidad: caracteres por segundo de audio.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

import librosa
import numpy as np
import torch
from num2words import num2words
from qwen_asr import Qwen3ASRModel
from qwen_tts import Qwen3TTSModel

from common import ASR, TTS_BASE, local_model


def _num(m):
    return " " + num2words(int(m.group(0).replace(".", "")), lang="es") + " "


def norm(s):
    # el ASR escribe numeros con digitos ("42.500"); el texto pedido los tiene en palabras
    s = re.sub(r"\d{1,3}(?:\.\d{3})+|\d+", _num, s)
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9ñ ]+", " ", s).split()


def wer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)], len(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tts-base", default=TTS_BASE["1.7B"], help="da el speaker encoder")
    ap.add_argument("--asr", default=ASR)
    ap.add_argument("--data", required=True)
    ap.add_argument("--dirs", nargs="+", required=True, help="carpetas de gen.py como nombre=ruta")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = Path(args.data)

    tts = Qwen3TTSModel.from_pretrained(local_model(args.tts_base), device_map="cuda:0", dtype=torch.bfloat16)

    def emb(path):
        y, _ = librosa.load(path, sr=24000, mono=True)
        with torch.inference_mode():
            e = tts.model.extract_speaker_embedding(audio=y.astype(np.float32), sr=24000).float().cpu().numpy()
        return e / np.linalg.norm(e)

    train = [json.loads(l) for l in open(data / "train_raw.jsonl", encoding="utf-8")]
    centroid = np.mean([emb(r["audio"]) for r in train], axis=0)
    centroid /= np.linalg.norm(centroid)

    evals = [json.loads(l) for l in open(data / "eval.jsonl", encoding="utf-8")]
    systems = {"real": [{"name": r["utt"], "text": r["text"], "path": r["audio"]} for r in evals]}
    for spec in args.dirs:
        name, d = spec.split("=", 1)
        meta = json.loads((Path(d) / "meta.json").read_text(encoding="utf-8"))
        systems[name] = [{"name": m["name"], "text": m["text"], "path": str(Path(d) / f"{m['name']}.wav")} for m in meta]

    for items in systems.values():
        for it in items:
            it["sim"] = float(emb(it["path"]) @ centroid)
            it["dur"] = librosa.get_duration(path=it["path"])
    del tts
    torch.cuda.empty_cache()

    asr = Qwen3ASRModel.from_pretrained(local_model(args.asr), dtype=torch.bfloat16, device_map="cuda:0")
    for items in systems.values():
        res = asr.transcribe(audio=[it["path"] for it in items], language="Spanish")
        for it, r in zip(items, res):
            it["hyp"] = r.text
            it["err"], it["nw"] = wer(it["text"], r.text)

    lines = ["| Sistema | Grupo | N | WER | Sim. voz | Car./s |", "|---|---|---|---|---|---|"]
    for name, items in systems.items():
        for grp, sel in (("eval", [i for i in items if not i["name"].startswith("dom_")]),
                         ("dominio", [i for i in items if i["name"].startswith("dom_")])):
            if not sel:
                continue
            w = sum(i["err"] for i in sel) / sum(i["nw"] for i in sel)
            sim = np.mean([i["sim"] for i in sel])
            cps = sum(len(i["text"]) for i in sel) / sum(i["dur"] for i in sel)
            lines.append(f"| {name} | {grp} | {len(sel)} | {w*100:.1f}% | {sim:.3f} | {cps:.1f} |")
    table = "\n".join(lines)
    print(table)
    Path(args.out).write_text(json.dumps(systems, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(args.out).with_suffix(".md").write_text(table + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
