"""Instrumentacion simple de latencia por turno del agente de voz.

Junta las metricas que emite LiveKit Agents (evento `metrics_collected`) y las
agrupa por `speech_id` (una respuesta del agente = un turno). Por cada turno
queda el desglose de "en que se va el tiempo" entre que el cliente deja de
hablar y el agente empieza a sonar:

    eou   = end_of_utterance_delay: desde que el cliente dejo de hablar hasta que
            la sesion decide que termino el turno. Incluye:
              stt = transcription_delay: lo que tarda el STT en cerrar el
                    transcript final despues del ultimo audio del cliente.
              (el resto es la espera del endpointing / turn-detector)
    ttft  = LLM time-to-first-token (desde que se envia el prompt).
    tts   = TTS time-to-first-byte del primer segmento de audio.
    total = eou + ttft + tts  ~ latencia percibida por el cliente hasta oir la
            primera silaba de la respuesta.

Uso: `tracker = TurnLatencyTracker()`; `session.on("metrics_collected",
lambda ev: tracker.on_metrics(ev.metrics))`; al terminar, `tracker.summary()`.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field

from livekit.agents.metrics import EOUMetrics, LLMMetrics, STTMetrics, TTSMetrics

logger = logging.getLogger("aiva.latency")

_FIELDS = ("eou", "stt", "endpointing", "ttft", "llm_total", "tts", "total")


@dataclass
class Turn:
    speech_id: str
    eou: float | None = None          # end_of_utterance_delay
    stt: float | None = None          # transcription_delay
    endpointing: float | None = None  # eou - stt
    ttft: float | None = None         # LLM time to first token
    llm_total: float | None = None    # LLM duration completa
    llm_tokens: int | None = None
    tts: float | None = None          # TTS ttfb (primer segmento)
    tts_audio: float = 0.0            # audio generado en total (s)
    cancelled: bool = False           # el cliente interrumpio
    logged: bool = field(default=False, repr=False)

    @property
    def total(self) -> float | None:
        if self.eou is None or self.ttft is None or self.tts is None:
            return None
        return self.eou + self.ttft + self.tts

    def as_dict(self) -> dict:
        d = {k: (round(v, 3) if isinstance(v, float) else v)
             for k, v in self.__dict__.items() if k != "logged"}
        d["total"] = round(self.total, 3) if self.total is not None else None
        return d


class TurnLatencyTracker:
    def __init__(self, log: logging.Logger | None = None):
        self._log = log or logger
        self._turns: dict[str, Turn] = {}
        self._order: list[str] = []
        self.stt_requests: list[dict] = []  # metricas STT crudas (no tienen speech_id)

    def _turn(self, speech_id: str | None) -> Turn | None:
        if not speech_id:
            return None
        t = self._turns.get(speech_id)
        if t is None:
            t = self._turns[speech_id] = Turn(speech_id=speech_id)
            self._order.append(speech_id)
        return t

    def on_metrics(self, m) -> None:
        if isinstance(m, EOUMetrics):
            t = self._turn(m.speech_id)
            if t is None:
                return
            t.eou = m.end_of_utterance_delay
            t.stt = m.transcription_delay
            t.endpointing = max(m.end_of_utterance_delay - m.transcription_delay, 0.0)
        elif isinstance(m, LLMMetrics):
            t = self._turn(m.speech_id)
            if t is None:
                return
            t.ttft = m.ttft
            t.llm_total = m.duration
            t.llm_tokens = m.completion_tokens
            t.cancelled = t.cancelled or m.cancelled
        elif isinstance(m, TTSMetrics):
            t = self._turn(m.speech_id)
            if t is None:
                return
            if t.tts is None:  # solo el primer segmento define cuando empieza a sonar
                t.tts = m.ttfb
            t.tts_audio += m.audio_duration
            t.cancelled = t.cancelled or m.cancelled
        elif isinstance(m, STTMetrics):
            self.stt_requests.append({
                "duration": round(m.duration, 3),
                "audio_duration": round(m.audio_duration, 3),
                "streamed": m.streamed,
            })
            return
        else:
            return
        if t.total is not None and not t.logged:
            t.logged = True
            self._log_turn(t)

    def _log_turn(self, t: Turn) -> None:
        n = self._order.index(t.speech_id) + 1
        self._log.info(
            "turno %d | total %.2fs = eou %.2fs (stt %.2fs + endpointing %.2fs) "
            "+ llm ttft %.2fs + tts ttfb %.2fs | llm total %.2fs (%s tok) | audio %.1fs%s",
            n, t.total, t.eou, t.stt or 0.0, t.endpointing or 0.0, t.ttft, t.tts,
            t.llm_total or 0.0, t.llm_tokens, t.tts_audio,
            " | INTERRUMPIDO" if t.cancelled else "",
        )

    def turns(self) -> list[Turn]:
        # Solo turnos que arrancan con el cliente hablando (tienen EOU). El saludo
        # inicial via session.say() no tiene EOU ni LLM, asi que queda afuera.
        return [self._turns[s] for s in self._order if self._turns[s].eou is not None]

    def summary(self) -> dict:
        turns = self.turns()
        stats: dict[str, dict] = {}
        for f in _FIELDS:
            vals = [getattr(t, f) for t in turns if getattr(t, f) is not None]
            if vals:
                stats[f] = {
                    "avg": round(statistics.fmean(vals), 3),
                    "p50": round(statistics.median(vals), 3),
                    "max": round(max(vals), 3),
                }
        return {"turns": [t.as_dict() for t in turns], "stats": stats, "n_turns": len(turns)}

    def log_summary(self) -> None:
        s = self.summary()
        if not s["n_turns"]:
            self._log.info("latencia: sin turnos con metricas")
            return
        parts = [f"{f} avg {v['avg']:.2f}s / p50 {v['p50']:.2f}s / max {v['max']:.2f}s"
                 for f, v in s["stats"].items()]
        self._log.info("latencia resumen (%d turnos): %s", s["n_turns"], " | ".join(parts))
