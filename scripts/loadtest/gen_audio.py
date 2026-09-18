"""Genera el corpus de audio "de usuario" para el load test (run.py), con el
propio vllm-tts del stack -- asi no hace falta grabar nada a mano y el audio
tiene las mismas caracteristicas (acento, ritmo) que el que produce el agente.

Se corre UNA sola vez (cachea los .wav en scripts/loadtest/audio/, que queda
bind-mounteado y sobrevive a que se recree el contenedor). Requiere que
vllm-tts este arriba (`make up` / `make health-vllm`).

Uso: make loadtest-audio
"""
import audioop
import wave
from pathlib import Path

import httpx

from app import config

AUDIO_DIR = Path(__file__).resolve().parent / "audio"

# Distribucion de duracion de las respuestas del "cliente": en una llamada
# real la gran mayoria son cortas ("si", "no", "dale") y las largas son la
# excepcion -- run.py samplea 50% cortas / 25% medianas / 25% largas por
# llamada (ver SAMPLE_WEIGHTS ahi). LONG_CAP_S: las largas se recortan a esto
# despues de generarlas, por si el TTS se extiende de mas.
LONG_CAP_S = 5.0

# El VAD del agente (app/livekit_agent.py) usa min_silence_duration=0.3: una
# pausa interna mas larga que eso CIERRA el turno del usuario. El TTS mete
# pausas en cada coma, asi que sin este post-proceso una frase como
# "No, la verdad que todavia no lo lleve al service." se generaba con 0.78s de
# silencio despues del "No," y el agente la partia en DOS turnos ("No." +
# "La verdad que...") -- respondiendo al fragmento mientras el usuario todavia
# hablaba. Medido sobre el corpus anterior: las 3 frases medium se partian
# siempre, ~14% de los turnos del load test quedaban contaminados.
# 0.15s deja margen de sobra por debajo del umbral del VAD.
MAX_INTERNAL_SILENCE_S = 0.15
# Espejo de min_silence_duration del VAD en app/livekit_agent.py -- solo se usa
# para verificar el corpus generado. Si alla se cambia, cambiar aca.
VAD_MIN_SILENCE_S = 0.3
# Umbral de "esto es silencio" para el recorte. Mas bajo que el del detector
# del caller (150) a proposito: conviene equivocarse conservando audio antes
# que comerse el arranque suave de una palabra.
SILENCE_RMS = 100
WINDOW_MS = 20

# Frases genericas de "cliente" -- el load test mide latencia de inferencia,
# no precision de negocio, asi que no hace falta que respondan la pregunta
# real del guion activo.
UTTERANCES = {
    "short": [
        "Si.",
        "No.",
        "Perfecto.",
        "Dale, de acuerdo.",
    ],
    "medium": [
        "Hola, buenas tardes, si, te escucho bien.",
        "No, la verdad que todavia no lo lleve al service.",
        "Perfecto, muchas gracias por la informacion.",
    ],
    "long": [
        "Si, el auto esta andando barbaro, sin ningun problema hasta ahora.",
        "Mas o menos, tuve un par de dudas con el manual pero nada grave.",
    ],
}


def _tidy_silence(path: Path) -> None:
    """Saca el silencio del principio/final y acota las pausas internas a
    MAX_INTERNAL_SILENCE_S, para que el VAD del agente vea la frase como UN
    solo turno.

    El silencio del final tambien importa para la medicion: el caller marca
    `sent_end` cuando termina de empujar el archivo, asi que cualquier cola de
    silencio se cuenta como si el usuario hubiera seguido hablando y baja
    artificialmente la latencia medida.
    """
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        data = w.readframes(w.getnframes())
    step = int(params.framerate * WINDOW_MS / 1000) * params.sampwidth
    windows = [data[i:i + step] for i in range(0, len(data), step)]
    loud = [audioop.rms(c, params.sampwidth) >= SILENCE_RMS for c in windows]
    if not any(loud):
        return
    first, last = loud.index(True), len(loud) - 1 - loud[::-1].index(True)

    max_quiet = max(1, int(MAX_INTERNAL_SILENCE_S * 1000 / WINDOW_MS))
    out, quiet_run = [], 0
    for i in range(first, last + 1):
        if loud[i]:
            quiet_run = 0
            out.append(windows[i])
        else:
            quiet_run += 1
            if quiet_run <= max_quiet:
                out.append(windows[i])
    new_data = b"".join(out)
    if len(new_data) == len(data):
        return
    with wave.open(str(path), "wb") as w:
        w.setparams(params)
        w.writeframes(new_data)
    before, after = len(data) / (params.framerate * params.sampwidth), len(new_data) / (params.framerate * params.sampwidth)
    print(f"  {path.name}: silencios recortados {before:.2f}s -> {after:.2f}s")


def _internal_gaps(path: Path, min_gap_s: float) -> list[float]:
    """Pausas internas (en segundos) mayores o iguales a min_gap_s -- se usa
    para verificar que el post-proceso hizo su trabajo."""
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        data = w.readframes(w.getnframes())
    step = int(params.framerate * WINDOW_MS / 1000) * params.sampwidth
    gaps, run = [], 0.0
    for i in range(0, len(data) - step, step):
        if audioop.rms(data[i:i + step], params.sampwidth) < SILENCE_RMS:
            run += WINDOW_MS / 1000
        else:
            if run:
                gaps.append(run)
            run = 0.0
    return [g for g in gaps if g >= min_gap_s]


def _trim_to(path: Path, max_seconds: float) -> None:
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        max_frames = int(params.framerate * max_seconds)
        if params.nframes <= max_frames:
            return
        w.setpos(0)
        frames = w.readframes(max_frames)
    with wave.open(str(path), "wb") as w:
        w.setparams(params)
        w.setnframes(max_frames)
        w.writeframes(frames)
    print(f"  {path.name}: recortado a {max_seconds:.1f}s (TTS se extendio de mas)")


def main() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    base = config.VLLM_TTS_BASE_URL.rstrip("/")
    n = 0
    for category, texts in UTTERANCES.items():
        for i, text in enumerate(texts):
            out = AUDIO_DIR / f"{category}_{i:02d}.wav"
            n += 1
            if out.exists():
                print(f"ya existe {out.name}, salteo")
                continue
            print(f"generando {out.name}: {text!r}")
            r = httpx.post(
                f"{base}/audio/speech",
                json={
                    "model": config.VLLM_TTS_MODEL,
                    "voice": config.VLLM_TTS_VOICE,
                    "input": text,
                    "response_format": "wav",
                },
                timeout=60,
            )
            r.raise_for_status()
            out.write_bytes(r.content)
            _tidy_silence(out)
            if category == "long":
                _trim_to(out, LONG_CAP_S)

    # Verificacion: si alguna frase quedara con una pausa interna por encima
    # del umbral del VAD del agente, el load test mediria mal sin avisar (el
    # agente partiria la frase en dos turnos), asi que se avisa fuerte.
    print()
    bad = []
    for wav in sorted(AUDIO_DIR.glob("*.wav")):
        gaps = _internal_gaps(wav, VAD_MIN_SILENCE_S)
        dur = wave.open(str(wav), "rb").getnframes() / wave.open(str(wav), "rb").getframerate()
        status = f"PAUSAS {[round(g, 2) for g in gaps]}" if gaps else "ok"
        print(f"  {wav.name:15s} {dur:5.2f}s  {status}")
        if gaps:
            bad.append(wav.name)
    if bad:
        raise SystemExit(
            f"\nERROR: {bad} tienen pausas internas >= {VAD_MIN_SILENCE_S}s; el agente las "
            f"partiria en varios turnos. Reformula esas frases (menos comas) y volve a correr."
        )
    print(f"\nlisto: {n} audios en {AUDIO_DIR}, sin pausas internas >= {VAD_MIN_SILENCE_S}s")


if __name__ == "__main__":
    main()
