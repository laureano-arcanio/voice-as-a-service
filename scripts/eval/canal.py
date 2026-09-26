"""Capa de canal entre el cliente simulado y el motor (docs/EVAL_LLM_PLAN.md,
seccion 3): lo que dice el cliente llega al agente como lo transcribiria el STT.

  texto     tal cual (default, gratis).
  stt-sim   perturbaciones textuales de los errores medidos del STT: tildes,
            homofonos, email dictado partido en dos turnos, cortes del VAD.
  tts-stt   el turno pasa por vllm-tts (una voz distinta a la del agente), se
            degrada a banda telefonica (stt_corpus/channel.py, variante tel8k) y
            lo transcribe stt-parakeet. Es el STT real; carga las GPUs en uso.
"""
import io
import random
import re
import unicodedata

import httpx

from app import config

# Confusiones vistas en llamadas reales (replay_transcripts.py) y en el eval de
# STT (README, "Eval de STT").
HOMOFONOS = {
    "gómez": "gomes", "suárez": "suares", "fernández": "fernandes", "pérez": "peres",
    "fibranet": "fibra net", "belgrano": "de grano", "running": "rolling", "calistenia": "calisteña",
    "ecografía": "eco grafía", "veintitrés": "veinte y tres", "browix": "brogüix", "whatsapp": "guasap",
    "rapipago": "rapi pago", "gmail": "yimeil", "hotmail": "jotmeil",
}


class CanalTexto:
    nombre = "texto"

    async def aplicar(self, texto: str, rng: random.Random) -> list[str]:
        return [texto]


class CanalSttSim:
    """Cada perturbacion tiene su probabilidad; el rng viene del escenario, asi
    que la misma semilla da las mismas perturbaciones."""
    nombre = "stt-sim"

    def __init__(self, p_tildes=0.3, p_homofono=0.7, p_corte_email=0.5, p_corte_vad=0.15):
        self.p_tildes, self.p_homofono, self.p_corte_email, self.p_corte_vad = p_tildes, p_homofono, p_corte_email, p_corte_vad

    async def aplicar(self, texto: str, rng: random.Random) -> list[str]:
        palabras = texto.split()
        out = []
        for w in palabras:
            base = re.sub(r"[^\wáéíóúñü]", "", w.lower())
            if base in HOMOFONOS and rng.random() < self.p_homofono:
                out.append(HOMOFONOS[base] + re.sub(r"[\wáéíóúñü]", "", w))
            elif rng.random() < self.p_tildes:
                out.append(unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode())
            else:
                out.append(w)
        texto = " ".join(out)
        # El VAD corta el dictado del email antes del dominio (llamada 2d0c771b).
        if " arroba " in texto and rng.random() < self.p_corte_email:
            a, b = texto.split(" arroba ", 1)
            return [a, "arroba " + b]
        if len(palabras) > 6 and rng.random() < self.p_corte_vad:
            n = rng.randint(1, 2)
            return [" ".join(texto.split()[:-n])]
        return [texto]


class CanalTtsStt:
    nombre = "tts-stt"

    def __init__(self, voz: str = "martin", variante: str = "tel8k"):
        self.voz, self.variante = voz, variante
        self.http = httpx.AsyncClient(timeout=60)
        self.auth = {"Authorization": f"Bearer {config.VLLM_API_KEY}"}

    async def aplicar(self, texto: str, rng: random.Random) -> list[str]:
        wav = await self.sintetizar(texto)
        wav = self.degradar(wav, rng)
        return [await self.transcribir(wav)]

    async def sintetizar(self, texto: str) -> bytes:
        # Nunca sin voice: mata el engine de vllm-tts (AGENTS.md).
        r = await self.http.post(f"{config.VLLM_TTS_BASE_URL}/audio/speech", headers=self.auth,
                                 json={"model": config.VLLM_TTS_MODEL, "voice": self.voz, "input": texto,
                                       "response_format": "wav"})
        r.raise_for_status()
        return r.content

    def degradar(self, wav: bytes, rng: random.Random) -> bytes:
        import numpy as np
        from scripts.stt_corpus import channel as ch
        x, sr = ch.read_wav(io.BytesIO(wav))
        tel = ch.normalize(ch.resample(x, sr, 8000, band=(300, 3400)), 8000)
        if self.variante == "tel8k_noise":
            noise = np.random.default_rng(rng.getrandbits(32)).standard_normal(len(tel))
            tel = tel + noise * np.sqrt(ch.active_power(tel, 8000) / 10)
        y = ch.ulaw(tel)
        if self.variante == "tel8k_cuts":
            y, _, _ = ch.packet_loss(y, 8000, 0.05, 2.0, np.random.default_rng(rng.getrandbits(32)))
        buf = io.BytesIO()
        import wave
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(ch.to_pcm(y))
        return buf.getvalue()

    async def transcribir(self, wav: bytes) -> str:
        r = await self.http.post(f"{config.VLLM_STT_BASE_URL}/audio/transcriptions", headers=self.auth,
                                 files={"file": ("audio.wav", wav, "audio/wav")},
                                 data={"model": config.VLLM_STT_MODEL, "language": "es", "response_format": "json"})
        r.raise_for_status()
        return (r.json().get("text") or "").strip()


def crear(nombre: str, **kw):
    if nombre == "texto":
        return CanalTexto()
    if nombre == "stt-sim":
        return CanalSttSim()
    if nombre.startswith("tts-stt"):
        # tts-stt, tts-stt:tel8k_noise, tts-stt:tel8k_cuts
        variante = nombre.split(":", 1)[1] if ":" in nombre else "tel8k"
        return CanalTtsStt(voz=kw.get("voz") or "martin", variante=variante)
    raise ValueError(f"canal desconocido: {nombre}")
