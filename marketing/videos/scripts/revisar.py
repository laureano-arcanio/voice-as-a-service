"""Revisión de un render (marketing/VIDEOS.md, "Controles"): duración, volumen, locución transcrita por tramos
y hojas de cuadros para mirar la composición sin ver el video entero.

Uso: python3 scripts/revisar.py <video.mp4> [--cada S] [--tramos 0,6,16.4,...]
- --cada: segundos entre cuadros de la hoja (default 2).
- --tramos: cortes en segundos para transcribir (por ejemplo, el inicio de cada escena); sin él, de a 15 s.
Escribe las hojas en scratch/videos/revision/<nombre>/ y deja el texto en la salida.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REPO = RAIZ.parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from voces import env, transcribir  # noqa: E402


def sh(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    video = Path(args[0]).resolve()
    cada, tramos = 2.0, None
    if "--cada" in args:
        cada = float(args[args.index("--cada") + 1])
    if "--tramos" in args:
        tramos = [float(x) for x in args[args.index("--tramos") + 1].split(",")]
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)).stdout)
    lufs = sh("ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128", "-f", "null", "-").stderr
    integrado = [l for l in lufs.splitlines() if l.strip().startswith("I:")][-1].strip()
    print(f"{video.name}: {dur:.1f} s · volumen integrado {integrado} (referencia: -16 ± 1,5 LUFS)")

    out = REPO / "scratch" / "videos" / "revision" / video.stem
    out.mkdir(parents=True, exist_ok=True)
    # Hojas de 4 x 4 cuadros
    sh("ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"fps=1/{cada},scale=480:-1,tile=4x4", str(out / "hoja-%02d.png"))
    print(f"hojas de cuadros (uno cada {cada:g} s): {out}/")

    key = env("VLLM_API_KEY")
    cortes = tramos or [x * 15.0 for x in range(int(dur // 15) + 1)]
    cortes = [c for c in cortes if c < dur] + [dur]
    with tempfile.TemporaryDirectory(dir=REPO / "scratch") as tmp:
        for a, b in zip(cortes, cortes[1:]):
            w = Path(tmp) / "tramo.wav"
            sh("ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", str(video), "-ac", "1", "-ar", "16000", str(w))
            print(f"[{a:5.1f}-{b:5.1f}] {transcribir(key, w.read_bytes())}")


if __name__ == "__main__":
    main()
