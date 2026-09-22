"""Corpus de evaluacion de STT con voces argentinas reales: OpenSLR 61
(Google, es-AR, frases leidas por voluntarios, 48kHz, CC BY-SA 4.0), en las
variantes de canal de channel.py (clean16k, tel8k, tel8k_noise, tel8k_cuts).
Salida en el formato de scripts/stt_eval.py (X.wav + X.txt), una carpeta por
variante.

Toma --per-gender frases por genero, repartidas en ronda entre todos los
hablantes (31 mujeres y 13 hombres), y saltea las que tienen digitos
("5" contra "cinco" contaria como error). Es determinista: misma --seed,
mismo corpus.

No baja los zips (1.8GB): los lee por HTTP con rangos y trae solo los .wav
elegidos, que quedan cacheados en <out>/_src/.

Uso: make stt-corpus [ARGS="--per-gender 150 --snr 10 --loss 0.05 --burst 2"]
     make stt-eval ARGS="--audio-dir scripts/stt_corpus/data/openslr61/tel8k --runs 1"
"""
import argparse
import csv
import io
import random
import re
import zipfile
from pathlib import Path

import httpx

from scripts.stt_corpus import channel

BASE_URL = "https://www.openslr.org/resources/61"
GENDERS = {"f": "female", "m": "male"}
OUT_DIR = Path(__file__).resolve().parent / "data" / "openslr61"


class _HttpRangeFile(io.RawIOBase):
    """Archivo remoto de solo lectura con seek, via HTTP Range: zipfile lee
    el directorio central del final del zip y despues solo los miembros
    pedidos."""

    def __init__(self, client: httpx.Client, url: str):
        self._client, self._url, self._pos = client, url, 0
        self._size = int(client.head(url).headers["content-length"])

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        self._pos = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}[whence] + offset
        return self._pos

    def readinto(self, buf) -> int:
        if self._pos >= self._size:
            return 0
        end = min(self._pos + len(buf), self._size) - 1
        r = self._client.get(self._url, headers={"Range": f"bytes={self._pos}-{end}"})
        r.raise_for_status()
        data = r.content
        buf[:len(data)] = data
        self._pos += len(data)
        return len(data)


def load_index(client: httpx.Client) -> dict[str, dict[str, list[tuple[str, str]]]]:
    """{genero: {hablante: [(utt, texto)]}}, sin las frases con digitos."""
    index = {}
    for g, name in GENDERS.items():
        by_speaker = index.setdefault(g, {})
        for line in client.get(f"{BASE_URL}/line_index_{name}.tsv").text.splitlines():
            utt, text = line.split("\t", 1)
            if not re.search(r"\d", text):
                by_speaker.setdefault(utt.split("_")[1], []).append((utt, text.strip()))
    return index


def _select(index: dict, per_gender: int, seed: int) -> list[dict]:
    """Frases elegidas: en ronda por hablante, asi entran todos."""
    rng = random.Random(seed)
    chosen = []
    for g in GENDERS:
        queues = [rng.sample(v, len(v)) for _, v in sorted(index[g].items())]
        rng.shuffle(queues)
        picked = []
        while len(picked) < per_gender and any(queues):
            for q in queues:
                if q and len(picked) < per_gender:
                    picked.append(q.pop())
        chosen += [{"utt": u, "gender": g, "speaker": u.split("_")[1], "text": t} for u, t in picked]
    return chosen


def fetch(client: httpx.Client, rows: list[dict], src_dir: Path) -> None:
    """Baja a src_dir los .wav de rows (dicts con utt y gender) que falten."""
    src_dir.mkdir(parents=True, exist_ok=True)
    for g, name in GENDERS.items():
        missing = {r["utt"] for r in rows if r["gender"] == g and not (src_dir / f"{r['utt']}.wav").exists()}
        if not missing:
            continue
        print(f"bajando {len(missing)} audios de es_ar_{name}.zip (por rangos)...", flush=True)
        remote = io.BufferedReader(_HttpRangeFile(client, f"{BASE_URL}/es_ar_{name}.zip"), buffer_size=1 << 20)
        with zipfile.ZipFile(remote) as z:
            for info in z.infolist():
                utt = Path(info.filename).stem
                if utt in missing:
                    (src_dir / f"{utt}.wav").write_bytes(z.read(info))
                    missing.discard(utt)
        if missing:
            raise SystemExit(f"no estan en el zip: {sorted(missing)[:5]}...")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--per-gender", type=int, default=150, help="frases por genero (default 150)")
    p.add_argument("--out", type=Path, default=OUT_DIR)
    channel.add_args(p)
    args = p.parse_args()

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        rows = _select(load_index(client), args.per_gender, args.seed)
        fetch(client, rows, args.out / "_src")

    for r in rows:
        x, sr = channel.read_wav(args.out / "_src" / f"{r['utt']}.wav")
        r.update(channel.write_variants(x, sr, args.out, r["utt"], r["text"], args))

    with open(args.out / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["utt", "gender", "speaker", "duration_s", "lost_packets", "cuts", "text"])
        w.writeheader()
        w.writerows(rows)
    by_g = {g: sum(r["gender"] == g for r in rows) for g in GENDERS}
    speakers = {g: len({r["speaker"] for r in rows if r["gender"] == g}) for g in GENDERS}
    hours = sum(r["duration_s"] for r in rows) / 3600
    print(f"listo: {len(rows)} frases ({by_g['f']} mujer / {by_g['m']} hombre, "
          f"{speakers['f']} / {speakers['m']} hablantes, {hours:.2f} h) x {len(channel.VARIANTS)} variantes en {args.out}")
    print(channel.summary(rows, args))


if __name__ == "__main__":
    main()
