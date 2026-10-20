"""Música de fondo sintetizada (sin licencias de terceros): pad suave + arpegio + bajo.

Es determinística (semilla fija): no se versiona el WAV, se regenera con este script.
Uso: python3 scripts/musica.py <proyecto> [segundos]   -> public/proyectos/<proyecto>/musica.wav
(sin segundos, usa musica_segundos de proyectos/<proyecto>/guion.json)
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

SR = 44100
if len(sys.argv) < 2:
    raise SystemExit(__doc__)
# Sin segundos, los del guion (musica_segundos: la duración del video con margen)
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else json.loads(
    (Path(__file__).resolve().parents[1] / "proyectos" / sys.argv[1] / "guion.json").read_text())["musica_segundos"]
OUT = Path(__file__).resolve().parents[1] / "public" / "proyectos" / sys.argv[1] / "musica.wav"
rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# Cmaj9 · Am9 · Fmaj9 · G6sus, 4 s cada uno (~ 60 bpm en negras)
ACORDES = [
    [48, 55, 59, 62, 64],
    [45, 52, 55, 59, 60],
    [41, 48, 52, 55, 57],
    [43, 50, 52, 55, 60],
]
SEG = 4.0
n = int(DUR * SR)
t = np.arange(n) / SR
mix = np.zeros(n)


def env_adsr(length, a, r):
    e = np.ones(length)
    na, nr = min(int(a * SR), length // 2), min(int(r * SR), length // 2)  # tramos cortos al final
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


# Pad: sinusoides con pocos armónicos y leve desafinación, entrada y salida lentas
for k in range(int(np.ceil(DUR / SEG))):
    ini, fin = int(k * SEG * SR), min(n, int((k + 1) * SEG * SR + 1.5 * SR))
    if ini >= n:
        break
    tt = np.arange(fin - ini) / SR
    e = env_adsr(fin - ini, 1.2, 1.6)
    for m in ACORDES[k % 4][1:]:
        for det in (-0.12, 0.12):
            f = hz(m + 12) * (1 + det / 100)
            ph = rng.uniform(0, 2 * np.pi)
            v = np.sin(2 * np.pi * f * tt + ph) + 0.25 * np.sin(4 * np.pi * f * tt + ph) + 0.08 * np.sin(6 * np.pi * f * tt)
            mix[ini:fin] += 0.05 * e * v
    # bajo
    f = hz(ACORDES[k % 4][0] - 12)
    mix[ini:fin] += 0.16 * e * np.sin(2 * np.pi * f * tt)

# Arpegio tipo "pluck" en corcheas (0,5 s), con decaimiento exponencial
PASO = 0.5
for i in range(int(DUR / PASO)):
    acorde = ACORDES[int(i * PASO / SEG) % 4]
    nota = acorde[[1, 2, 3, 4, 3, 2, 4, 3][i % 8]] + 24
    ini = int(i * PASO * SR)
    ln = min(n - ini, int(1.4 * SR))
    tt = np.arange(ln) / SR
    f = hz(nota)
    v = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 4.5)
    v[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    mix[ini:ini + ln] += 0.06 * v

# Reverb simple: convolución con ruido que decae
ir_len = int(2.2 * SR)
ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / SR * 3.0)
ir /= np.sqrt(np.sum(ir ** 2))
wet = np.fft.irfft(np.fft.rfft(mix, 2 * n) * np.fft.rfft(ir, 2 * n))[:n]
mix = 0.7 * mix + 0.35 * wet

# Fundido de entrada y salida, normalizado a -3 dBFS
mix *= env_adsr(n, 1.5, 3.0)
mix *= 10 ** (-3 / 20) / np.max(np.abs(mix))
pcm = (mix * 32767).astype("<i2").tobytes()
head = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1, 1, SR, SR * 2, 2, 16,
                   b"data", len(pcm))
OUT.write_bytes(head + pcm)
print(f"{OUT} {DUR:.1f} s")
