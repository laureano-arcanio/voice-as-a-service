"""Datos del contacto de una campaña de voz o de una llamada suelta en la conversación
(docs/features/CAMPANAS.md).

`vars` es la copia de los datos del contacto que guarda la campaña (nombre, teléfono, email).
Llegan a la conversación de tres formas:
- La apertura acepta `{{variable}}`: se reemplaza con su valor. Una variable que el contacto no tiene queda
  vacía (no se lee "{{deuda}}" en voz alta) y el texto se acomoda: "Hola {{nombre}}, soy..." -> "Hola, soy...".
- Los datos cuyo nombre coincide con un campo del workflow lo precargan (`state.fields`): el agente no
  los pregunta. Sirve el valor que el tipo del campo acepta; el que no, va con el resto.
- El resto va al prompt como "Datos del contacto" (`Progress.contact`).

Una llamada suelta (pantalla Llamadas, `POST /calls` con `contact_id` y `context`) usa los mismos `vars` del
contacto de la agenda, y además el motivo en texto libre (`Progress.context`), que va al prompt como
"MOTIVO DEL LLAMADO".
"""
import re
import unicodedata
from typing import Any

from .models import ConversationState, Workflow
from .workflow import check_updates

VAR_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
MAX_ENTRIES = 30
MAX_VALUE_CHARS = 200
# El motivo de una llamada suelta: el mensaje que el contacto dejo en la web entra entero.
MAX_CONTEXT_CHARS = 2000
# Datos que viajan en `vars` pero no son del contacto: los valores posicionales de una plantilla de WhatsApp.
INTERNAL = ("params",)


def key(name: str) -> str:
    """Nombre de variable comparable: sin acentos ni mayusculas, con _ (igual que los datos del contacto)."""
    text = unicodedata.normalize("NFD", str(name or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")[:64]


def fmt(value: Any) -> str:
    """El valor como texto, en una linea. Vacio para None."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"\s+", " ", str(value)).strip()


def _lookup(vars: dict, name: str) -> str:
    wanted = key(name)
    for k, v in vars.items():
        if k not in INTERNAL and key(k) == wanted:
            return fmt(v)
    return ""


def render_template(text: str, vars: dict | None) -> str:
    """Cambia cada `{{variable}}` por su valor en `vars`. Sin valor queda vacio, y si eso deja un espacio
    antes de una coma o un cierre ("Hola , soy"), se acomoda. Sin variables, el texto no se toca."""
    vars = vars or {}
    missing = False

    def swap(m: re.Match) -> str:
        nonlocal missing
        value = _lookup(vars, m.group(1))
        missing = missing or not value
        return value

    out = VAR_RE.sub(swap, text)
    if missing:
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"[ \t]+([,.;:!?)])", r"\1", out).strip()
    return out


def preload(workflow: Workflow, vars: dict | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """(campos precargados, datos del contacto): los datos que se llaman como un campo del workflow y
    cuyo valor ese campo acepta van a `fields`; el resto, sin vacios, queda como dato del contacto."""
    clean = {k: v for k, v in (vars or {}).items() if k not in INTERNAL and fmt(v) != ""}
    candidates, used = {}, {}
    for k, v in clean.items():
        if (name := key(k)) in workflow.fields and name not in candidates:
            candidates[name], used[name] = v, k
    valid, _ = check_updates(workflow, candidates)
    rest = {k: v for k, v in clean.items() if k not in {used[name] for name in valid}}
    return valid, rest


def _lines(data: dict) -> str:
    items = [(k, fmt(v)) for k, v in data.items() if fmt(v)][:MAX_ENTRIES]
    return "\n".join(f"- {k}: {v[:MAX_VALUE_CHARS]}" for k, v in items)


def render_contact(contact: dict | None) -> str:
    """El bloque "Datos del contacto" del prompt, o vacio si no hay."""
    lines = _lines(contact or {})
    if not lines:
        return ""
    return ("DATOS DEL CONTACTO (de la campaña o la llamada que originó la conversación; usalos con naturalidad, "
            f"sin leerlos como una lista ni inventar otros):\n{lines}")


def render_context(context: str | None) -> str:
    """El bloque "Motivo del llamado" del prompt (llamada suelta), o vacio si no hay."""
    if not context or not context.strip():
        return ""
    return ("MOTIVO DEL LLAMADO (lo que dejó escrito el contacto, o el equipo, antes de esta llamada: es la razón por "
            "la que llamás. Usalo para ir al punto y no preguntes lo que ya dice; no lo leas textual ni inventes lo "
            f"que no dice):\n{context.strip()[:MAX_CONTEXT_CHARS]}")


def render_known(state: ConversationState) -> str:
    """Los campos ya cargados al empezar (la campaña o el telefono de la llamada), para el prompt."""
    known = {n: state.fields[n] for n in state.progress.preloaded if state.fields.get(n) is not None}
    lines = _lines(known)
    if not lines:
        return ""
    return f"DATOS YA CONOCIDOS (no los preguntes; si hace falta, confirmalos):\n{lines}"


def prompt_block(state: ConversationState | None) -> str:
    """Lo que la campaña o la llamada le suman al prompt (datos del contacto, motivo del llamado y campos ya
    conocidos), o vacio."""
    if state is None:
        return ""
    blocks = (render_contact(state.progress.contact), render_context(state.progress.context), render_known(state))
    return "\n\n".join(b for b in blocks if b)
