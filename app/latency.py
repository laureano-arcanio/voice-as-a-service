"""Latencia por turno del agente de voz: en que se va el tiempo entre que el
cliente deja de hablar y el agente empieza a sonar.

    eou         = end_of_utterance_delay: desde que el cliente dejo de hablar
                  hasta que la sesion da el turno por terminado. Incluye:
      stt       = transcription_delay: cierre del transcript final.
      endpointing = eou - stt: espera del VAD / turn detector.
    llm         = ConversationEngine.process_turn completo (el LLM devuelve el
                  JSON entero antes de hablar, asi que es su tiempo al primer audio).
    tts         = TTS time-to-first-byte del primer segmento.
    total       = eou + llm + tts.

Se agrupa por speech_id (una respuesta del agente = un turno). EOU y TTS llegan
por el evento `metrics_collected` de LiveKit; el LLM ya no pasa por el plugin
(el agente sobreescribe llm_node), asi que lo mide el agente y lo pasa con
`on_llm`.
"""
import statistics

from livekit.agents.metrics import EOUMetrics, TTSMetrics

STAT_KEYS = ("total", "eou", "stt", "endpointing", "llm", "tts")


class TurnLatencyTracker:
    def __init__(self):
        self.turns: dict[str, dict] = {}

    def _turn(self, speech_id: str) -> dict:
        return self.turns.setdefault(speech_id, {"tts_audio": 0.0})

    def on_metrics(self, m) -> None:
        if not getattr(m, "speech_id", None):
            return
        if isinstance(m, EOUMetrics):
            t = self._turn(m.speech_id)
            t["eou"] = m.end_of_utterance_delay
            t["stt"] = m.transcription_delay
            t["endpointing"] = max(m.end_of_utterance_delay - m.transcription_delay, 0.0)
        elif isinstance(m, TTSMetrics) and m.speech_id in self.turns:
            t = self.turns[m.speech_id]
            t.setdefault("tts", m.ttfb)
            t["tts_audio"] += m.audio_duration

    def on_llm(self, speech_id: str | None, seconds: float) -> None:
        if speech_id:
            self._turn(speech_id)["llm"] = seconds

    def summary(self) -> dict:
        turns = []
        for t in self.turns.values():
            if "eou" not in t:
                continue
            parts = [t.get(k) for k in ("eou", "llm", "tts")]
            t["total"] = sum(parts) if None not in parts else None
            turns.append({k: round(v, 3) if isinstance(v, float) else v for k, v in t.items()})
        stats = {}
        for k in STAT_KEYS:
            values = [t[k] for t in turns if t.get(k) is not None]
            if values:
                stats[k] = {"avg": round(statistics.mean(values), 3), "max": round(max(values), 3)}
        return {"n_turns": len(turns), "turns": turns, "stats": stats}
