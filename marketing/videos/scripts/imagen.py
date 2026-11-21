"""Imágenes fijas para un proyecto de video, con la API de imágenes local (vLLM-Omni + Qwen-Image-2.1).

Escribe el PNG en public/proyectos/<proyecto>/img/<nombre>.png y anota la generación (prompt final,
tamaño, pasos, semilla, modelo y tiempo) en proyectos/<proyecto>/imagenes.json.

Límites (los hace cumplir este script): lado máximo 1024 px, área máxima 1024x1024 y 12 pasos.
Formatos: 1:1, 16:9, 9:16, 4:3, 3:4, 4:5, 5:4, 3:2, 2:3, 2:1, 21:9 (o --size WxH).
Estilos: foto, ilustracion, caricatura, 3d, anime, linea, isometrico, storyboard, pixel, marca
o --estilo-libre "texto".

Uso: python3 scripts/imagen.py <proyecto> <nombre> --prompt "..." [--formato 16:9] [--estilo foto]
     [--pasos 12] [--seed N] [--size 1024x576] [--con-texto] [--estilo-libre "..."] [--dry-run]
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = os.environ.get("ATENTINA_IMG_API", "http://192.168.1.99:8210/v1").rstrip("/")
MODELO = os.environ.get("ATENTINA_IMG_MODEL", "/models/Qwen-Image-2.1")

LADO_MAX = 1024
AREA_MAX = 1024 * 1024
PASOS_MAX = 12
MULTIPLO = 32

FORMATOS = {
    "1:1": (1024, 1024),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "4:3": (1024, 768),
    "3:4": (768, 1024),
    "4:5": (832, 1024),
    "5:4": (1024, 832),
    "3:2": (1024, 672),
    "2:3": (672, 1024),
    "2:1": (1024, 512),
    "21:9": (1024, 448),
}

ESTILOS = {
    "foto": "photorealistic editorial photography, natural light, 50 mm lens, shallow depth of field, fine texture",
    "ilustracion": "flat vector illustration, fully colored limited palette, bold simple shapes, subtle gradients, generous margins",
    "caricatura": "colorful cartoon caricature, fully colored flat palette, thick clean outlines, expressive features, simple background",
    "3d": "stylized 3d render, soft studio lighting, smooth materials, subtle shadows",
    "anime": "anime style, clean line art, cel shading, expressive eyes",
    "linea": "minimal line-art icon, single accent color, generous white space",
    "isometrico": "isometric illustration, flat palette, 45 degree projection",
    "storyboard": "black and white storyboard sketch, marker shading, loose lines",
    "pixel": "16-bit pixel art, limited palette, crisp pixels",
    "marca": "Atentina brand graphic: white background with a light dot grid, accent blue #2456e6, "
             "flat geometric shapes, generous margins, no photographic texture",
}

SIN_TEXTO = "no text, no lettering, no words, no watermarks, no logos"


def err(msg):
    raise SystemExit(msg)


def parsear(argv):
    if len(argv) < 3:
        err(__doc__)
    proyecto, nombre = argv[1], argv[2]
    opts = {"proyecto": proyecto, "nombre": nombre, "formato": "1:1", "estilo": "foto",
            "pasos": PASOS_MAX, "seed": None, "size": None, "con_texto": False,
            "estilo_libre": None, "dry_run": False, "prompt": None}
    i = 3
    while i < len(argv):
        a = argv[i]
        if a in ("--prompt", "--formato", "--estilo", "--pasos", "--seed", "--size", "--estilo-libre"):
            if i + 1 >= len(argv):
                err(f"falta el valor de {a}")
            v = argv[i + 1]
            key = a[2:].replace("-", "_")
            opts[key] = int(v) if key in ("pasos", "seed") else v
            i += 2
        elif a == "--con-texto":
            opts["con_texto"] = True
            i += 1
        elif a == "--dry-run":
            opts["dry_run"] = True
            i += 1
        else:
            err(f"opción desconocida: {a}\n\n{__doc__}")
    if not opts["prompt"]:
        err("falta --prompt \"<qué se ve>\"")
    return opts


def tamano(opts):
    if opts["size"]:
        m = re.fullmatch(r"(\d+)x(\d+)", opts["size"])
        if not m:
            err(f"--size inválido: {opts['size']!r} (esperado WxH, ej. 1024x576)")
        w, h = int(m.group(1)), int(m.group(2))
    elif opts["formato"] in FORMATOS:
        w, h = FORMATOS[opts["formato"]]
    else:
        err(f"formato desconocido: {opts['formato']!r}. Usá: {', '.join(FORMATOS)}")
    if max(w, h) > LADO_MAX or w * h > AREA_MAX:
        err(f"{w}x{h} supera el límite ({LADO_MAX}px de lado y {AREA_MAX} px de área). "
            f"Formatos válidos: {', '.join(f'{k}={v[0]}x{v[1]}' for k, v in FORMATOS.items())}")
    if w % MULTIPLO or h % MULTIPLO:
        err(f"{w}x{h} no es múltiplo de {MULTIPLO} (el modelo redondea y cambia el encuadre)")
    if min(w, h) < 256:
        err(f"{w}x{h}: lado mínimo 256 px")
    return w, h


def prompt_final(opts):
    partes = [opts["prompt"].strip().rstrip(".")]
    if opts["estilo_libre"]:
        partes.append(opts["estilo_libre"].strip().rstrip("."))
    elif opts["estilo"] in ESTILOS:
        partes.append(ESTILOS[opts["estilo"]])
    else:
        err(f"estilo desconocido: {opts['estilo']!r}. Usá: {', '.join(ESTILOS)} o --estilo-libre")
    if not opts["con_texto"]:
        partes.append(SIN_TEXTO)
    return ". ".join(partes) + "."


def chequear_api():
    try:
        with urllib.request.urlopen(f"{API}/models", timeout=5) as r:
            json.loads(r.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        err(f"la API de imágenes no responde en {API} ({e}).\n"
            "Es el server de vLLM-Omni + Qwen-Image-2.1 del entorno de desarrollo: pedile al usuario\n"
            "que lo levante con `bash scratch/vllm-omni-qwen21/run.sh` (no versionado) y no lo reinicies por tu cuenta.")


def main():
    opts = parsear(os.sys.argv)
    proyecto = RAIZ / "proyectos" / opts["proyecto"]
    if not proyecto.is_dir():
        existentes = ", ".join(sorted(p.name for p in (RAIZ / "proyectos").iterdir() if p.is_dir()))
        err(f"proyecto desconocido: {opts['proyecto']!r}. Proyectos: {existentes}")
    nombre = re.sub(r"[^a-z0-9_-]+", "-", opts["nombre"].lower()).strip("-")
    if not nombre:
        err("nombre inválido: usá letras, números, guiones")
    if not 1 <= opts["pasos"] <= PASOS_MAX:
        err(f"pasos fuera de rango: {opts['pasos']} (máximo {PASOS_MAX})")

    w, h = tamano(opts)
    prompt = prompt_final(opts)
    seed = opts["seed"] if opts["seed"] is not None else int.from_bytes(os.urandom(4), "little") % (2**31)
    destino = RAIZ / "public" / "proyectos" / opts["proyecto"] / "img" / f"{nombre}.png"

    if opts["dry_run"]:
        print(f"proyecto: {opts['proyecto']}\nnombre:   {nombre}\ntamaño:   {w}x{h}\n"
              f"pasos:    {opts['pasos']}\nsemilla:  {seed}\nprompt:   {prompt}\narchivo:  {destino}")
        return

    chequear_api()
    cuerpo = json.dumps({
        "model": MODELO, "prompt": prompt, "size": f"{w}x{h}", "n": 1,
        "num_inference_steps": opts["pasos"], "seed": seed, "response_format": "b64_json",
    }).encode()
    req = urllib.request.Request(f"{API}/images/generations", data=cuerpo,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            salida = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:400]
        err(f"la API devolvió HTTP {e.code}: {detalle}")
    except (urllib.error.URLError, OSError) as e:
        err(f"falló el pedido a {API}: {e}")
    segundos = round(time.time() - t0, 2)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(base64.b64decode(salida["data"][0]["b64_json"]))

    meta_path = proyecto / "imagenes.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else []
    meta.append({
        "nombre": nombre, "archivo": f"proyectos/{opts['proyecto']}/img/{nombre}.png",
        "prompt": prompt, "formato": opts["formato"], "size": f"{w}x{h}", "pasos": opts["pasos"],
        "seed": seed, "modelo": MODELO, "api": API, "segundos": segundos,
        "creado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")

    print(f"imagen: {destino}")
    print(f"remotion: staticFile(\"proyectos/{opts['proyecto']}/img/{nombre}.png\")")
    print(f"{w}x{h}, {opts['pasos']} pasos, seed {seed}, {segundos} s")
    print(f"metadatos: {meta_path}")


if __name__ == "__main__":
    main()
