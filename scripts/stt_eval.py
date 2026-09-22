"""Compara los STT candidatos (perfil `stt-eval` de docker-compose.yml) contra
el actual (vllm-stt) sobre el mismo corpus: WER y latencia por request.

Manda cada .wav como lo haria el agente (POST /v1/audio/transcriptions,
language=es, VLLM_API_KEY), de a un request por vez: mide latencia de
inferencia SIN carga, no throughput. Para ver como se comporta uno bajo carga,
apuntar el agente a el (ver .env.example) y correr `make loadtest`.

Corpus: por defecto el del load test (scripts/loadtest/audio, voz sintetica
del propio vllm-tts), con UTTERANCES de gen_audio.py como referencia. Con
--audio-dir se usa otro: cada X.wav con su transcript correcto en X.txt al
lado (ej. recortes de llamadas reales). --telephone degrada el audio a 8kHz
mu-law, que es lo que llega en una llamada real por Anura/Asterisk.

El WER se calcula sobre texto normalizado (minusculas, sin tildes ni
puntuacion): "Si." y "sí" cuentan como la misma palabra.

Uso: make stt-eval   /   make stt-eval ARGS="--telephone --runs 5"
"""
import argparse
import audioop
import io
import os
import re
import statistics
import time
import unicodedata
import wave
from pathlib import Path

import httpx

from app import config
from scripts.loadtest.gen_audio import AUDIO_DIR, UTTERANCES

# nombre -> (base_url, model). vllm-stt va con su URL/modelo de compose y no
# con los de config: si .env apunta el agente a un candidato, igual se compara
# contra Qwen3-ASR.
ENGINES = {
    "qwen3-asr": ("http://vllm-stt:8000/v1", os.getenv("VLLM_STT_MODEL", "Qwen/Qwen3-ASR-1.7B")),
    "parakeet": ("http://stt-parakeet:8000/v1", "nvidia/parakeet-tdt-0.6b-v3"),
    "whisper-turbo": ("http://stt-whisper:8000/v1", "openai/whisper-large-v3-turbo"),
    "moonshine-es": ("http://stt-moonshine:8000/v1", "moonshine-es"),
}

# Mismo bug de qwenllm/qwen3-asr que parchea app/livekit_agent.py: el
# transcript viene con el template interno antepuesto.
_ASR_TEMPLATE_PREFIX_RE = re.compile(r"^language\s+\S+<asr_text>")


def _normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w\s]", " ", text).split()


def _edit_distance(ref: list[str], hyp: list[str]) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1]


def _corpus(audio_dir: Path | None) -> list[tuple[str, bytes, str]]:
    """[(nombre, wav_bytes, referencia)]"""
    if audio_dir:
        return [(p.stem, p.read_bytes(), p.with_suffix(".txt").read_text().strip())
                for p in sorted(audio_dir.glob("*.wav"))]
    return [(f"{cat}_{i:02d}", (AUDIO_DIR / f"{cat}_{i:02d}.wav").read_bytes(), text)
            for cat, texts in UTTERANCES.items() for i, text in enumerate(texts)]


def _to_telephone(wav_bytes: bytes) -> bytes:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        width, rate, pcm = w.getsampwidth(), w.getframerate(), w.readframes(w.getnframes())
        if w.getnchannels() == 2:
            pcm = audioop.tomono(pcm, width, 0.5, 0.5)
    pcm, _ = audioop.ratecv(pcm, width, 1, rate, 8000, None)
    pcm = audioop.ulaw2lin(audioop.lin2ulaw(pcm, width), width)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(width)
        w.setframerate(8000)
        w.writeframes(pcm)
    return out.getvalue()


def _duration(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getnframes() / w.getframerate()


def _transcribe(client: httpx.Client, base_url: str, model: str, wav: bytes) -> tuple[str, float]:
    t0 = time.perf_counter()
    r = client.post(
        f"{base_url}/audio/transcriptions",
        files={"file": ("audio.wav", wav, "audio/wav")},
        data={"model": model, "language": "es", "response_format": "json"},
    )
    elapsed = time.perf_counter() - t0
    r.raise_for_status()
    return _ASR_TEMPLATE_PREFIX_RE.sub("", r.json()["text"]).strip(), elapsed


def _pct(values: list[float], p: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, round(p * (len(values) - 1)))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engines", default=",".join(ENGINES), help="subset separado por comas")
    parser.add_argument("--audio-dir", type=Path, help="X.wav + X.txt (default: corpus del load test)")
    parser.add_argument("--telephone", action="store_true", help="degradar a 8kHz mu-law antes de mandar")
    parser.add_argument("--runs", type=int, default=3, help="requests por audio para la latencia")
    args = parser.parse_args()

    corpus = _corpus(args.audio_dir)
    if args.telephone:
        corpus = [(name, _to_telephone(wav), ref) for name, wav, ref in corpus]
    headers = {"Authorization": f"Bearer {config.VLLM_API_KEY}"}
    summary = []

    with httpx.Client(headers=headers, timeout=60) as client:
        for engine in args.engines.split(","):
            base_url, model = ENGINES[engine]
            try:
                _transcribe(client, base_url, model, corpus[0][1])  # warmup
            except httpx.HTTPError as e:
                print(f"\n== {engine}: no responde en {base_url} ({e!r}), salteo")
                continue

            print(f"\n== {engine} ({model})")
            errors = ref_words = 0
            latencies, rtfs = [], []
            for name, wav, ref in corpus:
                runs = [_transcribe(client, base_url, model, wav) for _ in range(args.runs)]
                hyp = runs[0][0]
                ref_tokens = _normalize(ref)
                dist = _edit_distance(ref_tokens, _normalize(hyp))
                errors += dist
                ref_words += len(ref_tokens)
                clip_latencies = [t for _, t in runs]
                latencies += clip_latencies
                rtfs += [t / _duration(wav) for t in clip_latencies]
                mark = "  " if dist == 0 else f"{dist:2d}"
                print(f"  {mark} {name:10s} {statistics.median(clip_latencies) * 1000:5.0f}ms  {hyp!r}")
                if dist:
                    print(f"     {'':10s} {'ref':>7s}  {ref!r}")
            summary.append((engine, errors / max(ref_words, 1), statistics.median(latencies),
                            _pct(latencies, 0.9), statistics.median(rtfs)))

    print(f"\nResumen{' (audio telefonico 8kHz mu-law)' if args.telephone else ''}"
          f" -- {len(corpus)} audios x {args.runs} runs, requests de a uno:")
    print(f"  {'engine':15s} {'WER':>6s} {'p50':>7s} {'p90':>7s} {'RTF p50':>8s}")
    for engine, wer, p50, p90, rtf in summary:
        print(f"  {engine:15s} {wer:6.1%} {p50 * 1000:5.0f}ms {p90 * 1000:5.0f}ms {rtf:8.3f}")


if __name__ == "__main__":
    main()
