"""Minutos por voz de OpenSLR 61: brutos y con voz (recorte de silencios de punta), para elegir voz.

Uso: GPU=none ./run.sh python /code/voice_minutes.py
"""
import collections, glob, os
from concurrent.futures import ProcessPoolExecutor
import librosa

def one(f):
    y, sr = librosa.load(f, sr=16000, mono=True)
    _, (a, b) = librosa.effects.trim(y, top_db=40)
    pad = int(0.1 * sr)
    return f, len(y) / sr, (min(len(y), b + pad) - max(0, a - pad)) / sr

files = glob.glob("/src/*/*.wav")
tot = collections.defaultdict(lambda: [0, 0.0, 0.0])
with ProcessPoolExecutor(12) as ex:
    for f, raw, sp in ex.map(one, files, chunksize=32):
        k = "_".join(os.path.basename(f).split("_")[:2])
        tot[k][0] += 1; tot[k][1] += raw; tot[k][2] += sp
rows = sorted(tot.items(), key=lambda kv: -kv[1][2])
print("| # | Voz | Género | Frases | Min brutos | Min con voz | % voz |\n|---|---|---|---|---|---|---|")
for i, (k, (n, raw, sp)) in enumerate(rows, 1):
    print(f"| {i} | {k} | {'F' if k.startswith('arf') else 'M'} | {n} | {raw/60:.1f} | {sp/60:.1f} | {sp/raw*100:.0f}% |")
