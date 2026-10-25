"""Locución de un proyecto de video con el TTS propio (vllm-tts local, docs/VIDEOS.md).

Lee proyectos/<proyecto>/guion.json ({"lineas": [{"id", "voz", "texto"}]}) y escribe en
public/proyectos/<proyecto>/vo/: <id>.wav, duraciones.json y envolventes.json (nivel por frame a 30 fps,
para mover las bocas de los personajes).

Uso: python3 scripts/voces.py <proyecto> [--tomas N] [id ...]   (sin ids, todas las líneas)
Con --tomas genera N tomas por línea, las transcribe con el STT propio y se queda con la más fiel al texto.
"""
import difflib
import json
import os
import struct
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REPO = RAIZ.parents[1]
SR = 24000
TTS_URL = os.environ.get("TTS_URL", "http://127.0.0.1:8103/v1")
STT_URL = os.environ.get("STT_URL", "http://127.0.0.1:8102/v1")

# Cómo se escribe para que el TTS lo pronuncie -> cómo lo escribe el STT (para medir la fidelidad)
GRAFIAS = {"ópen, ei, ái": "OpenAI", "yéison": "JSON", "Báic": "Bike",  # BAIC se escribe "Báic" (baicenter-analisis)
           "Ese Cu Ele": "SQL",  # SQL se escribe "Ese Cu Ele" (sqlamoblamientos-analisis)
           "ese de ká": "SDK"}  # SDK (api-desarrolladores)


def env(name):
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"falta {name} en .env")


def wav(pcm: bytes) -> bytes:
    head = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1, 1, SR,
                       SR * 2, 2, 16, b"data", len(pcm))
    return head + pcm


def tts(key, model, voz, texto):
    # Siempre con una voz del checkpoint: sin `voice` el engine de vllm-tts se cae (AGENTS.md)
    body = json.dumps({"model": model, "voice": voz, "input": texto, "response_format": "pcm"}).encode()
    req = urllib.request.Request(f"{TTS_URL}/audio/speech", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=60).read()


def acelerar(pcm: bytes, factor: float) -> bytes:
    """Acelera el PCM (s16le, 24 kHz, mono) sin cambiar el tono (ffmpeg atempo)."""
    if abs(factor - 1) < 1e-3:
        return pcm
    cmd = ["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
           "-filter:a", f"atempo={factor}", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-"]
    return subprocess.run(cmd, input=pcm, capture_output=True, check=True).stdout


def _letras(t):
    t = t.lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        t = t.replace(a, b)
    return "".join(c for c in t if c.isalnum())


def transcribir(key, wav_bytes, language="es"):
    bound = "----toma"
    body = (f"--{bound}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\n{language}\r\n"
            f"--{bound}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\n"
            "Content-Type: audio/wav\r\n\r\n").encode() + wav_bytes + f"\r\n--{bound}--\r\n".encode()
    req = urllib.request.Request(f"{STT_URL}/audio/transcriptions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": f"multipart/form-data; boundary={bound}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["text"]


def fidelidad(key, wav_bytes, texto):
    """Transcribe la toma y la compara con el texto (0..1)."""
    for a, b in GRAFIAS.items():
        texto = texto.replace(a, b)
    oido = transcribir(key, wav_bytes)
    return difflib.SequenceMatcher(None, _letras(texto), _letras(oido)).ratio(), oido


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        raise SystemExit(__doc__)
    proyecto, args = args[0], args[1:]
    tomas = 1
    if args[:1] == ["--tomas"]:
        tomas, args = int(args[1]), args[2:]
    datos = json.loads((RAIZ / "proyectos" / proyecto / "guion.json").read_text())
    guion = datos["lineas"]
    velocidad = float(datos.get("velocidad", 1))  # "velocidad": 1.1 acelera la locución sin cambiar el tono
    # "ganancia_db": -2 baja el nivel de la locución (una voz más fuerte que lucas saca la mezcla de -16 LUFS)
    ganancia = 10 ** (float(datos.get("ganancia_db", 0)) / 20)
    out = RAIZ / "public" / "proyectos" / proyecto / "vo"
    out.mkdir(parents=True, exist_ok=True)
    key, model = env("VLLM_API_KEY"), env("VLLM_TTS_MODEL")
    pedidas = set(args)
    for linea in guion:
        id_, voz, texto = linea["id"], linea["voz"], linea["texto"]
        if pedidas and id_ not in pedidas:
            continue
        mejor = None
        for _ in range(tomas):
            pcm = tts(key, model, voz, texto)
            puntaje, oido = fidelidad(key, wav(pcm), texto)
            if mejor is None or puntaje > mejor[0]:
                mejor = (puntaje, oido, pcm)
        puntaje, oido, pcm = mejor
        pcm = acelerar(pcm, velocidad)
        if ganancia != 1:
            pcm = b"".join(struct.pack("<h", max(-32768, min(32767, round(v[0] * ganancia)))) for v in struct.iter_unpack("<h", pcm))
        (out / f"{id_}.wav").write_bytes(wav(pcm))
        print(f"{id_} {voz:9s} {len(pcm) / 2 / SR:5.2f} s  {texto}\n    {puntaje:.2f} -> {oido}")

    # Duraciones y envolventes de todas las líneas del guion (también de las que no se regeneraron)
    dur, envs = {}, {}
    for linea in guion:
        raw = (out / f"{linea['id']}.wav").read_bytes()[44:]
        dur[linea["id"]] = round(len(raw) / (2 * SR), 3)
        s = [v[0] / 32768 for v in struct.iter_unpack("<h", raw[: len(raw) // 2 * 2])]
        paso = SR // 30
        rms = [(sum(x * x for x in s[i:i + paso]) / paso) ** 0.5 for i in range(0, len(s), paso)]
        top = max(rms) or 1
        envs[linea["id"]] = [round(min(1, v / top * 1.2), 2) for v in rms]
    (out / "duraciones.json").write_text(json.dumps(dur, indent=2))
    (out / "envolventes.json").write_text(json.dumps(envs))
    print(f"total voz: {sum(dur.values()):.1f} s")


if __name__ == "__main__":
    main()
