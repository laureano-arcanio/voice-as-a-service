"""Contestador automatico por heuristica (docs/LLAMADAS_SALIENTES_PLAN.md, seccion 5): en una llamada de
campaña, si lo primero que transcribe el STT de quien atendio suena a buzon ("deje su mensaje despues de
la señal", "el abonado no esta disponible"...), la llamada se da por `voicemail`: se corta y se reintenta
como cualquier otro resultado. Sin deteccion, un buzon queda `answered`.

Es una lista de frases, no un detector de audio (AMD): un humano que dice "no esta disponible" en su
primer turno se toma por buzon. Por eso mira solo los primeros turnos del cliente. Medir cuanto pasa antes
de pasar a un detector real (plan, seccion 5).

Aca esta la logica, sin LiveKit, para probarla aparte; el worker (app/voice/worker.py) la conecta al
evento `user_input_transcribed` de la sesion.
"""
import re
import unicodedata

# Frases en minusculas y sin acentos (ver normalize); se buscan como palabras enteras.
PHRASES = (
    r"deje (su|un|el) mensaje", r"deja (tu|un|el) mensaje", r"deje (su )?recado", r"grabe (su|un) mensaje",
    r"buzon", r"casilla de (voz|mensajes)", r"mensaje de voz", r"contestador",
    r"(despues|luego) (de|del) (la )?(senal|tono|bip|pitido)", r"(al|cuando) (oir|escuchar|oiga|escuche) (la )?(senal|tono)",
    r"no (esta|se encuentra) disponible", r"no (puede|podemos|puedo) atender", r"no (se )?encuentra en este momento",
    r"fuera del area de cobertura", r"apagado o fuera de (servicio|cobertura)", r"el abonado",
    r"el numero (que|al que) (usted )?(marco|llamo|intenta)", r"la persona a la que (usted )?(llama|intenta comunicarse)",
)
_PATTERN = re.compile(r"\b(?:" + "|".join(PHRASES) + r")\b")
# Cuantas transcripciones finales del cliente se miran: el saludo de un buzon llega en varios pedazos.
FIRST_SEGMENTS = 4


def normalize(text: str) -> str:
    """Minusculas, sin acentos ni signos, un solo espacio entre palabras."""
    plain = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", plain)).strip()


def looks_like_voicemail(text: str) -> bool:
    return _PATTERN.search(normalize(text)) is not None


class VoicemailDetector:
    """Junta las primeras transcripciones finales del cliente y avisa cuando suenan a buzon."""

    def __init__(self, segments: int = FIRST_SEGMENTS):
        self.segments = segments
        self._seen = 0
        self._text: list[str] = []
        self.detected = False

    def feed(self, transcript: str, is_final: bool = True) -> bool:
        """True la primera vez que lo dicho hasta ahora suena a buzon. Ignora lo parcial y lo que llega
        despues de los primeros turnos."""
        if self.detected or not is_final or self._seen >= self.segments or not transcript.strip():
            return False
        self._seen += 1
        self._text.append(transcript)
        self.detected = looks_like_voicemail(" ".join(self._text))
        return self.detected
