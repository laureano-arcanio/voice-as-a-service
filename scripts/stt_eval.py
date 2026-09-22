"""Compara el STT candidato levantado (perfil `stt-eval` de docker-compose.yml,
de a uno) contra el actual (vllm-stt) sobre el mismo corpus: WER y latencia
por request. Los engines que no responden se saltean.

Manda cada .wav como lo haria el agente (POST /v1/audio/transcriptions,
language=es, VLLM_API_KEY), de a un request por vez: mide latencia de
inferencia SIN carga, no throughput. Para ver como se comporta uno bajo carga,
apuntar el agente a el (ver .env.example) y correr `make loadtest`.

Corpus: por defecto el del load test (scripts/loadtest/audio, voz sintetica
del propio vllm-tts), con UTTERANCES de gen_audio.py como referencia. Con
--audio-dir se usa otro: cada X.wav con su transcript correcto en X.txt al
lado (ej. recortes de llamadas reales). --telephone degrada el audio a 8kHz
mu-law, que es lo que llega en una llamada real por Anura/Asterisk. Si la
carpeta tiene al lado un manifest.csv con datos (corpus de
scripts/stt_corpus/entities.py), reporta tambien el acierto del dato completo:
email, telefono, DNI, direccion.

El WER se calcula sobre texto normalizado (minusculas, sin tildes ni
puntuacion): "Si." y "sí" cuentan como la misma palabra. Los numeros en
digitos y romanos se pasan a palabras ("1936" -> "mil novecientos treinta y
seis", "XVII" -> "diecisiete"), igual que "veintiún/veintiuna" y
"doscientas": son formas de escribir lo mismo, no errores.

Uso: make stt-eval   /   make stt-eval ARGS="--telephone --runs 5"
"""
import argparse
import audioop
import collections
import csv
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
from scripts.stt_corpus.entity_match import match

# nombre -> (base_url, model). vllm-stt va con su URL/modelo de compose y no
# con los de config: si .env apunta el agente a un candidato, igual se compara
# contra Qwen3-ASR.
ENGINES = {
    "qwen3-asr": ("http://vllm-stt:8000/v1", os.getenv("VLLM_STT_MODEL", "Qwen/Qwen3-ASR-1.7B")),
    "parakeet": ("http://stt-parakeet:8000/v1", "nvidia/parakeet-tdt-0.6b-v3"),
    "whisper-turbo": ("http://stt-whisper:8000/v1", "openai/whisper-large-v3-turbo"),
}

# Mismo bug de qwenllm/qwen3-asr que parchea app/livekit_agent.py: el
# transcript viene con el template interno antepuesto.
_ASR_TEMPLATE_PREFIX_RE = re.compile(r"^language\s+\S+<asr_text>")


# Con tildes: _spell tambien arma el texto que lee el TTS en scripts/stt_corpus/entities.py
# (para comparar, _normalize las saca).
_UNITS = ("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince "
          "dieciséis diecisiete dieciocho diecinueve veinte veintiuno veintidós veintitrés veinticuatro "
          "veinticinco veintiséis veintisiete veintiocho veintinueve").split()
_TENS = "_ _ _ treinta cuarenta cincuenta sesenta setenta ochenta noventa".split()
_HUNDREDS = "_ ciento doscientos trescientos cuatrocientos quinientos seiscientos setecientos ochocientos novecientos".split()
# Variantes de genero/apocope que dicen el mismo numero: "veintiun grados", "doscientas personas".
_CANON = {"veintiun": "veintiuno", "veintiuna": "veintiuno",
          **{h[:-2] + "as": h for h in _HUNDREDS[2:]}}
_ROMAN = re.compile(r"\b(?=[IVXLC]{2,}\b)(C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\b")
_NUMBER = re.compile(r"\d{1,3}(?:[.,]\d{3})+(?![.,]?\d)|\d+(?:[.,]\d+)?")


def _below_1000(n: int) -> str:
    if n == 100:
        return "cien"
    h, r = divmod(n, 100)
    words = [_HUNDREDS[h]] if h else []
    if r >= 30:
        t, u = divmod(r, 10)
        words.append(_TENS[t] + (f" y {_UNITS[u]}" if u else ""))
    elif r or not h:
        words.append(_UNITS[r])
    return " ".join(words)


def _spell(n: int) -> str:
    """Entero en palabras, como se dice en voz: 1936 -> mil novecientos treinta y seis."""
    if n < 1000:
        return _below_1000(n)
    for size, one, many in ((10**6, "un millón", "millones"), (1000, "mil", "mil")):
        if n >= size:
            high, low = divmod(n, size)
            # Apocope delante de mil/millones: "veintiún mil", "treinta y un millones".
            head = one if high == 1 else re.sub(r"veintiuno$", "veintiún", re.sub(r"(?<!veinti)uno$", "un", _spell(high))) + f" {many}"
            return head + (f" {_spell(low)}" if low else "")


def _spell_numbers(text: str) -> str:
    """Numeros en digitos (y romanos) a palabras: Whisper escribe "Hace 14 grados"
    y "siglo XVII" donde la referencia dice "catorce" y "diecisiete"."""
    def roman(m):
        # Solo "XVII", "III"... o "siglo XX": "talle XL" o "CC" no son numeros.
        if not re.search(r"[IV]", m[0]) and not re.search(r"siglo\s*$", m.string[:m.start()], re.I):
            return m[0]
        c, x, i = m.groups()
        value = sum({"C": 100, "XC": 90, "XL": 40, "L": 50, "X": 10, "IX": 9, "IV": 4, "V": 5, "I": 1}.get(s, 0)
                    for s in re.findall(r"XC|XL|IX|IV|[CLXVI]", c + x + i))
        return _spell(value) if value else m[0]

    def number(m):
        s = m[0]
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):  # separador de miles: 3.000, 1,000
            return _spell(int(re.sub(r"[.,]", "", s)))
        whole, _, frac = re.split(r"([.,])", s, maxsplit=1) if re.search(r"[.,]", s) else (s, "", "")
        return _spell(int(whole)) + (f" coma {_spell(int(frac))}" if frac else "")

    text = re.sub(r"(\d)\s*%", r"\1 por ciento", _ROMAN.sub(roman, text))
    return _NUMBER.sub(number, text)


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_EMAIL_SYMBOLS = {"@": " arroba ", ".": " punto ", "_": " guion bajo ", "-": " guion medio "}


def _normalize(text: str) -> list[str]:
    # "larcanio@gmail.com" -> "larcanio arroba gmail punto com", como se dicta.
    text = _EMAIL.sub(lambda m: re.sub(r"[@._-]", lambda c: _EMAIL_SYMBOLS[c[0]], m[0]), text)
    text = unicodedata.normalize("NFD", _spell_numbers(text).lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return [_CANON.get(w, w) for w in re.sub(r"[^\w\s]", " ", text).split()]


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


def _entities(audio_dir: Path | None) -> dict[str, tuple[str, str, str, str]]:
    """{utt: (categoria, dato esperado, nucleo, qa)} si el corpus trae manifest.csv
    con datos (scripts/stt_corpus/entities.py); si no, vacio."""
    path = audio_dir.parent / "manifest.csv" if audio_dir else None
    if not path or not path.exists():
        return {}
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if not rows or "expected" not in rows[0]:
        return {}
    return {r["utt"]: (r["category"], r["expected"], r.get("expected_core", ""), r.get("qa", "ok"))
            for r in rows}


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
    parser.add_argument("--include-defects", action="store_true",
                        help="contar tambien los audios marcados con defecto de TTS en el manifest")
    args = parser.parse_args()

    corpus = _corpus(args.audio_dir)
    entities = _entities(args.audio_dir)
    # Los audios que el control marco defectuosos (columna qa del manifest) miden
    # el TTS que los genero, no el STT: por default no cuentan para el acierto.
    skip_bad = not args.include_defects
    bad = sum(v[3] != "ok" for v in entities.values())
    if entities and bad and skip_bad:
        print(f"(se saltean {bad} audios con defecto de TTS; --include-defects los cuenta)")
    hits = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))  # engine -> cat -> [ok, nucleo, n]
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
                if name in entities and not (skip_bad and entities[name][3] != "ok"):
                    cat, expected, core, _ = entities[name]
                    ok, core_ok = match(cat, hyp, expected, core)
                    h = hits[engine][cat]
                    h[0], h[1], h[2] = h[0] + ok, h[1] + core_ok, h[2] + 1
                    if not ok:
                        print(f"     {'':10s} {'dato':>7s}  esperado {expected!r}")
            summary.append((engine, errors / max(ref_words, 1), statistics.median(latencies),
                            _pct(latencies, 0.9), statistics.median(rtfs)))

    print(f"\nResumen{' (audio telefonico 8kHz mu-law)' if args.telephone else ''}"
          f" -- {len(corpus)} audios x {args.runs} runs, requests de a uno:")
    print(f"  {'engine':15s} {'WER':>6s} {'p50':>7s} {'p90':>7s} {'RTF p50':>8s}")
    for engine, wer, p50, p90, rtf in summary:
        print(f"  {engine:15s} {wer:6.1%} {p50 * 1000:5.0f}ms {p90 * 1000:5.0f}ms {rtf:8.3f}")
    if hits:
        cats = sorted({c for h in hits.values() for c in h})
        print("\nDatos -- acierto del dato completo (direccion: completa / calle + altura):")
        print(f"  {'engine':15s} " + " ".join(f"{c:>16s}" for c in cats))
        for engine, h in hits.items():
            cells = [f"{h[c][0] / h[c][2]:.0%}" + (f" / {h[c][1] / h[c][2]:.0%}" if c == "direccion" else "")
                     + f" (n={h[c][2]})" for c in cats]
            print(f"  {engine:15s} " + " ".join(f"{x:>16s}" for x in cells))


if __name__ == "__main__":
    main()
