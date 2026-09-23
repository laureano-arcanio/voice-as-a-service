"""Silencios de un audio: al inicio, al final y la pausa interna mas larga.

Frames de 20 ms; un frame es "voz" si su RMS esta a menos de 40 dB del pico del audio.
Uso como script: python silences.py <carpeta con .wav> [...] -> tabla markdown.
"""
import glob
import sys

import librosa
import numpy as np


def sil(path, db=40, hop=0.02):
    """(silencio inicial, silencio final, pausa interna mas larga, duracion), en segundos."""
    y, sr = librosa.load(path, sr=16000)
    rms = librosa.feature.rms(y=y, frame_length=int(0.04 * sr), hop_length=int(hop * sr))[0]
    voiced = 20 * np.log10(rms + 1e-9) > 20 * np.log10(rms.max() + 1e-9) - db
    idx = np.flatnonzero(voiced)
    if len(idx) == 0:
        return 0.0, 0.0, 0.0, len(y) / sr
    gaps = np.diff(idx) - 1
    return idx[0] * hop, (len(voiced) - 1 - idx[-1]) * hop, (gaps.max() * hop if len(gaps) else 0.0), len(y) / sr


if __name__ == "__main__":
    print("| Carpeta | N | Inicio p50/max | Final p50/max | Pausa interna p50/max | Pausas >0,7 s |")
    print("|---|---|---|---|---|---|")
    for d in sys.argv[1:]:
        a = np.array([sil(f) for f in sorted(glob.glob(d + "/*.wav"))])
        f = lambda c: f"{np.median(a[:, c]):.2f} / {a[:, c].max():.2f}"  # noqa: E731
        print(f"| {d} | {len(a)} | {f(0)} | {f(1)} | {f(2)} | {(a[:, 2] > 0.7).sum()} |")
