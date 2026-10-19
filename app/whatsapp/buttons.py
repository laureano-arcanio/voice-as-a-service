"""Links a vistas de apps como botón de WhatsApp (mensaje interactivo cta_url, 16-oct-2026).

Las URLs firmadas del gateway (https://<APPS_PUBLIC_HOST>/{cliente}/{app}/{vista}/?k=...) son largas
e ilegibles en el chat: la respuesta sale sin la URL y con un botón cuyo rótulo es el título de la
vista. Límites de Meta: cuerpo hasta 1024 caracteres, rótulo hasta 20. Lo arma service._send.
"""
import re
from dataclasses import dataclass

BODY_MAX = 1024
LABEL_MAX = 20
TRAILING = ".,;:)]»\"'"
BULLET = re.compile(r"^\s*([-•*]|\d+[.)])\s+")


@dataclass
class AppLink:
    url: str
    client: str
    app: str
    view: str
    line: str          # el resto de su línea, sin la URL ("Anahi Revelante" en "- Anahi Revelante: <url>")


def extract(body: str, host: str) -> tuple[str, list[AppLink]]:
    """El texto sin los links de vistas, y los links en orden. Sin host o sin links: (body, []).
    De una línea con link queda el resto como frase ("asignáselo en su perfil: <url>" → "asignáselo en
    su perfil"), salvo que sea un ítem de lista o haya varios links: entonces es el rótulo de su botón."""
    if not host:
        return body, []
    pattern = re.compile(rf"https?://{re.escape(host)}/([\w-]+)/([\w-]+)/([\w-]+)/\S*", re.IGNORECASE)
    links: list[AppLink] = []
    rows: list[tuple[str, bool]] = []          # (texto de la línea sin URLs, tenía link)
    for line in body.split("\n"):
        rest = line
        for m in pattern.finditer(line):
            url = m.group(0).rstrip(TRAILING)
            rest = rest.replace(url, "", 1)
            links.append(AppLink(url, m.group(1), m.group(2), m.group(3), ""))
        if rest is line:
            rows.append((line, False))
            continue
        rest = rest.strip()
        label = BULLET.sub("", rest).strip().rstrip(":").strip().strip("*_").strip()
        for link in links:
            if link.line == "" and link.url in line:
                link.line = label
        rows.append((rest, True))
    if not links:
        return body, []
    keep = []
    for rest, had_link in rows:
        if not had_link:
            keep.append(rest)
        elif rest and len(links) == 1 and not BULLET.match(rest):
            # "en su perfil: <url>." deja "en su perfil: ." → "en su perfil"
            keep.append(re.sub(r"\s+[.,;]$", "", re.sub(r"\s*:\s*[.,;]?$", "", rest.rstrip())))
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip()
    return text, links


def label(title: str) -> str:
    """El rótulo del botón: el título de la vista, hasta 20 caracteres."""
    title = (title or "Abrir").strip()
    return title if len(title) <= LABEL_MAX else title[:LABEL_MAX - 1].rstrip() + "…"
