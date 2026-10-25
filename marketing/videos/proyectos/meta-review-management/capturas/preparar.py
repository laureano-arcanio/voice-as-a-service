"""Copia las capturas reales del panel a public/ y desenfoca la tabla de Operadores (nombres y teléfonos de
personas reales). El modal de m03/m04/m05 queda nítido aunque se superponga a la tabla.

Uso: python3 preparar.py <carpeta con las capturas originales>
(las del 25-oct-2026 están en scratch/meta-review/caps/)
"""
import sys
from pathlib import Path

from PIL import Image, ImageFilter

DEST = Path(__file__).resolve().parents[3] / "public" / "proyectos" / "meta-review-management" / "capturas"
OPERADORES = (296, 548, 1720, 826)  # filas de la tabla (x0, y0, x1, y1), en px de la captura de 1784 de ancho
MODAL = {  # el modal de cada captura, que queda nítido
    "m03-nueva-plantilla.png": (582, 484, 1202, 1429),
    "m04-conectar.png": (582, 744, 1202, 1169),
    "m05-esperando-meta.png": (582, 726, 1202, 1187),
}
COPIAR = ["c00-login.png", "m06-popup-meta.png"]
DESENFOCAR = ["m01-whatsapp.png", "m02-plantillas.png", *MODAL]


def main():
    src = Path(sys.argv[1])
    DEST.mkdir(parents=True, exist_ok=True)
    for n in COPIAR:
        Image.open(src / n).convert("RGB").save(DEST / n, optimize=True)
    for n in DESENFOCAR:
        img = Image.open(src / n).convert("RGB")
        base = img.copy()
        if n in MODAL:  # sin el modal blanco, para que el desenfoque no lo derrame alrededor
            base.paste(img.getpixel((OPERADORES[0] + 4, OPERADORES[3] - 4)), MODAL[n])
        zona = base.crop(OPERADORES)
        # Pixelado + desenfoque fuerte: el texto no se reconstruye
        chico = zona.resize((max(1, zona.width // 14), max(1, zona.height // 14)), Image.BILINEAR)
        zona = chico.resize(zona.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
        out = img.copy()
        out.paste(zona, OPERADORES[:2])
        if n in MODAL:
            m = MODAL[n]
            out.paste(img.crop(m), m[:2])
        out.save(DEST / n, optimize=True)
    print(f"capturas en {DEST}")


if __name__ == "__main__":
    main()
