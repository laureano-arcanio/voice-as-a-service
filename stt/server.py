"""Servidor STT minimo con API compatible con OpenAI, para probar modelos que
vLLM no sirve: Parakeet TDT (transformers, GPU) y Moonshine (moonshine-voice,
CPU). Ver servicios stt-parakeet / stt-moonshine (perfil `stt-eval`) en
docker-compose.yml.

Implementa solo lo que usan livekit.plugins.openai.STT (app/livekit_agent.py)
y scripts/stt_eval.py: POST /v1/audio/transcriptions multipart con `file` (+
`model`/`language`/`response_format`, el resto se ignora) -> {"text": ...}.
Mismo esquema de auth que vLLM con --api-key: Bearer obligatorio en /v1/*,
/health y /metrics libres. El campo `model` del request NO se valida (a
diferencia de vLLM), para que cambiar VLLM_STT_BASE_URL alcance para apuntar
el agente aca.

Sin batching: cada request toma una instancia del modelo de un pool de
STT_WORKERS (default 1) y las demas esperan en cola.

/metrics imita los nombres de vLLM que leen scripts/loadtest/monitor/
(sampler.py toma como "vLLM" a todo servicio con metricas `vllm:*`), asi
analyze.py mide estos servers igual que a vllm-stt: inferencia y cola por
request, en vuelo, req/s. generation_tokens_total cuenta palabras del
transcript + 1 por request: no son tokens reales, solo sirve para que el
sampler detecte actividad (la detecta por avance de contadores de tokens).
"""
import io
import logging
import os
import queue
import threading
import time
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import soxr
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from starlette.concurrency import run_in_threadpool

BACKEND = os.environ["STT_BACKEND"]
MODEL = os.environ["STT_MODEL"]
API_KEY = os.getenv("STT_API_KEY", "")
WORKERS = int(os.getenv("STT_WORKERS", "1"))
# Parakeet y Moonshine esperan audio mono a 16kHz.
SAMPLE_RATE = 16000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stt")


class ParakeetBackend:
    """nvidia/parakeet-tdt-0.6b-v3 via transformers (AutoModelForTDT), sin
    NeMo. Multilingue con deteccion automatica: no acepta pista de idioma."""

    def __init__(self):
        import torch
        from transformers import AutoModelForTDT, AutoProcessor

        self._torch = torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = getattr(torch, os.getenv("STT_DTYPE", "bfloat16"))
        self._processor = AutoProcessor.from_pretrained(MODEL)
        # El UserWarning "RNN module weights are not part of single contiguous
        # chunk" del warmup es esperable en bf16: cuDNN no soporta RNN en bf16
        # (flatten_parameters() no aplica). Es solo el LSTM chico del decoder.
        self._model = AutoModelForTDT.from_pretrained(MODEL, dtype=dtype, device_map=device).eval()

    def transcribe(self, audio: np.ndarray, language: str | None) -> str:
        inputs = self._processor([audio], sampling_rate=SAMPLE_RATE)
        inputs = inputs.to(self._model.device, dtype=self._model.dtype)
        with self._torch.inference_mode():
            out = self._model.generate(**inputs, return_dict_in_generate=True)
        return self._processor.batch_decode(out.sequences, skip_special_tokens=True)[0].strip()


class MoonshineBackend:
    """Moonshine via moonshine-voice (runtime C++ + ONNX Runtime propio, solo
    CPU). Los modelos no-ingleses son monolingues: el idioma lo fija
    MOONSHINE_LANGUAGE al arrancar, no el request. OJO licencia: los modelos
    no-ingleses son "Moonshine Community License" (no comercial / <USD 1M)."""

    def __init__(self):
        import moonshine_voice as mv

        arch = mv.string_to_model_arch(os.getenv("MOONSHINE_ARCH", "small-streaming"))
        path, arch = mv.get_model_for_language(os.getenv("MOONSHINE_LANGUAGE", "es"), arch)
        self._transcriber = mv.Transcriber(model_path=path, model_arch=arch)

    def transcribe(self, audio: np.ndarray, language: str | None) -> str:
        transcript = self._transcriber.transcribe_without_streaming(audio.tolist(), sample_rate=SAMPLE_RATE)
        return " ".join(line.text.strip() for line in transcript.lines if line.text.strip())


BACKENDS = {"parakeet": ParakeetBackend, "moonshine": MoonshineBackend}
_pool: queue.Queue = queue.Queue()

_metrics_lock = threading.Lock()
_metrics = dict.fromkeys(
    ("running", "waiting", "success", "tokens", "inference_sum", "queue_sum"), 0.0
)


def _decode(data: bytes) -> np.ndarray:
    audio, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        audio = soxr.resample(audio, sr, SAMPLE_RATE)
    return audio


def _add(**deltas: float) -> None:
    with _metrics_lock:
        for k, v in deltas.items():
            _metrics[k] += v


def _transcribe(audio: np.ndarray, language: str | None) -> tuple[str, float]:
    """(texto, segundos de inferencia) -- sin contar la espera en cola."""
    t_queued = time.monotonic()
    _add(waiting=1)
    backend = _pool.get()
    t_start = time.monotonic()
    _add(waiting=-1, running=1, queue_sum=t_start - t_queued)
    try:
        text = backend.transcribe(audio, language)
    finally:
        _pool.put(backend)
        _add(running=-1)
    inference = time.monotonic() - t_start
    _add(success=1, tokens=len(text.split()) + 1, inference_sum=inference)
    return text, inference


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se carga todo ANTES de que uvicorn abra el puerto: /health no responde
    # hasta que el modelo esta listo (el healthcheck de compose cubre la espera).
    t0 = time.monotonic()
    for _ in range(WORKERS):
        backend = BACKENDS[BACKEND]()
        # Warmup: el primer request real no paga la inicializacion (CUDA, etc.).
        backend.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), None)
        _pool.put(backend)
    log.info("%s listo: %s x%d en %.1fs", BACKEND, MODEL, WORKERS, time.monotonic() - t0)
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def check_api_key(request: Request, call_next):
    if API_KEY and request.url.path.startswith("/v1/"):
        if request.headers.get("authorization") != f"Bearer {API_KEY}":
            return JSONResponse({"error": {"message": "Unauthorized"}}, status_code=401)
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    with _metrics_lock:
        m = dict(_metrics)
    lab = f'model_name="{MODEL}"'
    n = m["success"]
    lines = [
        f"vllm:num_requests_running{{{lab}}} {m['running']}",
        f"vllm:num_requests_waiting{{{lab}}} {m['waiting']}",
        f'vllm:request_success_total{{finished_reason="stop",{lab}}} {n}',
        f"vllm:generation_tokens_total{{{lab}}} {m['tokens']}",
        f"vllm:request_inference_time_seconds_sum{{{lab}}} {m['inference_sum']}",
        f"vllm:request_inference_time_seconds_count{{{lab}}} {n}",
        f"vllm:request_queue_time_seconds_sum{{{lab}}} {m['queue_sum']}",
        f"vllm:request_queue_time_seconds_count{{{lab}}} {n}",
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": BACKEND}]}


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    response_format: str = Form("json"),
):
    if response_format not in ("json", "text", "verbose_json"):
        raise HTTPException(400, f"response_format no soportado: {response_format}")
    try:
        audio = _decode(await file.read())
    except Exception as e:
        raise HTTPException(400, f"no se pudo decodificar el audio: {e}") from None

    t0 = time.monotonic()
    text, inference = await run_in_threadpool(_transcribe, audio, language)
    elapsed = time.monotonic() - t0
    duration = len(audio) / SAMPLE_RATE
    log.info("%.2fs de audio en %.0fms (inferencia %.0fms): %r",
             duration, elapsed * 1000, inference * 1000, text)

    if response_format == "text":
        return PlainTextResponse(text)
    if response_format == "verbose_json":
        return {"task": "transcribe", "language": language, "duration": duration, "text": text, "segments": []}
    return {"text": text}
