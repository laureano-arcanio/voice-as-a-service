"""Compara voces y grafías con el TTS propio: genera cada (voz, texto), lo transcribe con el STT propio y mide
la expresividad (desvío de F0 en semitonos: cuanto más bajo, más monótona suena).

Uso: python3 scripts/candidatas.py voces   |   python3 scripts/candidatas.py api
Escribe en scratch/videos/candidatas/<grupo>/ (para escuchar las tomas).
"""
import json
import struct
import sys
import urllib.request
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "scratch" / "videos" / "candidatas"
SR = 24000

A1 = "¡Sí! Tengo a las diez o a las once. ¿Cuál te queda mejor?"
GRUPOS = {
    "voces": [(v, A1) for v in ["sofia", "jimena", "gabriela", "laura", "veronica", "valentina", "mariana",
                                "daniela", "camila", "martina", "florencia", "paula", "milagros", "rocio"]],
    "api": [("lucas", t) for t in [
        "Lo creás por API.",
        "Lo creás por ei pi ái.",
        "Lo creás por éi pi ái.",
        "Lo creás por ei-pi-ai.",
        "Lo creás por <en>API</en>.",
        "Lo creás por la ei, pi, ái.",
        "Lo definís en un yéison.",
        "Lo definís en un JSON.",
    ]],
    # Video goldman v2: "aires", "Goldman", "clasifica" y el cierre (dos tomas por texto: el TTS varía)
    "goldman": [("lucas", t) for t in [
        "En Isaías Goldman, en temporada de aires, las consultas no paran.",
        "En Isaías Goldman, en temporada de áires, las consultas no paran.",
        "En Isaías Góldman, en temporada de áires, las consultas no paran.",
        "En Isaías Góldman, en temporada de áires las consultas no paran.",
        "En Isaías Gold man, en la temporada de áires, las consultas no paran.",
        "En Isaías Goldman, en temporada de aire acondicionado, las consultas no paran.",
        "Actualmente, un solo número y el local cerrado no alcanzan. La consulta que no se contesta en minutos, se va a otro lado.",
        "Clasifica, responde lo general, y deriva a su equipo.",
        "Clasífica, responde lo general, y deriva a su equipo.",
        "Empecemos un piloto en noviembre, antes del pico de consultas.",
        "Arranquemos con un piloto en noviembre, antes del pico de consultas.",
    ] for _ in range(2)],
    # Video goldman-analisis v1: nombres de clientes, cifras y "aire" (dos tomas por texto)
    "goldman-analisis": [("lucas", t) for t in [
        "En Isaías Goldman ya hicieron lo difícil.",
        "Empresas como Arcor, Georgalos y Mostaza.",
        "Empresas como Arcor, Yeorgalos y Mostaza.",
        "Empresas como Arcor, Georgálos y Mostaza.",
        "Mil seiscientas setenta y una reseñas, con cuatro coma dos.",
        "Quien quiere saber cuánto sale un aire, tiene que escribir y esperar.",
        "Quien quiere saber cuánto sale un áire, tiene que escribir y esperar.",
        "Ciento veintiuna de las ciento sesenta y ocho horas de la semana, cerrado.",
    ] for _ in range(2)],
    # Video baicenter-analisis v1: cómo dice "BAIC" y "EPEC" (dos tomas por texto)
    "baicenter": [("lucas", t) for t in [
        "En BAIC Center ya hicieron lo difícil.",
        "En Baic Center ya hicieron lo difícil.",
        "En Báic Center ya hicieron lo difícil.",
        "Y flotas como la de EPEC.",
        "Y flotas como la de Epec.",
        "Cuatro marcas: BAIC, Arcfox, Mitsubishi y Foton.",
    ] for _ in range(2)],
    "baicenter2": [("lucas", t) for t in [
        "En BAIC Center, ya hicieron lo difícil. Nueve años, cuatro marcas, y flotas como la de EPEC.",
        "En Báic Center ya hicieron lo difícil. Nueve años, cuatro marcas, y flotas como la de EPEC.",
        "En Baik Center ya hicieron lo difícil. Nueve años, cuatro marcas, y flotas como la de EPEC.",
    ] for _ in range(2)],
    # zennonbi-analisis v1: "Zennon", "Dynamics", "Dataverse", "Power Automate", "Power BI", "KickStart" y "API"
    "zennonbi": [(v, t) for v, t in [
        ("paula", "En Zennon implementan Dynamics desde dos mil dieciocho."),
        ("paula", "En Zénon implementan Dynamics desde dos mil dieciocho."),
        ("paula", "Power Automate la pide por ápi, y el resultado vuelve a Dataverse."),
        ("paula", "Power Automate la pide por API, y el resultado vuelve a Dataverse."),
        ("paula", "Un módulo de voz en cada KickStart, medido en Power BI."),
        ("lucas", "Dynamics Sales: el agente llama al lead apenas entra."),
        ("lucas", "Customer Service: el número del cliente atiende a toda hora."),
    ] for _ in range(2)],
}


def env(name):
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"falta {name}")


KEY = env("VLLM_API_KEY")


def tts(voice, text):
    body = json.dumps({"model": env("VLLM_TTS_MODEL"), "voice": voice, "input": text, "response_format": "pcm"}).encode()
    req = urllib.request.Request("http://127.0.0.1:8103/v1/audio/speech", data=body,
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=60).read()


def wav(pcm):
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1, 1, SR, SR * 2, 2, 16,
                       b"data", len(pcm)) + pcm


def stt(path, language="es"):
    bound = "----x"
    data = path.read_bytes()
    body = (f"--{bound}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\n{language}\r\n"
            f"--{bound}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\n"
            f"Content-Type: audio/wav\r\n\r\n").encode() + data + f"\r\n--{bound}--\r\n".encode()
    req = urllib.request.Request("http://127.0.0.1:8102/v1/audio/transcriptions", data=body,
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": f"multipart/form-data; boundary={bound}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["text"]


def f0_semitones(pcm):
    """F0 por autocorrelación en ventanas de 40 ms; devuelve (mediana Hz, desvío en semitonos)."""
    x = np.frombuffer(pcm, "<i2").astype(float) / 32768
    win, hop = int(0.04 * SR), int(0.01 * SR)
    lo, hi = SR // 400, SR // 90
    f0 = []
    rms_all = np.sqrt(np.mean(x ** 2))
    for i in range(0, len(x) - win, hop):
        w = x[i:i + win] * np.hanning(win)
        if np.sqrt(np.mean(w ** 2)) < 0.6 * rms_all:
            continue
        ac = np.correlate(w, w, "full")[win - 1:]
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > 0.45 * ac[0]:
            f0.append(SR / lag)
    f0 = np.array(f0)
    st = 12 * np.log2(f0 / np.median(f0))
    return float(np.median(f0)), float(np.std(st))


def main():
    grupo = sys.argv[1]
    d = OUT / grupo
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, (voz, texto) in enumerate(GRUPOS[grupo]):
        pcm = tts(voz, texto)
        p = d / f"{i:02d}-{voz}.wav"
        p.write_bytes(wav(pcm))
        hz, st = f0_semitones(pcm)
        rows.append((voz, len(pcm) / 2 / SR, hz, st, stt(p), stt(p, "en") if grupo == "api" else "", texto))
    rows.sort(key=lambda r: -r[3]) if grupo == "voces" else None
    for voz, dur, hz, st, txt, txt_en, texto in rows:
        print(f"{voz:10s} {dur:4.1f}s  F0 {hz:5.0f} Hz  ±{st:4.2f} st  | {texto:32s} -> {txt} {('| en: ' + txt_en) if txt_en else ''}")


if __name__ == "__main__":
    main()
