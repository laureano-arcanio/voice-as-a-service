"""Corpus de datos dictados para evaluar STT: emails, direcciones, telefonos
(formato argentino, sin +549) y DNI (8 digitos). Es una referencia de STT,
independiente del agente.

- Textos: --per-category por categoria, con estilos de dictado variados
  (email con punto, junto, con numeros, deletreado; telefono digito a digito
  o de a pares, con o sin 0 y 15; DNI completo, por grupos, de a pares...),
  cada uno dentro de una frase ("Mi mail es ...", "Anotá: ..."). ~60% de las
  direcciones son de Cordoba. Nombres, telefonos y DNI son inventados; las
  calles son reales con alturas inventadas.
- Voces: CosyVoice3 (servicio tts-cosyvoice, perfil `tts-eval`) clonando
  --voices-per-gender hablantes de OpenSLR 61 por genero (ref_audio por
  request: no registra nada en el TTS). Cada texto sale con una voz de mujer y
  una de hombre. Con --tts-url se puede usar otro TTS con la misma API; con
  vllm-tts (Qwen3-TTS) el audio sale con tartamudeos y frases cortadas.
- Canal: las variantes de channel.py, como el corpus de OpenSLR.

Cada texto se valida contra si mismo con entity_match.py (una transcripcion
perfecta tiene que dar 100%), y cada audio se controla con un STT literal
(--qa-url, Parakeet): el TTS a veces tartamudea ("punto co com") o corta la
frase, y esos audios se rehacen con otra semilla. La sintesis queda cacheada en <out>/_tts/: correr
de nuevo solo rehace el canal. manifest.csv tiene categoria, estilo, voz, texto
y el dato esperado; stt_eval.py lo usa para medir el acierto por entidad.

Uso: make stt-corpus-entities [ARGS="--per-category 100"]   (requiere vllm-tts arriba)
     make stt-eval ARGS="--audio-dir scripts/stt_corpus/data/entities/tel8k --runs 1"
"""
import argparse
import base64
import collections
import csv
import random
import re
import unicodedata
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import numpy as np

from app import config
from scripts.stt_corpus import channel, openslr61
from scripts.stt_corpus.entity_match import canon, match
from scripts.stt_eval import _normalize, _spell

OUT_DIR = Path(__file__).resolve().parent / "data" / "entities"
CATEGORIES = ("email", "direccion", "telefono", "dni")

_DIGIT = "cero uno dos tres cuatro cinco seis siete ocho nueve".split()
_LETTER = {"a": "a", "b": "be larga", "c": "ce", "d": "de", "e": "e", "f": "efe", "g": "ge", "h": "hache",
           "i": "i", "j": "jota", "k": "ka", "l": "ele", "m": "eme", "n": "ene", "o": "o", "p": "pe", "q": "cu",
           "r": "erre", "s": "ese", "t": "te", "u": "u", "v": "ve corta", "w": "doble ve", "x": "equis",
           "y": "i griega", "z": "zeta"}

FIRST = ("Juan María Sofía Martín Lucía Florencia Agustín Valentina Gonzalo Camila Facundo Micaela Nicolás "
         "Julieta Santiago Rocío Matías Brenda Ezequiel Yanina Walter Ximena Kevin Yésica Bautista Victoria "
         "Hernán Belén Lautaro Zoe").split()
LAST = ("González Rodríguez Fernández López Martínez Pérez García Sánchez Romero Sosa Álvarez Torres Ruiz "
        "Ramírez Flores Benítez Acosta Medina Herrera Suárez Aguirre Giménez Gutiérrez Pereyra Rojas Molina "
        "Castro Ortiz Silva Luna Juárez Cabrera Ríos Ferreyra Godoy Vázquez Villalba Zabala Quiroga Bustos "
        "Olmos Barrionuevo Echeverría").split()
HANDLES = ("larcanio lauchita negrox tucu flopi juanchi mechi pato kari vicky yamil xime chino colo fede sole "
           "nacho caro rulo gringo").split()
COMPANIES = [("estudio García", "estudiogarcia"), ("ferretería el sol", "ferreteriaelsol"),
             ("distribuidora norte", "distribuidoranorte"), ("agro Córdoba", "agrocordoba"),
             ("taller López", "tallerlopez")]
DOMAINS = [("gmail punto com", "gmail.com", 35), ("hotmail punto com", "hotmail.com", 20),
           ("outlook punto com", "outlook.com", 8), ("yahoo punto com punto ar", "yahoo.com.ar", 8),
           ("hotmail punto com punto ar", "hotmail.com.ar", 5), ("live punto com punto ar", "live.com.ar", 5),
           ("fibertel punto com punto ar", "fibertel.com.ar", 4), ("icloud punto com", "icloud.com", 4),
           ("company", "company", 11)]
EMAIL_PHRASES = ["Mi mail es {e}.", "Sí, mi email es {e}.", "Anotá. {e}.", "Te paso el correo. {e}.", "Es {e}.",
                 "{e}.", "Mi correo es {e}.", "Mandámelo a {e}.", "Eh... mi mail es {e}.",
                 "El mail de la empresa es {e}.", "Escribime a {e}.", "Sí, claro, es {e}."]

CORDOBA = ("Avenida Colón|Avenida Vélez Sarsfield|Bulevar San Juan|Obispo Trejo|Duarte Quirós|"
           "Avenida Hipólito Yrigoyen|Avenida Rafael Núñez|Avenida Fuerza Aérea|Avenida Sabattini|"
           "Bulevar Chacabuco|Rondeau|Independencia|Ituzaingó|Belgrano|Rivera Indarte|Deán Funes|"
           "Avenida Maipú|Avenida Castro Barros|Avenida Monseñor Pablo Cabrera|Humberto Primo|Santa Rosa|"
           "La Rioja|Jujuy|Tucumán|Caseros|Montevideo|Paraná|Chile|Laprida|veintisiete de abril|"
           "nueve de julio|veinticinco de mayo").split("|")
CORDOBA_BARRIOS = ("Nueva Córdoba|Alta Córdoba|General Paz|Güemes|Alberdi|Cerro de las Rosas|Argüello|"
                   "Villa Belgrano|Jardín|San Vicente|Observatorio|Cofico|Villa Cabrera|Centro").split("|")
CORDOBA_TOWNS = [("Villa Carlos Paz", 5152), ("Río Cuarto", 5800), ("Alta Gracia", 5186), ("Villa María", 5900),
                 ("Jesús María", 5220), ("La Calera", 5151)]
TOWN_STREETS = ("San Martín|Avenida San Martín|Belgrano|Rivadavia|Sarmiento|Mitre|Avenida Libertador|"
                "veinticinco de mayo|nueve de julio|Moreno").split("|")
CABA = ("Avenida Corrientes|Avenida Rivadavia|Avenida Cabildo|Avenida Santa Fe|Scalabrini Ortiz|Thames|"
        "Gorriti|Honduras|Billinghurst|Juncal|Arenales|Avenida Belgrano").split("|")
CABA_BARRIOS = "Palermo|Caballito|Almagro|Villa Crespo|Recoleta|Flores|Núñez|Villa Urquiza".split("|")
GBA_TOWNS = [("Quilmes", 1878), ("Lanús", 1824), ("San Isidro", 1642), ("Morón", 1708), ("Banfield", 1828)]
OTHER = [("Bulevar Oroño", "Rosario", 2000), ("Pellegrini", "Rosario", 2000), ("Avenida San Martín", "Mendoza", 5500),
         ("Las Heras", "Mendoza", 5500), ("Avenida Mate de Luna", "San Miguel de Tucumán", 4000),
         ("Avenida Argentina", "Neuquén", 8300), ("Balcarce", "Salta", 4400)]
ADDRESS_PHRASES = ["Vivo en {a}.", "La dirección es {a}.", "Es en {a}.", "Mandalo a {a}.", "Mi domicilio es {a}.",
                   "Sí, anotá. {a}.", "Estoy en {a}.", "La entrega es en {a}.", "{a}.", "Queda en {a}.",
                   "El local está en {a}."]

AREAS = [("11", 8, 25), ("351", 7, 25), ("341", 7, 8), ("261", 7, 7), ("221", 7, 5), ("381", 7, 5),
         ("358", 7, 5), ("3541", 6, 5), ("299", 7, 5), ("223", 7, 5), ("387", 7, 5)]
CEL_PHRASES = ["Mi celular es {n}.", "El número es {n}.", "Anotá. {n}.", "Te paso mi teléfono. {n}.", "Es el {n}.",
               "{n}.", "Llamame al {n}.", "Mi WhatsApp es {n}.", "Sí, es {n}."]
FIJO_PHRASES = ["El fijo es {n}.", "El teléfono de la casa es {n}.", "Anotá el fijo. {n}.", "Es el {n}.", "{n}."]
DNI_PHRASES = ["Mi DNI es {n}.", "El documento es {n}.", "Mi número de documento es {n}.", "{n}.", "Es el {n}.",
               "Sí, {n}.", "DNI {n}.", "Te lo paso. {n}."]


def _ascii(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def _digits(s: str) -> str:
    return " ".join(_DIGIT[int(d)] for d in s)


def _group(s: str) -> str:
    """Un grupo como se lee escrito: "045" -> cero cuarenta y cinco, "007" -> cero cero siete."""
    zeros = len(s) - len(s.lstrip("0"))
    words = ["cero"] * min(zeros, len(s) - 1) + ([_spell(int(s))] if int(s) or zeros < len(s) else ["cero"])
    return " ".join(words)


def _pairs(s: str) -> str:
    return ", ".join(_group(s[i:i + 2]) for i in range(0, len(s), 2))


def _year(rng: random.Random) -> tuple[str, str]:
    y = rng.randint(1965, 2012)
    said = _spell(y) if y >= 2000 or rng.random() < 0.5 else f"{_spell(y // 100)} {_group(str(y % 100).zfill(2))}"
    return said, str(y)


def _capitalize(text: str) -> str:
    """Mayuscula despues de cada punto: asi lee el TTS los deletreos."""
    return re.sub(r"(?<=\. )([a-záéíóúñ])", lambda m: m[1].upper(), text)


def _email(rng: random.Random) -> dict:
    first, last = rng.choice(FIRST), rng.choice(LAST)
    f, l = _ascii(first), _ascii(last)
    style = rng.choices(["punto", "junto", "inicial", "numero", "guion", "apodo", "deletreo"],
                        [25, 15, 10, 20, 10, 10, 10])[0]
    tail = ""
    if style == "punto":
        said, local = f"{first} punto {last}", f"{f}.{l}"
    elif style == "junto":
        said, local, tail = f"{first} {last}", f + l, ", todo junto"
    elif style == "inicial":
        said, local = f"{_LETTER[f[0]]} {last}", f[0] + l
    elif style == "numero":
        if rng.random() < 0.5:
            n = str(rng.randint(10, 99))
            num_said = _spell(int(n)) if rng.random() < 0.6 else _digits(n)
        else:
            num_said, n = _year(rng)
        said, local = f"{first} {last} {num_said}", f + l + n
    elif style == "guion":
        sep, sep_said = rng.choice([("_", "guion bajo"), ("-", "guion medio")])
        said, local = f"{first} {sep_said} {last}", f + sep + l
    elif style == "apodo":
        local = rng.choice(HANDLES)
        said = local
        if rng.random() < 0.5:
            n = str(rng.randint(1, 99))
            said, local = f"{said} {_spell(int(n))}", local + n
    else:
        local = rng.choice(HANDLES + [l])
        said = ". ".join(_LETTER[c] for c in local).capitalize() + "."  # "Ele. A. U. Ce." (con comas el TTS lo lee mal)
    dom_said, dom, _ = rng.choices(DOMAINS, [d[2] for d in DOMAINS])[0]
    if dom == "company":
        name_said, name = rng.choice(COMPANIES)
        dom_said, dom = f"{name_said} punto com punto ar", f"{name}.com.ar"
    email_said = f"{said} arroba {dom_said}{tail}"
    return {"style": style, "text": _capitalize(rng.choice(EMAIL_PHRASES).format(e=email_said)),
            "expected": f"{local}@{dom}"}


def _house_number(rng: random.Random) -> str:
    n = rng.choice([rng.randint(100, 999), rng.randint(1000, 5999)])
    if n >= 1000 and n % 100 and rng.random() < 0.5:  # "doce treinta y cuatro"
        return f"{_spell(n // 100)} {_group(str(n % 100).zfill(2))}"
    return _spell(n)


def _address(rng: random.Random) -> dict:
    # Calle, barrio y localidad coherentes: barrios solo en Cordoba capital y CABA.
    region = rng.choices(["cordoba", "cordoba-interior", "caba", "gba", "otra"], [45, 15, 17, 8, 15])[0]
    barrio = cross = None
    if region == "cordoba":
        street, barrio, town, cp = rng.choice(CORDOBA), rng.choice(CORDOBA_BARRIOS), rng.choice(
            ["Córdoba", "Córdoba capital"]), 5000
        cross = rng.sample(CORDOBA[:29], 2)
    elif region == "cordoba-interior":
        street, (town, cp) = rng.choice(TOWN_STREETS), rng.choice(CORDOBA_TOWNS)
    elif region == "caba":
        street, barrio, town, cp = rng.choice(CABA), rng.choice(CABA_BARRIOS), rng.choice(
            ["Capital Federal", "Buenos Aires", "CABA"]), 1414
        cross = rng.sample(CABA, 2)
    elif region == "gba":
        street, (town, cp) = rng.choice(TOWN_STREETS), rng.choice(GBA_TOWNS)
    else:
        street, town, cp = rng.choice(OTHER)
    core = f"{street} {_house_number(rng)}"
    parts = [core]
    if rng.random() < 0.4:
        floor, letter = rng.randint(1, 9), rng.choice("ABCDEF")
        ordinal = "primero segundo tercero cuarto quinto sexto séptimo octavo noveno".split()[floor - 1]
        parts.append(rng.choice([f"piso {_spell(floor)}, departamento {letter}", f"{ordinal} {letter}"]))
    if barrio and rng.random() < 0.35:
        parts.append(f"barrio {barrio}")
    if cross and rng.random() < 0.15:
        parts.append(f"entre {cross[0]} y {cross[1]}")
    if rng.random() < 0.6:
        parts.append(town)
    if rng.random() < 0.1:
        parts.append(f"código postal {_spell(cp)}")
    address = ", ".join(parts)
    return {"style": region, "text": _capitalize(rng.choice(ADDRESS_PHRASES).format(a=address)), "expected": address,
            "expected_core": core}


def _phone(rng: random.Random) -> dict:
    area, length, _ = rng.choices(AREAS, [a[2] for a in AREAS])[0]
    number = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(length - 1))
    style = rng.choices(["cel15", "cel10", "fijo"], [40, 30, 30])[0]
    zero = style != "cel10" and rng.random() < 0.3
    area_said = rng.choice(["once", "uno uno"]) if area == "11" else (
        _spell(int(area)) if len(area) == 3 and rng.random() < 0.1 else _digits(area))
    # 7 digitos: 456 78 90; 8 (CABA): 45 67 89 01; 6: 456 789.
    mode = rng.choices(["digitos", "pares", "grupos"], [35, 45, 20])[0]
    if mode == "digitos":
        num_said = _digits(number)
    elif length == 8:
        num_said = _pairs(number)
    elif length == 7:
        head = _digits(number[:3]) if mode == "pares" else _group(number[:3])
        num_said = f"{head}, {_pairs(number[3:])}"
    else:
        num_said = _pairs(number) if mode == "pares" else f"{_group(number[:3])}, {_group(number[3:])}"
    said = ", ".join(filter(None, ["cero" if zero else "", area_said, "quince" if style == "cel15" else "", num_said]))
    if style == "fijo" and rng.random() < 0.4:  # solo el numero local
        said, digits = num_said, number
    else:
        digits = ("0" if zero else "") + area + ("15" if style == "cel15" else "") + number
    phrases = FIJO_PHRASES if style == "fijo" else CEL_PHRASES
    return {"style": f"{style}/{mode}", "text": _capitalize(rng.choice(phrases).format(n=said)), "expected": digits}


def _dni(rng: random.Random) -> dict:
    n = rng.randint(20_000_000, 46_999_999) if rng.random() < 0.85 else rng.randint(10_000_000, 19_999_999)
    if rng.random() < 0.2:  # algun grupo con ceros adelante: 30.045.007
        s = list(str(n))
        s[rng.choice([2, 5])] = "0"
        n = int("".join(s))
    s = str(n)
    style = rng.choices(["completo", "grupos", "pares", "digitos"], [30, 35, 15, 20])[0]
    said = {"completo": lambda: _spell(n), "grupos": lambda: f"{_group(s[:2])}, {_group(s[2:5])}, {_group(s[5:])}",
            "pares": lambda: _pairs(s), "digitos": lambda: _digits(s)}[style]()
    return {"style": style, "text": _capitalize(rng.choice(DNI_PHRASES).format(n=said)), "expected": s}


def _items(per_category: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    gen = {"email": _email, "direccion": _address, "telefono": _phone, "dni": _dni}
    items = []
    for cat in CATEGORIES:
        seen = set()
        while sum(i["category"] == cat for i in items) < per_category:
            item = gen[cat](rng)
            if item["expected"] in seen:
                continue
            seen.add(item["expected"])
            item["category"] = cat
            ok, core_ok = match(cat, item["text"], item["expected"], item.get("expected_core", ""))
            if not (ok and core_ok):  # una transcripcion perfecta tiene que dar bien
                raise SystemExit(f"el texto no valida contra su dato esperado: {item}")
            items.append(item)
    return items


def _voices(client: httpx.Client, per_gender: int, seed: int, out: Path) -> list[dict]:
    """Voces de referencia: por hablante, sus 2 frases mas largas (~8-12 s) pegadas."""
    index = openslr61.load_index(client)
    rng = random.Random(seed)
    voices = []
    for g in openslr61.GENDERS:
        for speaker in sorted(rng.sample(sorted(index[g]), per_gender)):
            clips = sorted(index[g][speaker], key=lambda c: -len(c[1]))[:2]
            voices.append({"gender": g, "speaker": speaker, "clips": clips})
    src = openslr61.OUT_DIR / "_src"
    openslr61.fetch(client, [{"utt": u, "gender": v["gender"]} for v in voices for u, _ in v["clips"]], src)
    (out / "_voices").mkdir(parents=True, exist_ok=True)
    for v in voices:
        parts = []
        for utt, _ in v["clips"]:
            x, sr = channel.read_wav(src / f"{utt}.wav")
            parts += [channel.resample(x, sr, 24000), np.zeros(7200)]
        ref = channel.normalize(np.concatenate(parts[:-1]), 24000)
        path = out / "_voices" / f"{v['gender']}{v['speaker']}.wav"
        channel.write_wav(path, ref, 24000)
        v["ref_text"] = " ".join(t for _, t in v["clips"])
        v["ref_audio"] = "data:audio/wav;base64," + base64.b64encode(path.read_bytes()).decode()
        path.with_suffix(".txt").write_text(v["ref_text"] + "\n")
    return voices


def _synthesize(client: httpx.Client, url: str, row: dict, voice: dict, path: Path, attempt: int,
                model: str, instruct: str) -> None:
    ref_text = voice["ref_text"]
    if instruct:
        # CosyVoice3 toma como instruccion lo que va antes de <|endofprompt|>; sin
        # esto el server pone "You are a helpful assistant." y en los deletreos a
        # veces se le escapa el idioma (lee con acento de otra lengua).
        ref_text = f"{instruct}<|endofprompt|>{ref_text}"
    r = client.post(f"{url}/audio/speech", json={
        "model": model, "input": row["text"], "task_type": "Base", "language": "Spanish",
        "ref_audio": voice["ref_audio"], "ref_text": ref_text, "response_format": "wav",
        "seed": zlib.crc32(row["utt"].encode()) % 2**31 + 1000 * attempt})
    r.raise_for_status()
    path.write_bytes(r.content)


def _defects(text: str, hyp: str, ratio: float) -> list[str]:
    """Defectos del TTS en una transcripcion literal (Parakeet): el modelo a veces
    tartamudea ("punto co com") o corta el principio o el final de la frase.
    Un STT con decoder LLM (Qwen) los tapa, asi que hace falta uno literal."""
    ref, h = _normalize(text), _normalize(hyp)
    out = []
    for i, t in enumerate(h):  # "punto punto", "cocom"
        if i and t == h[i - 1] and h.count(t) > ref.count(t):
            out.append(f"repite {t}")
        elif any(t[:k] == t[k:2 * k] for k in range(2, len(t) // 2 + 1)) and t not in ref:
            out.append(f"repite {t}")
    # Cortado: cuanto del contenido aparece, caracter a caracter sobre la forma
    # canonica. No cuenta palabras: un STT literal pega ("arrobaliv.com.ar") y
    # escribe simbolos ("." por "punto"), y eso no es un defecto del audio.
    a, b = "".join(canon(text)), "".join(canon(hyp))
    lcs = [0] * (len(b) + 1)
    for ca in a:
        prev = 0
        for j, cb in enumerate(b, 1):
            prev, lcs[j] = lcs[j], (prev + 1 if ca == cb else max(lcs[j], lcs[j - 1]))
    # 0.55: el STT literal se come letras y pega palabras en los dictados, asi
    # que con el umbral alto (0.85) marcaba 200 audios buenos. Por debajo de
    # 0.55 el audio esta realmente cortado o mudo (medido sobre el corpus).
    if a and lcs[-1] / len(a) < 0.55:
        out.append(f"cortado ({lcs[-1] / len(a):.0%} del texto)")
    if not 0.6 <= ratio <= 1.6:  # p05-p95 del corpus: 0.68-1.45
        out.append(f"duracion {ratio:.2f}")
    return out


def _ratios(rows: list[dict], out: Path) -> None:
    """Duracion de cada audio contra lo que predice la velocidad de su propia voz
    (silabas y pausas): detecta cortes y alargues."""
    for r in rows:
        x, sr = channel.read_wav(out / "_tts" / f"{r['utt']}.wav")
        r["dur"] = len(x) / sr
        r["x"] = [len(re.findall(r"[aeiouáéíóúü]+", r["text"].lower())), r["text"].count(",") + r["text"].count("."), 1]
    for voice in {r["speaker"] for r in rows}:
        xs = [r for r in rows if r["speaker"] == voice]
        w = np.linalg.lstsq(np.array([r["x"] for r in xs]), np.array([r["dur"] for r in xs]), rcond=None)[0]
        for r in xs:
            r["ratio"] = r["dur"] / float(np.array(r["x"]) @ w)


def _transcribe(client: httpx.Client, url: str, path: Path) -> str:
    r = client.post(f"{url}/audio/transcriptions", files={"file": ("a.wav", path.read_bytes(), "audio/wav")},
                    data={"model": "x", "language": "es", "response_format": "json"})
    r.raise_for_status()
    return r.json()["text"]


def _qa(client: httpx.Client, rows: list[dict], args: argparse.Namespace) -> None:
    """Controla cada audio con un STT literal y rehace los defectuosos, hasta --qa-rounds veces."""
    try:
        client.get(f"{args.qa_url}/models", timeout=10).raise_for_status()
    except httpx.HTTPError as e:
        print(f"QA: {args.qa_url} no responde ({e!r}); sigo sin controlar el audio", flush=True)
        for r in rows:
            r["qa"] = "sin-qa"
        return
    pending = rows
    for attempt in range(1, args.qa_rounds + 1):
        _ratios(rows, args.out)
        with ThreadPoolExecutor(args.workers) as pool:
            hyps = list(pool.map(lambda r: _transcribe(client, args.qa_url, args.out / "_tts" / f"{r['utt']}.wav"), pending))
        bad = []
        for r, hyp in zip(pending, hyps):
            defects = _defects(r["text"], hyp, r["ratio"])
            r["qa"] = "ok" if not defects else "; ".join(defects)
            if defects:
                bad.append(r)
        print(f"QA ronda {attempt}: {len(bad)} de {len(pending)} con defectos", flush=True)
        if not bad or attempt == args.qa_rounds:
            for r in bad:
                r["qa"] = "defecto: " + r["qa"]
            return
        with ThreadPoolExecutor(args.workers) as pool:
            list(pool.map(lambda r: _synthesize(client, args.tts_url, r, r["voice"], args.out / "_tts" / f"{r['utt']}.wav",
                                                attempt, args.tts_model, args.instruct), bad))
        pending = bad


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--per-category", type=int, default=100, help="textos por categoria (default 100)")
    p.add_argument("--voices-per-gender", type=int, default=10, help="voces clonadas por genero (default 10)")
    p.add_argument("--workers", type=int, default=8, help="sintesis en paralelo (default 8)")
    p.add_argument("--timeout", type=float, default=900, help="timeout por request al TTS, en segundos")
    p.add_argument("--tts-url", default="http://tts-cosyvoice:8000/v1", help="TTS que genera el corpus")
    p.add_argument("--tts-model", default="FunAudioLLM/Fun-CosyVoice3-0.5B-2512")
    p.add_argument("--instruct", default="Hablás en español rioplatense, con acento argentino.",
                   help="instruccion de estilo para el TTS (CosyVoice3); vacio = default del server")
    p.add_argument("--qa-url", default="http://stt-parakeet:8000/v1",
                   help="STT literal que controla el audio sintetizado (default: stt-parakeet)")
    p.add_argument("--qa-rounds", type=int, default=3, help="intentos por audio defectuoso (0 = sin control)")
    p.add_argument("--force", action="store_true", help="rehacer la sintesis aunque este cacheada (ej. al cambiar de TTS)")
    p.add_argument("--out", type=Path, default=OUT_DIR)
    channel.add_args(p)
    args = p.parse_args()

    items = _items(args.per_category, args.seed)
    rows = []
    headers = {"Authorization": f"Bearer {config.VLLM_API_KEY}"}
    # Timeout alto: con --workers alto, un pedido puede esperar varios minutos en
    # la cola del TTS antes de que le toque (con 180s cortaba a mitad de corrida).
    with httpx.Client(timeout=args.timeout, follow_redirects=True, headers=headers) as client:
        voices = _voices(client, args.voices_per_gender, args.seed, args.out)
        by_g = {g: [v for v in voices if v["gender"] == g] for g in openslr61.GENDERS}
        pos: dict[str, int] = {}
        for i, item in enumerate(items):
            pos[item["category"]] = idx = pos.get(item["category"], -1) + 1
            for k, g in enumerate(openslr61.GENDERS):  # una voz de mujer y una de hombre, rotando
                v = by_g[g][(i + 3 * k) % len(by_g[g])]
                rows.append({**item, "utt": f"{item['category']}_{idx:03d}_{g}{v['speaker']}",
                             "gender": g, "speaker": v["speaker"], "voice": v})
        (args.out / "_tts").mkdir(parents=True, exist_ok=True)
        todo = [r for r in rows if args.force or not (args.out / "_tts" / f"{r['utt']}.wav").exists()]
        print(f"{len(items)} textos x 2 voces = {len(rows)} audios; a sintetizar: {len(todo)}", flush=True)

        def job(r):
            _synthesize(client, args.tts_url, r, r["voice"], args.out / "_tts" / f"{r['utt']}.wav", 0,
                        args.tts_model, args.instruct)

        with ThreadPoolExecutor(args.workers) as pool:
            for n, _ in enumerate(pool.map(job, todo), 1):
                if n % 100 == 0:
                    print(f"  {n}/{len(todo)}", flush=True)
        if args.qa_rounds:
            _qa(client, rows, args)

    for r in rows:
        x, sr = channel.read_wav(args.out / "_tts" / f"{r['utt']}.wav")
        r.update(channel.write_variants(x, sr, args.out, r["utt"], r["text"], args))
        r.setdefault("qa", "sin-qa")
    cols = ["utt", "category", "style", "gender", "speaker", "duration_s", "lost_packets", "cuts", "qa",
            "expected", "expected_core", "text"]
    with open(args.out / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    hours = sum(r["duration_s"] for r in rows) / 3600
    qa = collections.Counter(r["qa"].split(":")[0].split(" (")[0] for r in rows)
    print(f"listo: {len(rows)} audios ({', '.join(f'{c} {args.per_category}' for c in CATEGORIES)} textos x 2 voces; "
          f"{len(voices)} voces), {hours:.2f} h x {len(channel.VARIANTS)} variantes en {args.out}")
    print(f"QA del audio: {dict(qa)}")
    print(channel.summary(rows, args))


if __name__ == "__main__":
    main()
