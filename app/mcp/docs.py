"""docs/MCP_HERRAMIENTAS.md y landing/src/data/mcp-tools.json (la página /desarrolladores/docs/mcp) desde el
catálogo (`make mcp-docs`). tests/test_mcp.py verifica que estén al día.

Uso: python -m app.mcp.docs  (escribe los dos)
"""
import json
import pathlib

from . import guides
from .catalog import CORE, DEFAULT, TOOLS, TOOLSETS

DOC = "docs/MCP_HERRAMIENTAS.md"

LANDING_JSON = "landing/src/data/mcp-tools.json"
PLANS = ("Free", "Mostrador", "Sucursal", "Red")
# Red no es un tier: es a medida (una instancia propia, la cotiza un asesor), con todo y sin tope. El tier
# Central se borró el 26-oct-2026 (docs/ARQUITECTURA.md).

# Qué es cada función del plan (services/features.TIER_HAS) y en qué planes está hoy, con el tope si lo hay
# (docs/features/MCP.md; cambia con los tiers).
FEATURES: dict[str, tuple[str, dict[str, str]]] = {
    "outbound_calls": ("Llamadas salientes (con un número asignado)", {"Mostrador": "", "Sucursal": "", "Red": ""}),
    "whatsapp": ("WhatsApp", {"Mostrador": "", "Sucursal": "", "Red": ""}),
    "contacts": ("Agenda de contactos", {"Mostrador": "500", "Sucursal": "5.000", "Red": "sin tope"}),
    "team": ("Equipo y derivaciones", {"Mostrador": "1 persona", "Sucursal": "2", "Red": "sin tope"}),
    "call_links": ("Link para llamar", {"Free": "1", "Mostrador": "", "Sucursal": "", "Red": ""}),
    "campaigns_whatsapp": ("Campañas de WhatsApp", {"Sucursal": "", "Red": ""}),
    "campaigns_voice": ("Campañas de llamadas", {"Sucursal": "de a 1", "Red": "a medida"}),
    "external_agent": ("Agente propio (tu endpoint, nuestra voz)", {"Sucursal": "", "Red": ""}),
    "custom_tools": ("Herramientas: llamadas a tus APIs", {"Sucursal": "10", "Red": "sin tope"}),
    "code_tools": ("Herramientas en código (JavaScript)", {"Sucursal": "", "Red": ""}),
    "white_label": ("Panel con tu marca (logo y colores)", {"Red": ""}),
    "advanced_reports": ("Reportes completos (resultados, mensajes, transferencias y campañas)",
                         {"Mostrador": "", "Sucursal": "", "Red": ""}),
    "direct_calls": ("Llamadas directas: tu equipo llama y atiende desde el panel, sin el agente",
                     {"Mostrador": "", "Sucursal": "", "Red": ""}),
}


def _plans_text(plans: dict[str, str]) -> str:
    parts = [f"{p} ({plans[p]})" if plans[p] else p for p in PLANS if p in plans]
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} y {parts[-1]}"


def _kind(t) -> str:
    return "lectura" if t.reads else "confirmar" if t.destructive else "escritura"


def render() -> str:
    lines = [
        "# Herramientas del servidor MCP",
        "",
        "Generado desde `app/mcp/catalog.py` con `make mcp-docs`: no editar a mano. Diseño en",
        "[`MCP.md`](features/MCP.md).",
        "",
        "- URL: `https://app.atentina.com.ar/mcp` (Streamable HTTP).",
        "- Auth: OAuth 2.1 (el cliente MCP descubre el login solo, por el 401 con `resource_metadata`) o",
        "  `Authorization: Bearer vaas_...`, una API key con el alcance `mcp` (o `mcp_read`: solo las de lectura;",
        "  panel → Desarrolladores). Las marcadas \"solo OAuth\" necesitan un usuario: con API key responden",
        "  `needs_oauth`; las \"solo API key\" (inferencia), con OAuth responden `needs_api_key`.",
        f"- Grupos: sin el parámetro, todos menos `inference`; `/mcp?toolsets=a,b` elige (`all` = todos los de",
        f"  cliente; `core` = {', '.join(f'`{c}`' for c in CORE)}). `get_plan_tools` va siempre.",
        "- `admin`: solo para un admin que, al autorizar, eligió \"Toda la plataforma\"; ese token ve `admin` más",
        "  las de cliente de los grupos pedidos, y en estas elige el cliente en cada llamada (`client_id`).",
        "- Una herramienta que el plan no incluye responde `feature_not_in_plan` con el motivo y los planes que la",
        "  tienen; `get_plan_tools` da la lista completa para el plan del cliente.",
        "",
        "## Funciones del plan",
        "",
        "| Función | Qué es | Planes (hoy) |",
        "|---|---|---|",
    ]
    lines += [f"| `{k}` | {name} | {_plans_text(plans)} |" for k, (name, plans) in FEATURES.items()]
    for toolset, title in TOOLSETS.items():
        tools = [t for t in TOOLS if t.toolset == toolset]
        lines += ["", f"## `{toolset}`: {title}", "", "| Herramienta | Qué hace | Tipo | Plan | API |",
                  "|---|---|---|---|---|"]
        for t in tools:
            plan = (" o ".join(f"`{f}`" for f in t.features) or ("admin" if toolset == "admin" else "todos")) + (
                " (solo OAuth)" if t.session else "") + (" (solo API key)" if t.api_key_only else "")
            api = f"`{t.method} {t.path}`" if t.path else "—"
            kind = "**confirmar**" if t.destructive else _kind(t)
            lines.append(f"| `{t.name}` | {t.description.replace('|', '/')} | {kind} | {plan} | {api} |")
    lines += ["", "## Resources y prompts", "",
              "| URI o nombre | Qué es |", "|---|---|"]
    lines += [f"| `{r['uri']}` | {r['title']} |" for r in guides.list_resources()]
    lines += [f"| prompt `{p['name']}` | {p['description']} |" for p in guides.list_prompts()]
    lines += ["", "Tipo **confirmar**: borra, cancela, corta, llama o manda mensajes (`destructiveHint`); el cliente",
              "MCP le pide confirmación al usuario."]
    return "\n".join(lines) + "\n"


def render_landing() -> str:
    """Los datos de /desarrolladores/docs/mcp: grupos, herramientas y funciones por plan. Sin `admin`: es
    interno."""
    public = [t for t in TOOLS if t.toolset != "admin"]
    data = {
        "toolsets": [{"id": k, "title": v, "core": k in CORE, "default": k in DEFAULT}
                     for k, v in TOOLSETS.items() if k != "admin"],
        "plans": list(PLANS),
        "features": [{"id": k, "name": name, "plans": dict(plans)}
                     for k, (name, plans) in FEATURES.items()],
        "tools": [{"name": t.name, "toolset": t.toolset, "title": t.title, "description": t.description,
                   "kind": _kind(t), "features": list(t.features), "oauth": t.session, "api_key": t.api_key_only}
                  for t in public],
        "resources": guides.list_resources(),
        "prompts": guides.list_prompts(),
    }
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    root = pathlib.Path(__file__).parents[2]
    (root / DOC).write_text(render())
    (root / LANDING_JSON).write_text(render_landing())
    print(f"{DOC} y {LANDING_JSON}: {len(TOOLS)} herramientas")
