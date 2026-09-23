"""Servidor STT minimo con API compatible con OpenAI, para Parakeet TDT
(transformers, GPU), que vLLM no sirve. Ver servicio stt-parakeet (perfil
`stt-eval`) en docker-compose.yml.

Implementa solo lo que usan livekit.plugins.openai.STT (app/livekit_agent.py)
y scripts/stt_eval.py: POST /v1/audio/transcriptions multipart con `file` (+
`model`/`language`/`response_format`, el resto se ignora) -> {"text": ...}.
Mismo esquema de auth que vLLM con --api-key: Bearer obligatorio en /v1/*,
/health y /metrics libres. El campo `model` del request NO se valida (a
diferencia de vLLM), para que cambiar VLLM_STT_BASE_URL alcance para apuntar
el agente aca.

Batching dinamico: una sola instancia del modelo y un hilo que junta los
requests que llegaron mientras la GPU estaba ocupada (hasta STT_MAX_BATCH) y
los transcribe en un solo generate(). Un request solo no espera a nadie: con
poca carga la latencia es la de antes. Medido en la 3090 con los 300 audios de
OpenSLR 61 tel8k (scratch/parakeet_batch/): batch 1 = 56 ms y 83 s de audio/s;
batch 8 = 98 ms y 367 s de audio/s (x4,4). En batch cambian 5-9 de 300
transcripts, casi todo puntuacion/mayusculas (ruido de bf16 por el padding).

/metrics imita los nombres de vLLM que leen scripts/loadtest/monitor/
(sampler.py toma como "vLLM" a todo servicio con metricas `vllm:*`), asi
analyze.py lo mide igual que a vllm-stt: inferencia y cola por
request, en vuelo, req/s. generation_tokens_total cuenta palabras del
transcript + 1 por request: no son tokens reales, solo sirve para que el
sampler detecte actividad (la detecta por avance de contadores de tokens).
"""
import asyncio
import io
import logging
import os
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import soxr
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response

MODEL = os.environ["STT_MODEL"]
API_KEY = os.getenv("STT_API_KEY", "")
# Tope del batch. Con 8 el peor caso es ~100 ms por batch (x4,4 de throughput);
# con 32 sube a ~260 ms para x6,3.
MAX_BATCH = int(os.getenv("STT_MAX_BATCH", "8"))
# Tope de audio por batch (items x audio mas largo, en segundos): todos se
# rellenan al mas largo, y un turno largo no deberia demorar a muchos cortos.
MAX_BATCH_SECONDS = float(os.getenv("STT_MAX_BATCH_SECONDS", "120"))
# Parakeet espera audio mono a 16kHz.
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

    def transcribe(self, audios: list[np.ndarray]) -> list[str]:
        inputs = self._processor(audios, sampling_rate=SAMPLE_RATE)
        inputs = inputs.to(self._model.device, dtype=self._model.dtype)
        with self._torch.inference_mode():
            out = self._model.generate(**inputs, return_dict_in_generate=True)
        return [t.strip() for t in self._processor.batch_decode(out.sequences, skip_special_tokens=True)]


@dataclass
class _Job:
    audio: np.ndarray
    future: Future = field(default_factory=Future)
    t_queued: float = field(default_factory=time.monotonic)

    @property
    def seconds(self) -> float:
        return len(self.audio) / SAMPLE_RATE


_jobs: queue.Queue[_Job] = queue.Queue()

_metrics_lock = threading.Lock()
_metrics = dict.fromkeys(
    ("running", "waiting", "success", "tokens", "inference_sum", "queue_sum",
     "batches", "batch_items"), 0.0
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


def _take_batch(first: _Job) -> tuple[list[_Job], _Job | None]:
    """El primero mas lo que ya este en cola, sin esperar, hasta los topes.
    Devuelve tambien el que no entro por MAX_BATCH_SECONDS: encabeza el proximo."""
    batch, longest = [first], first.seconds
    while len(batch) < MAX_BATCH:
        try:
            job = _jobs.get_nowait()
        except queue.Empty:
            break
        n = max(longest, job.seconds)
        if n * (len(batch) + 1) > MAX_BATCH_SECONDS:
            return batch, job
        batch.append(job)
        longest = n
    return batch, None


def _worker(backend: ParakeetBackend) -> None:
    carry = None
    while True:
        batch, carry = _take_batch(carry or _jobs.get())
        t_start = time.monotonic()
        _add(waiting=-len(batch), running=len(batch),
             queue_sum=sum(t_start - j.t_queued for j in batch))
        try:
            texts = backend.transcribe([j.audio for j in batch])
        except Exception:
            # Un audio problematico no tira el batch entero: de a uno, cada
            # request recibe su propio resultado o su propio error.
            log.exception("fallo un batch de %d, reintento de a uno", len(batch))
            texts = []
            for j in batch:
                try:
                    texts.append(backend.transcribe([j.audio])[0])
                except Exception as e:  # noqa: BLE001
                    texts.append(e)
        inference = time.monotonic() - t_start
        _add(running=-len(batch), batches=1, batch_items=len(batch))
        for j, t in zip(batch, texts):
            if isinstance(t, Exception):
                j.future.set_exception(t)
            else:
                _add(success=1, tokens=len(t.split()) + 1, inference_sum=inference)
                j.future.set_result((t, inference))


async def _transcribe(audio: np.ndarray) -> tuple[str, float]:
    """(texto, segundos de inferencia del batch) -- sin contar la espera en cola."""
    job = _Job(audio)
    _add(waiting=1)
    _jobs.put(job)
    return await asyncio.wrap_future(job.future)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se carga todo ANTES de que uvicorn abra el puerto: /health no responde
    # hasta que el modelo esta listo (el healthcheck de compose cubre la espera).
    t0 = time.monotonic()
    backend = ParakeetBackend()
    # Warmup: el primer request real no paga la inicializacion (CUDA, etc.).
    backend.transcribe([np.zeros(SAMPLE_RATE, dtype=np.float32)] * 2)
    threading.Thread(target=_worker, args=(backend,), daemon=True, name="stt-batch").start()
    log.info("listo: %s (max_batch=%d) en %.1fs", MODEL, MAX_BATCH, time.monotonic() - t0)
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
        f"stt:batches_total{{{lab}}} {m['batches']}",
        f"stt:batch_items_total{{{lab}}} {m['batch_items']}",
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "stt-server"}]}


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
    text, inference = await _transcribe(audio)
    elapsed = time.monotonic() - t0
    duration = len(audio) / SAMPLE_RATE
    log.info("%.2fs de audio en %.0fms (inferencia %.0fms): %r",
             duration, elapsed * 1000, inference * 1000, text)

    if response_format == "text":
        return PlainTextResponse(text)
    if response_format == "verbose_json":
        return {"task": "transcribe", "language": language, "duration": duration, "text": text, "segments": []}
    return {"text": text}
