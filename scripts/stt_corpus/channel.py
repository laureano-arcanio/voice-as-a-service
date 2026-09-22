"""Canal telefonico simulado, compartido por los corpus de eval de STT
(openslr61.py, entities.py). Cada audio sale en 4 variantes:

  clean16k     16kHz, sin degradar: linea de base del modelo.
  tel8k        banda telefonica (300-3400Hz), 8kHz, G.711 mu-law: lo que
               llega por Anura/Asterisk.
  tel8k_noise  tel8k + ruido blanco a --snr dB sobre la voz activa (linea
               ruidosa), agregado antes de codificar.
  tel8k_cuts   tel8k + micro cortes: perdida de paquetes RTP de 20ms con
               rafagas (modelo de Gilbert-Elliott, --loss y --burst), sin
               ocultamiento (los paquetes perdidos quedan en silencio).

Todas se normalizan a -20 dBFS de voz activa. Solo numpy + audioop: la imagen
del agent no trae scipy ni soxr.
"""
import argparse
import audioop
import wave
import zlib
from pathlib import Path

import numpy as np

VARIANTS = ("clean16k", "tel8k", "tel8k_noise", "tel8k_cuts")
TARGET_DBFS = -20.0
FRAME_S = 0.02  # frame de analisis y paquete RTP (ptime 20ms)


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--snr", type=float, default=10.0, help="SNR del ruido blanco en tel8k_noise, dB (default 10)")
    p.add_argument("--loss", type=float, default=0.05, help="tasa de perdida de paquetes en tel8k_cuts (default 0.05)")
    p.add_argument("--burst", type=float, default=2.0, help="largo medio de rafaga, en paquetes de 20ms (default 2)")
    p.add_argument("--seed", type=int, default=0)


def read_wav(path) -> tuple[np.ndarray, int]:
    """path o archivo en memoria (io.BytesIO)."""
    with wave.open(path if hasattr(path, "read") else str(path)) as w:
        assert w.getsampwidth() == 2, f"{path}: se esperaba PCM 16 bits"
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        return x, w.getframerate()


def write_wav(path: Path, x: np.ndarray, sr: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(to_pcm(x))


def to_pcm(x: np.ndarray) -> bytes:
    return (np.clip(x, -1, 1 - 1 / 32768) * 32768).astype("<i2").tobytes()


def resample(x: np.ndarray, sr_in: int, sr_out: int, band: tuple[float, float] | None = None) -> np.ndarray:
    """Remuestreo por FFT (pasabajos ideal a la nueva Nyquist), con pasabanda
    opcional con flancos de coseno de 100Hz. Offline alcanza y no requiere scipy."""
    n_out = round(len(x) * sr_out / sr_in)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / sr_in)
    if band:
        lo, hi = band
        gain = np.clip((freqs - (lo - 50)) / 100, 0, 1) * np.clip(((hi + 50) - freqs) / 100, 0, 1)
        spec = spec * (0.5 - 0.5 * np.cos(np.pi * gain))
    keep = min(len(spec), n_out // 2 + 1)
    out = np.zeros(n_out // 2 + 1, dtype=complex)
    out[:keep] = spec[:keep]
    return np.fft.irfft(out, n_out) * (n_out / len(x))


def active_power(x: np.ndarray, sr: int) -> float:
    """Potencia media de los frames con voz: dentro de 35dB del frame mas fuerte."""
    n = int(FRAME_S * sr)
    frames = x[: len(x) // n * n].reshape(-1, n)
    p = (frames ** 2).mean(axis=1) + 1e-12
    return float(p[p > p.max() * 10 ** -3.5].mean())


def normalize(x: np.ndarray, sr: int) -> np.ndarray:
    x = x * 10 ** (TARGET_DBFS / 20) / np.sqrt(active_power(x, sr))
    peak = np.abs(x).max()
    return x / peak * 0.98 if peak > 0.98 else x


def ulaw(x: np.ndarray) -> np.ndarray:
    """Ida y vuelta por G.711 mu-law (el codec de la troncal)."""
    pcm = audioop.ulaw2lin(audioop.lin2ulaw(to_pcm(x), 2), 2)
    return np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768


def packet_loss(x: np.ndarray, sr: int, loss: float, burst: float, rng: np.random.Generator) -> tuple[np.ndarray, int, int]:
    """Gilbert-Elliott sobre paquetes de 20ms: tasa media `loss`, rafagas de
    `burst` paquetes en promedio. Devuelve (audio, paquetes perdidos, cortes)."""
    n = int(FRAME_S * sr)
    p_bg = 1 / burst
    p_gb = loss * p_bg / (1 - loss)
    y, lost, cuts, bad = x.copy(), 0, 0, False
    for i in range(len(x) // n):
        was_bad = bad
        bad = rng.random() < (1 - p_bg if bad else p_gb)
        if bad:
            y[i * n:(i + 1) * n] = 0
            lost += 1
            cuts += not was_bad
    return y, lost, cuts


def write_variants(x: np.ndarray, sr: int, out: Path, name: str, text: str, args: argparse.Namespace) -> dict:
    """Escribe <out>/<variante>/<name>.wav + .txt. Devuelve duracion y cortes."""
    rng = np.random.default_rng(zlib.crc32(name.encode()) ^ args.seed)
    tel = normalize(resample(x, sr, 8000, band=(300, 3400)), 8000)
    noise = rng.standard_normal(len(tel)) * np.sqrt(active_power(tel, 8000) / 10 ** (args.snr / 10))
    cut, lost, cuts = packet_loss(ulaw(tel), 8000, args.loss, args.burst, rng)
    audio = {
        "clean16k": (normalize(resample(x, sr, 16000), 16000), 16000),
        "tel8k": (ulaw(tel), 8000),
        "tel8k_noise": (ulaw(tel + noise), 8000),
        "tel8k_cuts": (cut, 8000),
    }
    for v, (y, rate) in audio.items():
        (out / v).mkdir(parents=True, exist_ok=True)
        write_wav(out / v / f"{name}.wav", y, rate)
        (out / v / f"{name}.txt").write_text(text + "\n")
    return {"duration_s": round(len(x) / sr, 2), "lost_packets": lost, "cuts": cuts}


def summary(rows: list[dict], args: argparse.Namespace) -> str:
    packets = sum(r["duration_s"] / FRAME_S for r in rows)
    return (f"tel8k_noise: SNR {args.snr:g} dB | tel8k_cuts: {sum(r['lost_packets'] for r in rows) / packets:.1%} "
            f"de paquetes perdidos en {sum(r['cuts'] for r in rows)} cortes")
