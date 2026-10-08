"""Arma los SVG del logo de Atentina: isotipo y logotipo horizontal (sobre claro y sobre oscuro).
Colores de docs/DESIGN_GUIDELINE.md: anillo y palabra en ink, barras en el acento.
Mismo isotipo y fuente (Bricolage Grotesque 800, OFL) que el logo anterior (Oíme).
Escribe en docs/brand/; después regenerar og.png con og.html (ver docs/LANDING.md).
Correr: python scripts/brand/build_atentina.py (necesita fonttools)."""
import math
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

NOMBRE = "Atentina"
f = instantiateVariableFont(TTFont(Path(__file__).with_name("Bricolage.ttf")), {"wght": 800, "opsz": 96, "wdth": 100})
cmap = f.getBestCmap(); gs = f.getGlyphSet(); hmtx = f["hmtx"]

def path(gname):
    pen = SVGPathPen(gs); gs[gname].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0))); return pen.getCommands()

def bbox(gname):
    bp = BoundsPen(gs); gs[gname].draw(bp); return bp.bounds

def dot_path():
    """Punto de la i: el contorno de 'i' que queda por encima de la altura de x."""
    rec = DecomposingRecordingPen(gs); gs[cmap[ord("i")]].draw(rec)
    contornos = []; cur = []
    for op in rec.value:
        cur.append(op)
        if op[0] in ("closePath", "endPath"): contornos.append(cur); cur = []
    top = bbox(cmap[ord("ı")])[3]
    out = SVGPathPen(gs); tp = TransformPen(out, (1, 0, 0, -1, 0, 0))
    for c in contornos:
        ys = [p[1] for op in c for p in op[1]]
        if min(ys) > top - 1:
            for name, args in c: getattr(tp, name)(*args)
    return out.getCommands()

def kern(a, b):
    total = 0
    for lk in f["GPOS"].table.LookupList.Lookup:
        for st in lk.SubTable:
            if lk.LookupType == 9: st = st.ExtSubTable
            if st.LookupType != 2: continue
            cov = st.Coverage.glyphs
            if a not in cov: continue
            i = cov.index(a)
            if st.Format == 1:
                for pvr in st.PairSet[i].PairValueRecord:
                    if pvr.SecondGlyph == b and pvr.Value1: total += getattr(pvr.Value1, "XAdvance", 0) or 0
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs.get(a, 0); c2 = st.ClassDef2.classDefs.get(b, 0)
                v = st.Class1Record[c1].Class2Record[c2].Value1
                if v: total += getattr(v, "XAdvance", 0) or 0
    return total

INK, ACCENT = "#0b1220", "#2456e6"            # sobre claro
CTA_INK, ACCENT_ON_DARK = "#f4f6fa", "#9db6ff"  # sobre fondo ink
def r(x): return f"{x:.2f}".rstrip("0").rstrip(".")

def mark(ink, accent, ox=0, oy=0, size=64):
    """Anillo abierto a la derecha (el que escucha) con tres barras de voz adentro. Caja size×size en (ox,oy)."""
    k = size / 64; cx, cy = ox + 32 * k, oy + 32 * k
    R, W = 24 * k, 8 * k
    a = math.radians(16)
    x1, y1 = cx + R * math.cos(a), cy + R * math.sin(a)
    x2, y2 = cx + R * math.cos(-a), cy + R * math.sin(-a)
    ring = f'<path d="M{r(x1)} {r(y1)}A{r(R)} {r(R)} 0 1 1 {r(x2)} {r(y2)}" fill="none" stroke="{ink}" stroke-width="{r(W)}" stroke-linecap="round"/>'
    bars = ""
    for dx, h in ((-9, 12), (0, 22), (9, 12)):
        bw = 6 * k; bh = h * k
        bars += f'<rect x="{r(cx + dx * k - bw / 2)}" y="{r(cy - bh / 2)}" width="{r(bw)}" height="{r(bh)}" rx="{r(bw / 2)}" fill="{accent}"/>'
    return ring + bars

def wordmark(ink, accent, x0, baseline, s, text=NOMBRE):
    """Trazados de la fuente. La i se dibuja como ı + punto; el punto puede llevar otro color."""
    out = []; x = x0; prev = None
    for ch in text:
        gn = cmap[ord(ch)]
        if prev: x += kern(prev, gn) * s
        t = f'transform="translate({r(x)} {r(baseline)}) scale({r(s)})"'
        if ch == "i":
            out.append(f'<path {t} fill="{ink}" d="{path(cmap[ord("ı")])}"/>')
            out.append(f'<path {t} fill="{accent}" d="{dot_path()}"/>')
        else:
            out.append(f'<path {t} fill="{ink}" d="{path(gn)}"/>')
        x += hmtx[gn][0] * s
        prev = gn
    return "".join(out), x

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {r(w)} {r(h)}" width="{r(w)}" height="{r(h)}" role="img" aria-label="{title}">'
            f'<title>{title}</title>{body}</svg>\n')

CAP = 660  # altura de mayúsculas en unidades de em

def logo(ink, accent):
    size = 64; s = 44 / CAP              # mayúsculas de 44 px junto a un isotipo de 64
    gap = 18
    first, last = cmap[ord(NOMBRE[0])], cmap[ord(NOMBRE[-1])]
    x0 = size + gap - bbox(first)[0] * s  # descontar el margen izquierdo de la primera letra
    baseline = 32 + 330 * s               # centrar las mayúsculas con el isotipo
    text, xend = wordmark(ink, ink, x0, baseline, s)  # la palabra va entera en ink, como en Logo.astro
    w = xend - (hmtx[last][0] - bbox(last)[2]) * s + 2   # descontar el margen derecho de la última
    return svg(w, size, mark(ink, accent) + text, NOMBRE)

files = {
    "atentina-mark.svg": svg(64, 64, mark(INK, ACCENT), NOMBRE),
    "atentina-logo.svg": logo(INK, ACCENT),
    "atentina-logo-blanco.svg": logo(CTA_INK, ACCENT_ON_DARK),
    "atentina-mark-blanco.svg": svg(64, 64, mark(CTA_INK, ACCENT_ON_DARK), NOMBRE),
}
OUT = Path(__file__).resolve().parents[2] / "docs" / "brand"
for name, content in files.items():
    (OUT / name).write_text(content); print(name, len(content), "bytes")
