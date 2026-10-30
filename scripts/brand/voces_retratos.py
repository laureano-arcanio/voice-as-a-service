"""Genera los retratos SVG de las voces del TTS, los mismos en el dashboard y en la landing.

Cada retrato es siempre de la misma voz (`<voz>.svg`, el id del catálogo `multi41`). Geometría común (cabeza,
rasgos, luz desde arriba a la izquierda) y por personaje: piel, pelo, ropa, accesorios.
Uso: make voces-retratos. Hay uno por cada voz de tts/finetune/voces.tsv; al sumar una voz al checkpoint, sumar su
retrato acá y su id a PORTRAITS en web/src/features/voices/names.ts.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTS = [ROOT / "web" / "public" / "voces", ROOT / "landing" / "public" / "voces"]

SKIN = {
    # luz, base, sombra, labio
    "clara": ("#f9e0d0", "#efc2a4", "#d0967a", "#c9776f"),
    "media": ("#f5d3b8", "#e2ae88", "#bf8661", "#bb6f63"),
    "trigueña": ("#efc6a2", "#d9a179", "#b47a55", "#ac6455"),
    "oliva": ("#e8bc94", "#cc9a6c", "#a3714a", "#a5604f"),
    "morena": ("#c48e69", "#9f6846", "#77492f", "#7f4639"),
    "oscura": ("#a8714f", "#7d4a2d", "#56301c", "#5e2f25"),
}

FEM_HEAD = "M120 56C97 56 83 73 83 99C83 124 99 146 120 150C141 146 157 124 157 99C157 73 143 56 120 56Z"
MASC_HEAD = "M120 54C96 54 81 72 81 99C81 122 92 140 108 149C114 152 126 152 132 149C148 140 159 122 159 99C159 72 144 54 120 54Z"


def eye(n, side, cx, cy, iris, fem):
    w = 8.4
    shape = f"M{cx-w} {cy} C{cx-5} {cy-5.4} {cx+5} {cy-5.4} {cx+w} {cy} C{cx+5} {cy+4.2} {cx-5} {cy+4.2} {cx-w} {cy}Z"
    lid = f"M{cx-w-0.6} {cy+0.4} C{cx-5} {cy-5.6} {cx+5} {cy-5.6} {cx+w+0.4} {cy-0.2}"
    out = cx + w if side == "r" else cx - w
    flick = ""
    if fem:
        d = 2.8 if side == "r" else -2.8
        flick = f'<path d="M{out} {cy-0.4}l{d} -2.4" stroke="#2a1d18" stroke-width="1.5" stroke-linecap="round"/>'
    return (
        f'<clipPath id="{n}-e{side}"><path d="{shape}"/></clipPath>'
        f'<path d="{shape}" fill="#fbf6f2"/>'
        f'<g clip-path="url(#{n}-e{side})">'
        f'<circle cx="{cx}" cy="{cy+0.2}" r="4.6" fill="{iris}"/>'
        f'<circle cx="{cx}" cy="{cy+0.2}" r="4.6" fill="none" stroke="#000" stroke-opacity=".3" stroke-width=".8"/>'
        f'<circle cx="{cx}" cy="{cy+0.2}" r="2.2" fill="#120c0a"/>'
        f'<rect x="{cx-w}" y="{cy-6}" width="{2*w}" height="4" fill="#000" opacity=".16"/>'
        f'</g>'
        f'<circle cx="{cx+1.6}" cy="{cy-1.3}" r="1.3" fill="#fff"/>'
        f'<path d="{lid}" stroke="#2a1d18" stroke-width="{1.9 if fem else 1.6}" stroke-linecap="round" fill="none"/>'
        f'{flick}'
        f'<path d="M{cx-6} {cy-7.4}C{cx-2} {cy-9.4} {cx+3} {cy-9.4} {cx+7} {cy-7.2}" stroke="#000" stroke-opacity=".13" stroke-width="1" fill="none" stroke-linecap="round"/>'
        f'<path d="M{cx-5} {cy+5.2}C{cx-2} {cy+6.2} {cx+2} {cy+6.2} {cx+5} {cy+5.2}" stroke="#000" stroke-opacity=".08" stroke-width="1" fill="none" stroke-linecap="round"/>'
    )


def skin_layer(n, p):
    light, base, shadow, lip = SKIN[p["skin"]]
    fem = p["fem"]
    head = FEM_HEAD if fem else MASC_HEAD
    neck = "M107 128L106 172C112 178 128 178 134 172L133 128Z" if fem else "M104 128L103 174C110 180 130 180 137 174L136 128Z"
    ex = (82, 158) if fem else (80, 160)
    return (
        f'<path d="{neck}" fill="url(#{n}-neck)"/>'
        f'<ellipse cx="{ex[0]}" cy="106" rx="6.5" ry="10" fill="{base}"/>'
        f'<path d="M{ex[0]-2} 101C{ex[0]-3} 106 {ex[0]-1} 111 {ex[0]+1} 112" stroke="{shadow}" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        f'<ellipse cx="{ex[1]}" cy="106" rx="6.5" ry="10" fill="{shadow}"/>'
        f'<path d="{head}" fill="url(#{n}-skin)"/>'
        f'<path d="{head}" fill="url(#{n}-shade)"/>'
        f'<ellipse cx="101" cy="120" rx="9" ry="5.5" fill="url(#{n}-blush)"/>'
        f'<ellipse cx="139" cy="120" rx="9" ry="5.5" fill="url(#{n}-blush)"/>'
    )


def features(n, p):
    light, base, shadow, lip = SKIN[p["skin"]]
    fem = p["fem"]
    by = p.get("brow_y", 92)
    bw = 3 if fem else 3.8
    brows = (
        f'<path d="M95 {by+1.5}C100 {by-2.5} 108 {by-2.5} 113 {by}" stroke="{p["brow"]}" stroke-width="{bw}" stroke-linecap="round" fill="none"/>'
        f'<path d="M127 {by}C132 {by-2.5} 140 {by-2.5} 145 {by+1.5}" stroke="{p["brow"]}" stroke-width="{bw}" stroke-linecap="round" fill="none"/>'
    )
    if fem:
        mouth = (
            f'<path d="M108 133.5C112 130.5 117 130.5 120 132C123 130.5 128 130.5 132 133.5C127 135 113 135 108 133.5Z" fill="{lip}"/>'
            f'<path d="M108 133.5C113 135 127 135 132 133.5C128 140.5 112 140.5 108 133.5Z" fill="{lip}" opacity=".85"/>'
            f'<path d="M107 133C113 135.6 127 135.6 133 133" stroke="#6b3a33" stroke-width="1.2" fill="none" stroke-linecap="round"/>'
            f'<ellipse cx="121" cy="137" rx="4" ry="1.1" fill="#fff" opacity=".3"/>'
        )
    else:
        mouth = (
            f'<path d="M109 134C113 132.2 117 132.2 120 133C123 132.2 127 132.2 131 134C126 135 114 135 109 134Z" fill="{lip}" opacity=".8"/>'
            f'<path d="M109 134C114 135 126 135 131 134C127 139 113 139 109 134Z" fill="{lip}" opacity=".6"/>'
            f'<path d="M108 133.6C114 136 126 136 132 133.6" stroke="#5e352c" stroke-width="1.3" fill="none" stroke-linecap="round"/>'
        )
    nose = (
        f'<path d="M116 101C117 109 117 115 113.5 121" stroke="{shadow}" stroke-width="1.3" fill="none" stroke-linecap="round" opacity=".5"/>'
        f'<path d="M113.5 120.5C112 123.5 115 125.5 117.5 124.5C119 125.6 121 125.6 122.5 124.5C125 125.5 128 123.5 126.5 120.5" stroke="{shadow}" stroke-width="1.5" fill="none" stroke-linecap="round"/>'
        f'<ellipse cx="121.5" cy="113" rx="1.8" ry="6" fill="#fff" opacity=".2"/>'
        f'<circle cx="121" cy="121" r="1.6" fill="#fff" opacity=".22"/>'
    )
    return brows + eye(n, "l", 104, 104, p["iris"], fem) + eye(n, "r", 136, 104, p["iris"], fem) + nose + mouth


def defs(n, p):
    light, base, shadow, lip = SKIN[p["skin"]]
    bg1, bg2 = p["bg"]
    h1, h2 = p["hair"]
    c1, c2 = p["cloth"]
    head = FEM_HEAD if p["fem"] else MASC_HEAD
    return f"""<defs>
<radialGradient id="{n}-bg" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></radialGradient>
<radialGradient id="{n}-skin" cx=".4" cy=".38" r=".75"><stop offset="0" stop-color="{light}"/><stop offset=".55" stop-color="{base}"/><stop offset="1" stop-color="{shadow}"/></radialGradient>
<linearGradient id="{n}-shade" x1="0" y1="0" x2="1" y2="0"><stop offset=".55" stop-color="{shadow}" stop-opacity="0"/><stop offset="1" stop-color="{shadow}" stop-opacity=".5"/></linearGradient>
<linearGradient id="{n}-neck" x1="0" y1="0" x2="0" y2="1"><stop offset=".1" stop-color="{shadow}"/><stop offset=".5" stop-color="{base}"/></linearGradient>
<radialGradient id="{n}-blush"><stop offset="0" stop-color="#e0786a" stop-opacity="{p.get('blush', .26)}"/><stop offset="1" stop-color="#e0786a" stop-opacity="0"/></radialGradient>
<linearGradient id="{n}-hair" x1=".2" y1="0" x2=".7" y2="1"><stop offset="0" stop-color="{h1}"/><stop offset="1" stop-color="{h2}"/></linearGradient>
<linearGradient id="{n}-cloth" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>
<clipPath id="{n}-clip"><circle cx="120" cy="120" r="120"/></clipPath>
<clipPath id="{n}-head"><path d="{head}"/></clipPath>
<filter id="{n}-soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2"/></filter>
</defs>"""


SHOULDERS = "M8 256C10 206 42 184 90 173C100 171 104 169 106 167L134 167C136 169 140 171 150 173C198 184 230 206 232 256Z"


def svg(n, p):
    light, base, shadow, lip = SKIN[p["skin"]]
    H = f"url(#{n}-hair)"
    front = p.get("front", "").replace("HAIR", H)
    # sombra que el pelo proyecta sobre la frente
    cast = ""
    if p.get("cast", True) and p.get("front_shape"):
        cast = (f'<g clip-path="url(#{n}-head)"><path d="{p["front_shape"]}" fill="{shadow}" opacity=".55" '
                f'transform="translate(1 3.5)" filter="url(#{n}-soft)"/></g>')
    parts = [
        defs(n, p),
        f'<g clip-path="url(#{n}-clip)">',
        f'<circle cx="120" cy="120" r="120" fill="url(#{n}-bg)"/>',
        '<g transform="translate(120 140) scale(1.22) translate(-120 -125)">',
        p.get("back", "").replace("HAIR", H),
        skin_layer(n, p),
        cast,
        p.get("beard", "").replace("HAIR", H),
        features(n, p),
        p.get("stache", "").replace("HAIR", H),
        '<g transform="translate(0 -7)">' + p["clothes"].replace("CLOTH", f"url(#{n}-cloth)").replace("NECK", f"url(#{n}-neck)") + "</g>",
        (f'<path d="{p["front_shape"]}" fill="{H}"/>' if p.get("front_shape") else "") + front,
        p.get("acc", "").replace("HAIR", H),
        "</g></g>",
    ]
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">\n' + "\n".join(x for x in parts if x) + "\n</svg>\n"


# ---------- ropa ----------
FOLDS = '<path d="M60 250C62 226 66 212 72 202M180 250C178 226 174 212 168 202" stroke="#000" stroke-opacity=".14" stroke-width="2" fill="none"/>'


def blazer(lapel, shirt="#f7f8fb"):
    return (
        f'<path d="{SHOULDERS}" fill="CLOTH"/>'
        f'<path d="M104 167L120 216L136 167Z" fill="{shirt}"/>'
        f'<path d="M106 167L114 176L120 216Z" fill="#000" opacity=".08"/>'
        f'<path d="M104 166L94 178L108 186L120 216Z" fill="{lapel}"/>'
        f'<path d="M136 166L146 178L132 186L120 216Z" fill="{lapel}"/>'
        f'<path d="M104 166L120 216L136 166" stroke="#000" stroke-opacity=".2" stroke-width="1.2" fill="none"/>'
        + FOLDS
    )


def sweater(rib):
    return (
        f'<path d="{SHOULDERS}" fill="CLOTH"/>'
        f'<path d="M102 167C108 182 132 182 138 167" stroke="{rib}" stroke-width="7" fill="none" stroke-linecap="round"/>'
        f'<path d="M102 167C108 182 132 182 138 167" stroke="#fff" stroke-opacity=".18" stroke-width="1.2" fill="none" transform="translate(0 -2.5)"/>'
        + FOLDS
    )


def shirt_open(collar):
    return (
        f'<path d="{SHOULDERS}" fill="CLOTH"/>'
        f'<path d="M104 167L120 198L136 167Z" fill="NECK"/>'
        f'<path d="M102 162L120 198L107 203L95 173Z" fill="{collar}" stroke="#000" stroke-opacity=".1"/>'
        f'<path d="M138 162L120 198L133 203L145 173Z" fill="{collar}" stroke="#000" stroke-opacity=".1"/>'
        f'<path d="M120 198L120 250" stroke="#000" stroke-opacity=".14" stroke-width="1.5"/>'
        f'<circle cx="121.5" cy="214" r="1.5" fill="#000" opacity=".22"/><circle cx="121.5" cy="232" r="1.5" fill="#000" opacity=".22"/>'
        + FOLDS
    )


def blouse(trim):
    return (
        f'<path d="{SHOULDERS}" fill="CLOTH"/>'
        f'<path d="M100 167C106 190 134 190 140 167" stroke="{trim}" stroke-width="2.6" fill="none"/>'
        f'<path d="M120 188L120 196" stroke="{trim}" stroke-width="2" stroke-linecap="round"/>'
        + FOLDS
    )


def headset():
    return (
        '<path d="M77 104C72 48 168 48 163 104" stroke="#2b3040" stroke-width="4.5" fill="none" stroke-linecap="round"/>'
        '<path d="M80 80C88 56 152 56 160 80" stroke="#fff" stroke-opacity=".22" stroke-width="1.3" fill="none" stroke-linecap="round"/>'
        '<rect x="70" y="95" width="14" height="23" rx="6" fill="#2b3040"/>'
        '<rect x="72.5" y="99" width="4.5" height="15" rx="2.2" fill="#2456e6"/>'
        '<rect x="156" y="95" width="14" height="23" rx="6" fill="#2b3040"/>'
        '<path d="M78 116C80 134 92 143 105 142" stroke="#2b3040" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
        '<rect x="103" y="138.5" width="9" height="7" rx="3.5" fill="#2b3040"/>'
    )


def glasses(color="#2a2c36"):
    return (
        f'<rect x="92" y="96" width="24" height="17" rx="6" fill="#fff" fill-opacity=".1" stroke="{color}" stroke-width="2.2"/>'
        f'<rect x="124" y="96" width="24" height="17" rx="6" fill="#fff" fill-opacity=".1" stroke="{color}" stroke-width="2.2"/>'
        f'<path d="M116 102C118 100 122 100 124 102" stroke="{color}" stroke-width="2" fill="none"/>'
        f'<path d="M92 102L82 100M148 102L158 100" stroke="{color}" stroke-width="2"/>'
        f'<path d="M96 99L101 99M128 99L133 99" stroke="#fff" stroke-opacity=".6" stroke-width="1.2" stroke-linecap="round"/>'
    )


def strands(color, paths, op=.5, w=1.6):
    return "".join(f'<path d="{d}" stroke="{color}" stroke-opacity="{op}" stroke-width="{w}" fill="none" stroke-linecap="round"/>' for d in paths)


P = {}

# Sofía: recepcionista, pelo largo lacio castaño oscuro con raya al costado, auriculares con micrófono, blazer azul.
P["sofia"] = dict(
    fem=True, skin="media", iris="#5a3a22", brow="#3a261c",
    hair=("#6a4532", "#2c1b14"), cloth=("#2f56c4", "#1740b8"), bg=("#f6f8ff", "#c7d5ff"),
    back='<path d="M78 96C70 54 94 38 122 38C152 38 174 56 164 98C162 136 168 168 178 198C150 210 90 210 62 198C72 168 80 136 78 96Z" fill="HAIR"/>'
         + strands("#000", ["M72 190C76 160 78 130 78 104", "M168 190C164 160 162 130 162 104"], .25, 2),
    front_shape="M82 104C76 62 98 42 122 42C150 42 168 62 160 106C158 88 150 76 136 70C126 66 114 64 108 62C100 70 90 82 82 104Z",
    front=strands("#a0704f", ["M110 50C128 50 146 58 154 74", "M106 56C122 58 140 64 150 78", "M100 54C94 60 88 72 86 84"], .55),
    clothes=blazer("#1a3590", "#f4f6fb"),
    acc=headset(),
)

# Paula: rulos voluminosos negros, piel trigueña, suéter ámbar, aros dorados.
curls_back = [(120, 58, 30), (92, 66, 24), (148, 66, 24), (76, 90, 21), (164, 90, 21), (70, 116, 19), (170, 116, 19),
              (74, 142, 17), (166, 142, 17), (84, 162, 14), (156, 162, 14), (100, 46, 18), (140, 46, 18)]
curls_front = [(92, 70, 9), (104, 63, 9), (117, 60, 9), (130, 61, 9), (142, 65, 9), (152, 73, 8), (85, 80, 7.5), (157, 84, 7)]
P["paula"] = dict(
    fem=True, skin="trigueña", iris="#3b2414", brow="#24160f",
    hair=("#4a3326", "#1a100b"), cloth=("#eaa64a", "#c97f1f"), bg=("#fffaf1", "#fbdcae"),
    back="".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="HAIR"/>' for x, y, r in curls_back)
         + strands("#8a6048", [f"M{x-r*.55} {y-r*.15}C{x-r*.3} {y-r*.6} {x+r*.3} {y-r*.6} {x+r*.5} {y-r*.2}" for x, y, r in curls_back], .5, 1.8),
    front="".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="HAIR"/>' for x, y, r in curls_front)
          + strands("#8a6048", [f"M{x-r*.55} {y-r*.1}C{x-r*.3} {y-r*.6} {x+r*.3} {y-r*.6} {x+r*.5} {y-r*.15}" for x, y, r in curls_front], .6, 1.4),
    cast=False,
    clothes=sweater("#c27a1e"),
    acc='<circle cx="81" cy="121" r="3.4" fill="none" stroke="#f2c14e" stroke-width="1.6"/><circle cx="159" cy="121" r="3.4" fill="none" stroke="#d9a738" stroke-width="1.6"/>',
)

# Valentina: pelo recogido en rodete, castaño rojizo, piel clara con pecas, blusa verde.
P["valentina"] = dict(
    fem=True, skin="clara", iris="#4d6b3a", brow="#7a4a2e", blush=.32,
    hair=("#bd7445", "#6e3a1f"), cloth=("#25b06b", "#16804a"), bg=("#f2fbf6", "#c3ead5"),
    back='<circle cx="120" cy="42" r="19" fill="HAIR"/>'
         + strands("#e0a070", ["M106 38C112 30 128 30 134 38", "M108 46C114 52 126 52 132 46"], .6, 1.6),
    front_shape="M82 104C78 70 96 52 120 52C144 52 162 70 158 104C156 90 152 80 144 74C134 68 126 66 120 66C112 66 102 68 96 74C88 80 84 90 82 104Z",
    front=strands("#e09a68", ["M90 80C96 66 108 60 120 60", "M150 80C144 66 132 60 120 60", "M120 54L120 64"], .6, 1.5),
    beard="".join(f'<circle cx="{x}" cy="{y}" r=".9" fill="#b0663f" opacity=".45"/>' for x, y in
                  [(99, 116), (103, 118), (96, 119), (107, 115), (141, 116), (137, 118), (144, 119), (133, 115), (117, 112), (123, 112)]),
    clothes=blouse("#0f6b3c"),
    acc='<circle cx="82" cy="119" r="2.4" fill="#fff" stroke="#d6d6d6" stroke-width=".6"/><circle cx="158" cy="119" r="2.4" fill="#eee" stroke="#ccc" stroke-width=".6"/>',
)

# Gonzalo: ~50 años, canas, barba corta gris, anteojos, blazer gris con camisa celeste.
P["gonzalo"] = dict(
    fem=False, skin="media", iris="#4a3526", brow="#8f8b86", brow_y=91,
    hair=("#e4e2de", "#9e9a94"), cloth=("#535a69", "#2c303a"), bg=("#f3f6ff", "#a9bfff"),
    back='<path d="M80 100C76 64 96 46 120 46C144 46 164 64 160 100Z" fill="HAIR"/>',
    front_shape="M80 100C78 66 98 46 122 46C146 46 164 66 160 100C158 86 154 78 148 72C136 66 128 70 120 68C110 66 100 68 94 74C86 82 82 90 80 100Z",
    front=strands("#ffffff", ["M96 58C110 50 132 50 148 60", "M90 70C100 60 112 56 124 56"], .7, 1.8),
    beard='<path d="M83 110C84 136 100 154 120 155C140 154 156 136 157 110C153 122 148 132 140 136C134 133 128 132 120 132C112 132 106 133 100 136C92 132 87 122 83 110Z" fill="HAIR"/>'
          + strands("#ffffff", ["M92 128C98 140 108 148 120 150", "M148 128C142 140 132 148 120 150"], .45, 1.4),
    stache='<path d="M105 131C110 126.5 118 127 120 128.5C122 127 130 126.5 135 131C130 130.5 124 130 120 131C116 130 110 130.5 105 131Z" fill="url(#gonzalo-hair)"/>',
    clothes=blazer("#3e4452", "#cfe0f7"),
    acc=glasses(),
)

# Lucas: piel morena, pelo negro corto texturado, suéter azul de marca, auriculares con micrófono.
P["lucas"] = dict(
    fem=False, skin="morena", iris="#2a1a10", brow="#1a110c",
    hair=("#2e2119", "#0e0907"), cloth=("#3b6cf0", "#1740b8"), bg=("#fff8ec", "#f8d6a2"),
    back='<path d="M82 100C78 66 98 50 120 50C142 50 162 66 158 100Z" fill="HAIR"/>',
    front_shape="M82 100C80 62 98 46 120 46C142 46 160 62 158 100C157 90 154 82 150 78C140 72 130 73 120 73C110 73 100 72 90 78C86 82 83 90 82 100Z",
    front=strands("#5a4434", [f"M{x-2.2} {y}a2.2 2.2 0 1 1 4.4 0" for x, y in [
        (100, 58), (111, 54), (122, 53), (133, 55), (143, 60), (95, 67), (106, 63), (117, 62), (128, 62), (139, 64), (149, 70), (90, 76)]], .8, 1.3),
    beard='<path d="M98 141C106 151 134 151 142 141" stroke="#1a110c" stroke-opacity=".22" stroke-width="5" fill="none" stroke-linecap="round"/>',
    clothes=sweater("#1740b8"),
    acc=headset(),
)

# Tomás: ~28 años, pelo castaño ondulado con jopo, barba de pocos días, camisa blanca abierta.
P["tomas"] = dict(
    fem=False, skin="oliva", iris="#5a3d24", brow="#3b2618",
    hair=("#86593a", "#3b2416"), cloth=("#ffffff", "#dfe5ef"), bg=("#f1faf5", "#a8dcbf"),
    back='<path d="M80 100C76 62 96 44 120 44C144 44 164 62 160 100Z" fill="HAIR"/>',
    front_shape="M80 100C76 70 86 44 112 36C134 30 158 40 163 62C165 76 163 90 160 100C157 86 152 76 142 70C132 66 122 66 112 70C104 74 99 79 97 86C95 80 90 79 87 84C83 90 81 95 80 100Z",
    front=strands("#b5845c", ["M96 56C108 42 132 38 150 48", "M92 66C106 54 128 52 154 60", "M110 44C120 38 134 36 144 40"], .65, 1.8),
    beard='<path d="M83 110C84 136 100 154 120 155C140 154 156 136 157 110C153 124 147 134 139 139C132 136 108 136 101 139C93 134 87 124 83 110Z" fill="#3b2416" opacity=".26"/>'
          '<path d="M106 130C112 127.5 128 127.5 134 130" stroke="#3b2416" stroke-opacity=".3" stroke-width="3" fill="none" stroke-linecap="round"/>',
    clothes=shirt_open("#f6f8fb"),
)

def suit_tie(lapel, shirt, tie):
    return blazer(lapel, shirt) + (
        f'<path d="M115.5 168L124.5 168L122.5 176L117.5 176Z" fill="{tie}"/>'
        f'<path d="M117.5 176L122.5 176L126 206L120 214L114 206Z" fill="{tie}"/>'
        f'<path d="M120 178L120 210" stroke="#000" stroke-opacity=".15" stroke-width="1"/>'
    )


def earrings(color, r=2.6):
    return (f'<circle cx="82" cy="119" r="{r}" fill="{color}"/><circle cx="158" cy="119" r="{r}" fill="{color}" opacity=".85"/>'
            f'<circle cx="81.2" cy="118.2" r="{r*.35}" fill="#fff" opacity=".7"/>')


# Martín: ~45 años, pelo oscuro corto peinado al costado con sienes grises, afeitado, traje azul marino y corbata.
P["martin"] = dict(
    fem=False, skin="trigueña", iris="#3a2618", brow="#2a1d16", brow_y=91,
    hair=("#4a3a30", "#1c1410"), cloth=("#2a3a5e", "#16213d"), bg=("#f2f5fb", "#b9c6e2"),
    back='<path d="M80 100C76 62 96 46 120 46C144 46 164 62 160 100Z" fill="HAIR"/>',
    front_shape="M80 100C78 64 98 44 124 44C148 44 164 62 160 100C158 86 154 78 146 72C136 66 124 66 112 66C104 66 100 64 98 60C92 70 84 84 80 100Z",
    front=strands("#7a6658", ["M100 56C114 48 136 48 152 60", "M104 62C118 56 136 58 150 68"], .6, 1.7)
          + strands("#d8d4cf", ["M82 98C82 90 84 84 86 80", "M158 98C158 90 156 84 154 80"], .8, 3),
    beard='<path d="M83 110C84 136 100 154 120 155C140 154 156 136 157 110C153 124 147 134 139 139C132 136 108 136 101 139C93 134 87 124 83 110Z" fill="#2a1d16" opacity=".12"/>',
    clothes=suit_tie("#1d2a47", "#f4f6fb", "#b8323f"),
)

# Carolina: carré lacio rubio por la mandíbula, piel clara, blazer bordó, aros de perla.
P["carolina"] = dict(
    fem=True, skin="clara", iris="#4f6a86", brow="#8a6a44",
    hair=("#e8c886", "#a87a3c"), cloth=("#a33a4f", "#7a2236"), bg=("#fff5f7", "#f3c4cf"),
    back='<path d="M80 98C74 58 96 40 120 40C144 40 166 58 160 98C160 120 163 138 168 152C150 160 90 160 72 152C77 138 80 120 80 98Z" fill="HAIR"/>'
         + strands("#7a5226", ["M76 150C80 130 80 112 80 100", "M164 150C160 130 160 112 160 100"], .3, 2),
    front_shape="M82 104C76 62 98 42 124 42C150 42 168 62 160 106C158 88 148 74 134 68C122 64 112 64 106 64C98 72 88 86 82 104Z",
    front=strands("#fbe6b8", ["M112 50C130 50 146 58 154 74", "M108 56C124 58 140 64 150 78"], .7, 1.6),
    clothes=blazer("#5e1828", "#fbf3f4"),
    acc=earrings("#fbf7ee", 3),
)

# Jimena: pelo negro lacio, tirante y recogido, con raya al medio, piel oliva, anteojos, blazer verde azulado.
P["jimena"] = dict(
    fem=True, skin="oliva", iris="#2e1d12", brow="#1a120e",
    hair=("#2e2420", "#0c0807"), cloth=("#14808a", "#0b5c63"), bg=("#effafa", "#b2e0e2"),
    back='<path d="M84 100C80 62 98 48 120 48C142 48 160 62 156 100Z" fill="HAIR"/>',
    front_shape="M82 104C78 68 96 50 120 50C144 50 162 68 158 104C156 88 150 76 140 70C132 66 124 64 120 62C116 64 108 66 100 70C90 76 84 88 82 104Z",
    front=strands("#5a4a42", ["M118 54C108 58 96 66 90 82", "M122 54C132 58 144 66 150 82"], .7, 1.5),
    clothes=blazer("#084046", "#f2f8f8"),
    acc=glasses("#1e2a4a"),
)

# Diego: ~35 años, pelo castaño oscuro con rulos cortos, barba tupida, suéter terracota.
diego_curls = [(96, 64), (106, 57), (117, 54), (128, 54), (139, 58), (148, 65), (90, 74), (101, 67), (112, 63), (124, 63), (135, 65), (152, 74)]
P["diego"] = dict(
    fem=False, skin="trigueña", iris="#3b2414", brow="#2b1b12",
    hair=("#5a3a26", "#24160e"), cloth=("#d0643b", "#a8462a"), bg=("#fff6f0", "#f4c9ad"),
    back='<path d="M82 100C78 64 98 46 120 46C142 46 162 64 158 100Z" fill="HAIR"/>',
    front_shape="M82 100C78 60 98 44 120 44C142 44 162 60 158 100C157 90 154 82 150 78C140 73 130 73 120 73C110 73 100 73 90 78C86 82 83 90 82 100Z",
    front="".join(f'<circle cx="{x}" cy="{y}" r="6.5" fill="HAIR"/>' for x, y in diego_curls)
          + strands("#8a6048", [f"M{x-3.6} {y}C{x-2} {y-3.8} {x+2} {y-3.8} {x+3.4} {y-1}" for x, y in diego_curls], .6, 1.3),
    cast=False,
    beard='<path d="M83 108C84 138 100 158 120 159C140 158 156 138 157 108C153 122 148 130 141 134C134 131 128 130 120 130C112 130 106 131 99 134C92 130 87 122 83 108Z" fill="HAIR"/>'
          + strands("#8a6048", ["M92 126C98 140 108 150 120 153", "M148 126C142 140 132 150 120 153"], .45, 1.4),
    stache='<path d="M104 131C110 126 118 126.5 120 128C122 126.5 130 126 136 131C130 130.5 124 130 120 131C116 130 110 130.5 104 131Z" fill="url(#diego-hair)"/>',
    clothes=sweater("#8a3a22"),
)

# Laura: pelo largo ondulado castaño claro con raya al medio, piel clara, blusa lavanda.
P["laura"] = dict(
    fem=True, skin="clara", iris="#5a4630", brow="#6a4a32", blush=.3,
    hair=("#b5875e", "#5e3e26"), cloth=("#9b87e0", "#7560c4"), bg=("#f7f5ff", "#d4cbf8"),
    back='<path d="M78 96C70 54 94 38 120 38C146 38 170 54 162 96C160 120 170 140 166 160C172 180 168 196 176 206C150 214 90 214 64 206C72 196 68 180 74 160C70 140 80 120 78 96Z" fill="HAIR"/>'
         + strands("#e0b88c", ["M72 120C68 140 76 152 72 170C68 186 74 196 70 204", "M168 120C172 140 164 152 168 170C172 186 166 196 170 204"], .45, 2),
    front_shape="M82 106C76 62 98 44 120 44C142 44 164 62 158 106C156 88 150 76 140 70C132 66 124 62 120 58C116 62 108 66 100 70C90 76 84 88 82 106Z",
    front=strands("#e0b88c", ["M118 50C106 56 94 66 88 84", "M122 50C134 56 146 66 152 84"], .6, 1.6),
    clothes=blouse("#55419e"),
    acc=earrings("#f2c14e", 2.2),
)

# Gabriela: ~55 años, pelo corto plateado con flequillo de costado, piel media, blazer azul petróleo, aros dorados.
P["gabriela"] = dict(
    fem=True, skin="media", iris="#3d5a6b", brow="#7a746e",
    hair=("#ecebe8", "#a3a09b"), cloth=("#2a6f97", "#1b4f70"), bg=("#f1f8ff", "#bcd9ef"),
    back='<path d="M78 102C74 62 96 44 120 44C144 44 166 62 162 102C164 114 162 124 158 130L82 130C78 124 76 114 78 102Z" fill="HAIR"/>',
    front_shape="M80 104C76 70 88 46 114 40C136 34 160 46 164 68C166 82 162 94 160 104C156 90 150 80 140 74C128 70 116 72 106 80C98 86 92 88 88 92C84 96 82 100 80 104Z",
    front=strands("#ffffff", ["M96 60C110 46 134 42 152 52", "M90 72C106 58 128 54 156 64"], .75, 1.8),
    clothes=blazer("#143c55", "#f4f7fa"),
    acc=earrings("#e3b445", 3),
)


# ---------- peinados para el resto del catálogo ----------
# Cada uno devuelve back / front_shape / front (y cast); `hl` es el color del brillo de los mechones.
SOFIA_BACK = '<path d="M78 96C70 54 94 38 122 38C152 38 174 56 164 98C162 136 168 168 178 198C150 210 90 210 62 198C72 168 80 136 78 96Z" fill="HAIR"/>'
SIDE_FRONT = "M82 104C76 62 98 42 122 42C150 42 168 62 160 106C158 88 150 76 136 70C126 66 114 64 108 62C100 70 90 82 82 104Z"
MID_FRONT = "M82 106C76 62 98 44 120 44C142 44 164 62 158 106C156 88 150 76 140 70C132 66 124 62 120 58C116 62 108 66 100 70C90 76 84 88 82 106Z"
BACK_FRONT = "M82 104C78 70 96 52 120 52C144 52 162 70 158 104C156 90 152 80 144 74C134 68 126 66 120 66C112 66 102 68 96 74C88 80 84 90 82 104Z"
BANGS = "M82 100C76 60 98 42 120 42C142 42 164 60 158 100C158 94 157 90 156 88C146 84 134 83 120 83C106 83 94 84 84 88C83 90 82 94 82 100Z"
CAP = '<path d="M84 100C80 62 98 48 120 48C142 48 160 62 156 100Z" fill="HAIR"/>'


def f_long(hl, mid=False):
    return dict(back=SOFIA_BACK + strands("#000", ["M72 190C76 160 78 130 78 104", "M168 190C164 160 162 130 162 104"], .22, 2),
                front_shape=MID_FRONT if mid else SIDE_FRONT,
                front=strands(hl, ["M118 50C106 56 94 66 88 84", "M122 50C134 56 146 66 152 84"] if mid else
                              ["M110 50C128 50 146 58 154 74", "M106 56C122 58 140 64 150 78"], .6, 1.6))


def f_bangs(hl, back=SOFIA_BACK):
    return dict(back=back, front_shape=BANGS,
                front=strands(hl, [f"M{x} {66 if abs(x-120) < 20 else 72}L{x+1} 84" for x in (96, 106, 116, 126, 136, 146)]
                              + ["M100 52C112 46 130 46 142 52"], .5, 1.4))


def f_ponytail(hl):
    return dict(back=CAP + '<path d="M146 60C178 62 188 110 178 158C174 178 162 182 160 166C168 130 164 92 146 60Z" fill="HAIR"/>'
                + strands(hl, ["M160 80C172 100 174 130 168 160"], .5, 1.6),
                front_shape=BACK_FRONT, front=strands(hl, ["M90 80C96 66 108 60 120 60", "M150 80C144 66 132 60 120 60"], .6, 1.5))


def f_wavy_mid(hl):
    return dict(back='<path d="M80 98C72 58 96 40 120 40C144 40 168 58 160 98C160 116 164 130 170 146C174 158 168 168 172 178C152 186 88 186 68 178C72 168 66 158 70 146C76 130 80 116 80 98Z" fill="HAIR"/>'
                + strands(hl, ["M74 130C70 142 76 152 72 164", "M166 130C170 142 164 152 168 164"], .45, 2),
                front_shape=SIDE_FRONT, front=strands(hl, ["M110 50C128 50 146 58 154 74", "M100 54C94 60 88 72 86 84"], .6, 1.6))


def curls(points, hl, op=.55):
    return ("".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="HAIR"/>' for x, y, r in points)
            + strands(hl, [f"M{x-r*.55} {y-r*.15}C{x-r*.3} {y-r*.6} {x+r*.3} {y-r*.6} {x+r*.5} {y-r*.2}" for x, y, r in points], op, 1.6))


def f_curly_long(hl):
    pts = curls_back + [(72, 172, 16), (168, 172, 16), (82, 192, 14), (158, 192, 14), (66, 150, 15), (174, 150, 15)]
    return dict(back=curls(pts, hl), front=curls(curls_front, hl, .6), cast=False)


def f_curly_short(hl):
    pts = [(120, 56, 24), (94, 64, 20), (146, 64, 20), (78, 86, 18), (162, 86, 18), (74, 110, 16), (166, 110, 16), (78, 132, 14), (162, 132, 14)]
    return dict(back=curls(pts, hl), front=curls([(96, 68, 8), (108, 62, 8), (120, 60, 8), (132, 62, 8), (144, 68, 8)], hl, .6), cast=False)


def f_afro(hl):
    dots = [(120 + 46 * __import__("math").cos(a / 7), 84 + 46 * __import__("math").sin(a / 7)) for a in range(0, 44, 3)]
    return dict(back='<circle cx="120" cy="84" r="58" fill="HAIR"/>'
                + "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{hl}" opacity=".35"/>' for x, y in dots),
                front_shape="M84 100C80 70 98 54 120 54C142 54 160 70 156 100C154 86 148 76 138 72C130 68 124 68 120 68C116 68 108 68 102 72C92 76 86 86 84 100Z",
                front="", cast=False)


def f_braid(hl, tie):
    knots = [(86, 126), (88, 140), (90, 154), (92, 168), (94, 182), (96, 196)]
    braid = "".join(f'<ellipse cx="{x}" cy="{y}" rx="8.5" ry="9" fill="HAIR"/><path d="M{x-7} {y-3}C{x-2} {y+4} {x+3} {y+4} {x+7} {y-3}" stroke="#000" stroke-opacity=".25" stroke-width="1.3" fill="none"/>' for x, y in knots)
    return dict(back=CAP + '<path d="M84 96C80 108 82 118 86 124L94 120C90 112 88 104 88 96Z" fill="HAIR"/>',
                front_shape=SIDE_FRONT, front=strands(hl, ["M110 50C128 50 146 58 154 74"], .6, 1.6),
                acc=braid + f'<circle cx="97" cy="206" r="4" fill="{tie}"/>')


def f_pixie(hl):
    return dict(back='<path d="M78 102C74 62 96 44 120 44C144 44 166 62 162 102C164 114 162 124 158 130L82 130C78 124 76 114 78 102Z" fill="HAIR"/>',
                front_shape="M80 104C76 70 88 46 114 40C136 34 160 46 164 68C166 82 162 94 160 104C156 90 150 80 140 74C128 70 116 72 106 80C98 86 92 88 88 92C84 96 82 100 80 104Z",
                front=strands(hl, ["M96 60C110 46 134 42 152 52", "M90 72C106 58 128 54 156 64"], .6, 1.8))


def f_bun(hl):
    return dict(back='<circle cx="120" cy="42" r="19" fill="HAIR"/>' + strands(hl, ["M106 38C112 30 128 30 134 38"], .6, 1.6),
                front_shape=BACK_FRONT, front=strands(hl, ["M90 80C96 66 108 60 120 60", "M150 80C144 66 132 60 120 60"], .6, 1.5))


BOB_BACK = '<path d="M80 98C74 58 96 40 120 40C144 40 166 58 160 98C160 120 163 138 168 152C150 160 90 160 72 152C77 138 80 120 80 98Z" fill="HAIR"/>'

MASC_CAP = '<path d="M80 100C76 62 96 46 120 46C144 46 164 62 160 100Z" fill="HAIR"/>'


def m_buzz(hl):
    return dict(front_shape="M84 96C82 66 98 52 120 52C142 52 158 66 156 96C154 84 150 76 144 72C136 68 128 67 120 67C112 67 104 68 96 72C90 76 86 84 84 96Z",
                front="".join(f'<circle cx="{x}" cy="{y}" r=".9" fill="{hl}" opacity=".5"/>' for x in range(94, 148, 7) for y in (58, 63) if (x - 120) ** 2 < 900),
                cast=False)


def m_bald():
    return dict(back='<path d="M80 110C78 96 80 86 86 80L90 110Z" fill="HAIR"/><path d="M160 110C162 96 160 86 154 80L150 110Z" fill="HAIR"/>',
                acc='<ellipse cx="108" cy="66" rx="12" ry="5" fill="#fff" opacity=".22" transform="rotate(-18 108 66)"/>', cast=False)


def m_long(hl):
    return dict(back='<path d="M80 100C74 60 96 44 120 44C144 44 166 60 160 100C160 124 164 146 168 166C150 172 90 172 72 166C76 146 80 124 80 100Z" fill="HAIR"/>',
                front_shape=MID_FRONT, front=strands(hl, ["M118 50C106 56 94 66 88 84", "M122 50C134 56 146 66 152 84"], .55, 1.6))


def m_manbun(hl):
    return dict(back=MASC_CAP + '<circle cx="120" cy="44" r="14" fill="HAIR"/>',
                front_shape=BACK_FRONT, front=strands(hl, ["M92 78C98 64 110 58 120 58", "M148 78C142 64 130 58 120 58"], .55, 1.5))


def m_slick(hl):
    return dict(back=MASC_CAP,
                front_shape="M80 100C78 62 96 40 122 40C148 40 164 60 160 100C158 86 154 76 148 70C140 64 130 62 120 62C110 62 100 64 92 70C86 76 82 86 80 100Z",
                front=strands(hl, ["M96 60C108 48 130 44 150 54", "M92 70C104 56 128 52 154 62", "M104 50C116 44 132 44 144 48"], .6, 1.7))


def m_hightop(hl):
    return dict(front_shape="M84 100C82 80 84 60 88 42L152 42C156 60 158 80 156 100C154 88 150 80 144 76C134 72 126 72 120 72C114 72 106 72 96 76C90 80 86 88 84 100Z",
                front="".join(f'<circle cx="{x}" cy="{y}" r="1.4" fill="{hl}" opacity=".45"/>' for x in range(94, 150, 8) for y in range(48, 70, 7)),
                cast=False)


def m_fringe(hl):
    return dict(back=MASC_CAP,
                front_shape="M80 100C76 62 96 44 120 44C144 44 164 62 160 100C158 92 156 88 152 86L146 90L140 83L132 90L124 83L116 90L108 83L100 90L92 84C86 88 82 94 80 100Z",
                front=strands(hl, ["M100 56C112 50 130 50 144 58", "M96 66C108 60 128 60 148 68"], .55, 1.6))


def m_side(hl):
    return dict(back=MASC_CAP,
                front_shape="M80 100C78 64 98 44 124 44C148 44 164 62 160 100C158 86 154 78 146 72C136 66 124 66 112 66C104 66 100 64 98 60C92 70 84 84 80 100Z",
                front=strands(hl, ["M100 56C114 48 136 48 152 60", "M104 62C118 56 136 58 150 68"], .6, 1.7))


FULL_BEARD = '<path d="M83 108C84 138 100 158 120 159C140 158 156 138 157 108C153 122 148 130 141 134C134 131 128 130 120 130C112 130 106 131 99 134C92 130 87 122 83 108Z" fill="HAIR"/>'
SHORT_BEARD = '<path d="M83 110C84 136 100 154 120 155C140 154 156 136 157 110C153 122 148 132 140 136C134 133 128 132 120 132C112 132 106 133 100 136C92 132 87 122 83 110Z" fill="HAIR"/>'
STUBBLE = '<path d="M83 110C84 136 100 154 120 155C140 154 156 136 157 110C153 124 147 134 139 139C132 136 108 136 101 139C93 134 87 124 83 110Z" fill="HAIR" opacity=".3"/>'


def stache(n):
    return f'<path d="M104 131C110 126 118 126.5 120 128C122 126.5 130 126 136 131C130 130.5 124 130 120 131C116 130 110 130.5 104 131Z" fill="url(#{n}-hair)"/>'


def hoops(color):
    return f'<circle cx="81" cy="122" r="4" fill="none" stroke="{color}" stroke-width="1.8"/><circle cx="159" cy="122" r="4" fill="none" stroke="{color}" stroke-width="1.8" opacity=".85"/>'


def persona(fem, skin, iris, brow, hair, cloth, bg, clothes, style, **extra):
    d = dict(fem=fem, skin=skin, iris=iris, brow=brow, hair=hair, cloth=cloth, bg=bg, clothes=clothes)
    d.update(style)
    if "acc" in style and "acc" in extra:
        extra["acc"] = style["acc"] + extra["acc"]
    d.update(extra)
    return d


# Resto del catálogo (multi41): sin descripción en la landing, cada una con peinado, piel, ropa y fondo propios.
P["martina"] = persona(True, "clara", "#3b2a20", "#1e1612", ("#2e2420", "#0c0807"), ("#3b3f4a", "#22252d"), ("#f5f6f8", "#cfd4dc"), blazer("#16181d", "#f4f5f7"), f_bangs("#6a5a52"))
P["camila"] = persona(True, "media", "#5a3a22", "#4a3020", ("#9a6a44", "#4e3220"), ("#e86a92", "#c4466e"), ("#fff4f8", "#f8c6d8"), sweater("#a8345a"), f_ponytail("#d6a47a"), acc=headset())
P["lucia"] = persona(True, "oscura", "#2a1a10", "#140c08", ("#2a1d16", "#0c0806"), ("#f2c230", "#d49c10"), ("#fffaea", "#f7e2a0"), blouse("#a87808"), f_afro("#5a4434"), acc=hoops("#e3b445"))
P["julieta"] = persona(True, "clara", "#4d6b3a", "#8a4a2a", ("#c4683a", "#7a3418"), ("#2aa198", "#1a7a72"), ("#effaf8", "#b8e6df"), blouse("#0e5a54"), f_wavy_mid("#f0a070"), blush=.34,
                       beard="".join(f'<circle cx="{x}" cy="{y}" r=".9" fill="#b0663f" opacity=".45"/>' for x, y in [(99, 116), (103, 118), (96, 119), (141, 116), (137, 118), (144, 119), (120, 112)]))
P["florencia"] = persona(True, "trigueña", "#4a3020", "#3a2418", ("#a87a4a", "#5a3a1e"), ("#8fae7a", "#6a8a56"), ("#f5faf0", "#d2e6c2"), sweater("#4e6a3c"), f_curly_long("#d8b080"))
P["agustina"] = persona(True, "oliva", "#3b2414", "#2a1a10", ("#5a3a26", "#24160e"), ("#ffffff", "#e2e8f0"), ("#fdf6ee", "#f2d8bc"), shirt_open("#f6f8fb"), f_braid("#8a6048", "#e05a3a"))
P["mariana"] = persona(True, "media", "#3b2a20", "#5a3420", ("#8a5230", "#4a2810"), ("#2a3a6e", "#16234a"), ("#f1f4ff", "#c4cff2"), blazer("#101a38", "#eef2fb"), dict(back=BOB_BACK, front_shape=SIDE_FRONT, front=strands("#c08a5a", ["M110 50C128 50 146 58 154 74", "M106 56C122 58 140 64 150 78"], .6, 1.6)), acc=glasses("#8a2a2a"))
P["romina"] = persona(True, "morena", "#2a1a10", "#140c08", ("#2a1d16", "#0c0806"), ("#d6403a", "#a82824"), ("#fff3f1", "#f6c4bc"), blazer("#7a1a16", "#fbf1f0"), f_bun("#5a4434"), acc=earrings("#e3b445", 2.6))
P["natalia"] = persona(True, "clara", "#5a3a22", "#4a3020", ("#5e3e28", "#2a1a10"), ("#e0a82e", "#b8841a"), ("#fffaee", "#f5dfa6"), sweater("#8a6210"), f_pixie("#a07850"), acc=hoops("#c9c9c9"))
P["silvina"] = persona(True, "media", "#4a3a2a", "#8a847e", ("#d8d4ce", "#8e8a84"), ("#7a3e6e", "#58284e"), ("#fbf3fa", "#e6c8e0"), blazer("#3e1a38", "#f8f2f7"), f_wavy_mid("#ffffff"), acc=glasses("#5a2a50"))
P["andrea"] = persona(True, "trigueña", "#3b2a1e", "#8a6a44", ("#e2b870", "#9a7030"), ("#f07a5e", "#cc5a40"), ("#fff5f1", "#fbd0c2"), blouse("#a83e28"), f_long("#fbe2b0"))
P["veronica"] = persona(True, "clara", "#4f6a86", "#7a4a2e", ("#a85a34", "#5e2c14"), ("#8a94a6", "#5e6878"), ("#f4f6f9", "#d2d8e2"), blazer("#3c4454", "#fbfbfc"),
                        dict(back=CAP, front_shape=MID_FRONT, front=strands("#e09a68", ["M118 54C108 58 96 66 90 82", "M122 54C132 58 144 66 150 82"], .6, 1.5)), acc=earrings("#fbf7ee", 3))
P["lorena"] = persona(True, "morena", "#2e1d12", "#1a110c", ("#3a2a20", "#120c08"), ("#1f8a8a", "#126a6a"), ("#effafa", "#b0dede"), sweater("#0c5252"), f_long("#7a5e4a", mid=True))
P["daniela"] = persona(True, "trigueña", "#2e1d12", "#1a120e", ("#2e2420", "#0c0807"), ("#7ab0e8", "#4a88cc"), ("#f0f7ff", "#c8def6"), blouse("#2a5e98"), f_ponytail("#5a4a42"), acc=glasses("#2a2c36"))
P["micaela"] = persona(True, "oliva", "#3b2414", "#2a1a10", ("#4a3326", "#1a100b"), ("#b79ce6", "#9478cc"), ("#f8f4ff", "#e0d2fa"), sweater("#6a4ea8"), f_curly_short("#8a6048"), acc=earrings("#f2c14e", 2))
P["rocio"] = persona(True, "media", "#4a3020", "#5a3420", ("#8a4a2a", "#4a2410"), ("#4a7ab8", "#2e5a94"), ("#f2f6fc", "#c6d6ee"), shirt_open("#6a94cc"), f_bangs("#d08a5a"))
P["belen"] = persona(True, "clara", "#4f6a86", "#a8864e", ("#f0d690", "#b89448"), ("#efe4d0", "#d4c4a6"), ("#fbf8f2", "#ece2cc"), sweater("#b8a27a"), f_braid("#fff2c8", "#2a6ad6"), blush=.3)
P["milagros"] = persona(True, "oscura", "#2a1a10", "#140c08", ("#2a1d16", "#0c0806"), ("#e8b030", "#c48e14"), ("#f6f4ff", "#d2ccf2"), blazer("#8a6408", "#fbf6e8"), f_curly_long("#6a5040"))
P["antonella"] = persona(True, "oliva", "#2e1d12", "#3a2418", ("#6a4228", "#2a160a"), ("#1a9a6a", "#0e7a50"), ("#effaf4", "#b2e4cc"), blazer("#0a4a30", "#f2faf6"), f_wavy_mid("#b08058"), acc=hoops("#e3b445"))
P["carla"] = persona(True, "clara", "#3d5a6b", "#a09a90", ("#ece6da", "#b8ae9c"), ("#2a2c32", "#141518"), ("#f4f4f6", "#d6d8de"), sweater("#000000"), dict(back=BOB_BACK, front_shape=SIDE_FRONT,
                     front=strands("#ffffff", ["M110 50C128 50 146 58 154 74", "M106 56C122 58 140 64 150 78"], .7, 1.6)), acc=glasses("#c84a3a"))
P["noelia"] = persona(True, "trigueña", "#3b2414", "#6a3418", ("#d0703a", "#8a3a14"), ("#2c3e70", "#18264c"), ("#fff6f0", "#f6d2bc"), blouse("#c84a2a"), f_pixie("#f4a870"))

P["mateo"] = persona(False, "clara", "#5a3d24", "#4a3020", ("#8a6040", "#4a3018"), ("#f08a3a", "#cc6a1e"), ("#fff6ee", "#f8d4b2"), sweater("#9a4a10"), m_fringe("#c49a6a"))
P["santiago"] = persona(False, "media", "#3b2a1e", "#3a2618", ("#6a4a32", "#2e1e12"), ("#4a6a8a", "#2e4a66"), ("#f2f6fa", "#c8d6e4"), shirt_open("#e8eef6"), m_long("#a0785a"), beard=STUBBLE)
P["nicolas"] = persona(False, "trigueña", "#2e1d12", "#1a110c", ("#2a1d16", "#0c0806"), ("#3a8a5a", "#246a40"), ("#f0faf4", "#bce4cc"), sweater("#1a5a34"), m_buzz("#6a5040"), acc=glasses("#2a2c36"))
P["facundo"] = persona(False, "oliva", "#3b2414", "#2b1b12", ("#4a3020", "#1c120a"), ("#6a5a8a", "#4a3e6a"), ("#f6f4fb", "#d6d0ea"), shirt_open("#f6f8fb"), m_manbun("#8a6048"), beard=FULL_BEARD, stache=stache("facundo"))
P["joaquin"] = persona(False, "clara", "#4f6a86", "#2a1d16", ("#2e2420", "#0c0807"), ("#2a2c32", "#141518"), ("#f3f4f7", "#cdd1da"), suit_tie("#0c0d10", "#ffffff", "#2456e6"), m_slick("#6a5a52"))
P["federico"] = persona(False, "media", "#4a3526", "#7a746e", ("#9e9a94", "#6e6a64"), ("#8a5a3a", "#6a4024"), ("#fbf6f0", "#ead6c2"), blazer("#4a2e1a", "#f4efe8"), m_bald(), beard=SHORT_BEARD, stache=stache("federico"), brow_y=91)
P["pablo"] = persona(False, "oscura", "#2a1a10", "#140c08", ("#2a1d16", "#0c0806"), ("#e0e6ee", "#b8c2d0"), ("#eef6ff", "#b8d4f4"), shirt_open("#f4f7fb"), m_hightop("#5a4434"), beard=STUBBLE)
P["emiliano"] = persona(False, "clara", "#3d5a6b", "#a8864e", ("#e6c27a", "#a88038"), ("#c43a4a", "#9a2434"), ("#fff4f5", "#f6c8ce"), sweater("#7a1424"), m_side("#fff0c8"), stache=stache("emiliano"))

if __name__ == "__main__":
    for n, p in P.items():
        s = svg(n, p)
        for out in OUTS:
            out.mkdir(exist_ok=True)
            (out / f"{n}.svg").write_text(s)
        print(n, len(s.encode()))
