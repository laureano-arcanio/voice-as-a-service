"""docs/MCP_HERRAMIENTAS.md desde el catálogo (`make mcp-docs`). tests/test_mcp.py verifica que esté al día.

Uso: python -m app.mcp.docs  (escribe el archivo)
"""
import pathlib

from .catalog import CORE, TOOLS, TOOLSETS

DOC = "docs/MCP_HERRAMIENTAS.md"

# Qué es cada función del plan (services/features.TIER_HAS) y en qué planes está hoy
# (docs/MCP_PLAN.md, sección 6; cambia con los tiers).
FEATURES = {
    "outbound_calls": ("Llamadas salientes", "Mostrador, Sucursal y Central (con un número asignado)"),
    "whatsapp": ("WhatsApp", "Mostrador, Sucursal y Central"),
    "contacts": ("Agenda de contactos", "Mostrador (500), Sucursal (5.000) y Central (sin tope)"),
    "team": ("Equipo y derivaciones", "Mostrador (1 persona), Sucursal (2) y Central (sin tope)"),
    "call_links": ("Link para llamar", "Todos (Free: 1)"),
    "campaigns_whatsapp": ("Campañas de WhatsApp", "Sucursal y Central"),
    "campaigns_voice": ("Campañas de llamadas", "Sucursal (de a 1) y Central (hasta 3)"),
}


def render() -> str:
    lines = [
        "# Herramientas del servidor MCP",
        "",
        "Generado desde `app/mcp/catalog.py` con `make mcp-docs`: no editar a mano. Diseño en",
        "[`MCP_PLAN.md`](MCP_PLAN.md).",
        "",
        "- URL: `https://mcp.atentina.com.ar/mcp` (Streamable HTTP). Auth: `Authorization: Bearer vaas_...`,",
        "  una API key con el alcance `mcp` (panel → API keys).",
        f"- Grupos: `/mcp?toolsets=a,b` (`all` = todos). Sin el parámetro: `core` = {', '.join(f'`{c}`' for c in CORE)}.",
        "  `get_plan_tools` va siempre.",
        "- Una herramienta que el plan no incluye responde `feature_not_in_plan` con el motivo y los planes que la",
        "  tienen; `get_plan_tools` da la lista completa para el plan del cliente.",
        "",
        "## Funciones del plan",
        "",
        "| Función | Qué es | Planes (hoy) |",
        "|---|---|---|",
    ]
    lines += [f"| `{k}` | {name} | {plans} |" for k, (name, plans) in FEATURES.items()]
    for toolset, title in TOOLSETS.items():
        tools = [t for t in TOOLS if t.toolset == toolset]
        lines += ["", f"## `{toolset}`: {title}", "", "| Herramienta | Qué hace | Plan | API |", "|---|---|---|---|"]
        for t in tools:
            plan = " o ".join(f"`{f}`" for f in t.features) or "todos"
            api = f"`{t.method} {t.path}`" if t.path else "—"
            lines.append(f"| `{t.name}` | {t.description.replace('|', '/')} | {plan} | {api} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = pathlib.Path(__file__).parents[2] / DOC
    path.write_text(render())
    print(f"{path}: {len(TOOLS)} herramientas")
