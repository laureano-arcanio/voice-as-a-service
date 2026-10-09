"""Layout comun de los mails (cabecera, pie) y las piezas para armar el contenido.

HTML con tablas y estilos en linea, que es lo que aguantan los clientes de correo. Los colores
son los de la marca (docs/DESIGN_GUIDELINE.md, seccion 3): un mail no puede usar las variables CSS.
Todo texto dinamico pasa por `esc`; las piezas devuelven `Safe` (ya escapado).
"""
import html
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

from ..config import settings


class Safe(str):
    """HTML ya escapado."""


BG, BG_2, LINE = "#f6f8fb", "#f1f4f9", "#e3e8ef"
INK, INK_2, MUTED = "#0b1220", "#33415c", "#64748b"
ACCENT, ACCENT_ON_DARK, CTA_INK = "#2456e6", "#9db6ff", "#f4f6fa"
FONT = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

_LAYOUT = Template((Path(__file__).parent / "templates" / "layout.html").read_text(encoding="utf-8"))


def esc(value: object) -> Safe:
    return value if isinstance(value, Safe) else Safe(html.escape(str(value), quote=True))


def heading(text: str) -> Safe:
    return Safe(f'<h1 style="margin:0 0 16px;font-family:{FONT};font-size:24px;line-height:1.25;'
                f'font-weight:800;letter-spacing:-0.02em;color:{INK};">{esc(text)}</h1>')


def paragraph(*parts: object, muted: bool = False) -> Safe:
    color, size = (MUTED, "14px") if muted else (INK_2, "16px")
    return Safe(f'<p style="margin:0 0 16px;font-size:{size};line-height:1.6;color:{color};">'
                f'{"".join(esc(p) for p in parts)}</p>')


def strong(text: object) -> Safe:
    return Safe(f'<strong style="color:{INK};">{esc(text)}</strong>')


def link(url: str, label: str | None = None) -> Safe:
    return Safe(f'<a href="{esc(url)}" style="color:{ACCENT};text-decoration:underline;">{esc(label or url)}</a>')


def button(url: str, label: str) -> Safe:
    """Boton "a prueba de Outlook": una celda con fondo, no un <a> con padding."""
    return Safe(
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 24px;"><tr>'
        f'<td bgcolor="{ACCENT}" style="background:{ACCENT};border-radius:8px;">'
        f'<a href="{esc(url)}" style="display:inline-block;padding:13px 26px;font-family:{FONT};font-size:16px;'
        f'font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">{esc(label)}</a>'
        '</td></tr></table>')


def steps(items: list[object]) -> Safe:
    rows = "".join(
        '<tr>'
        f'<td valign="top" width="28" style="width:28px;padding:0 0 10px;font-size:15px;font-weight:700;color:{ACCENT};">{i}.</td>'
        f'<td valign="top" style="padding:0 0 10px;font-size:15px;line-height:1.55;color:{INK_2};">{esc(item)}</td>'
        '</tr>' for i, item in enumerate(items, 1))
    return Safe(f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
                f'style="margin:0 0 12px;">{rows}</table>')


def details(title: str, rows: list[tuple[str, object]], note: object | None = None) -> Safe:
    """Cuadro de datos (plan, numero): titulo, filas etiqueta/valor y una nota opcional."""
    body = "".join(
        '<tr>'
        f'<td style="padding:6px 0;border-top:1px solid {LINE};font-size:14px;color:{MUTED};">{esc(label)}</td>'
        f'<td align="right" style="padding:6px 0;border-top:1px solid {LINE};font-size:14px;font-weight:600;'
        f'color:{INK};">{esc(value)}</td>'
        '</tr>' for label, value in rows)
    note_html = (f'<p style="margin:10px 0 0;font-size:13px;line-height:1.5;color:{MUTED};">{esc(note)}</p>'
                 if note else "")
    return Safe(
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'style="margin:0 0 24px;background:{BG};border:1px solid {LINE};border-radius:10px;"><tr>'
        f'<td style="padding:16px 20px;font-family:{FONT};">'
        f'<div style="margin:0 0 6px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
        f'color:{MUTED};">{esc(title)}</div>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{body}</table>'
        f'{note_html}</td></tr></table>')


def render(title: str, preheader: str, content: list[Safe], reason: str) -> str:
    """Mail completo. `reason`: por que le llega (va en el pie)."""
    return _LAYOUT.substitute(
        title=esc(title), preheader=esc(preheader), content="\n".join(content), reason=esc(reason),
        site_url=esc(settings.site_url), site_host=esc(urlsplit(settings.site_url).netloc or settings.site_url),
        support_email=esc(settings.support_email),
        bg=BG, bg_2=BG_2, line=LINE, ink=INK, ink_2=INK_2, muted=MUTED, accent=ACCENT,
        accent_on_dark=ACCENT_ON_DARK, cta_ink=CTA_INK, font=FONT)
