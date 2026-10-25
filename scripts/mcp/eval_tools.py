"""¿Elige bien Claude entre las herramientas del MCP? (docs/MCP_PLAN.md, sección 13).

Le da a un modelo (por OpenRouter, API compatible con OpenAI) las herramientas tal como las lista el servidor
(`server._describe`) y un pedido del usuario en español; mira cuál llama primero. Si llama a get_plan_tools
(lo que pide la descripción), le devuelve un plan con todo y toma la siguiente. Acierto: la primera
herramienta está entre las esperadas del caso (pasos previos razonables incluidos, ej. list_agents antes de
start_call). Sin herramienta: error.

    make mcp-eval [MODELS=anthropic/claude-sonnet-5.5,anthropic/claude-haiku-5.5]

Sin la API ni base: arma las herramientas desde el catálogo. Gasta tokens de OpenRouter (OPENROUTER_API_KEY):
~20k de entrada por pedido con las 87. Deja el detalle en scratch/mcp-eval/.
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import pathlib
import sys
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AUTH_SECRET", "eval")

from app.main import app  # noqa: E402
from app.mcp import catalog, server  # noqa: E402

URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM = ("Sos un asistente con acceso a la cuenta de Atentina del usuario por un servidor MCP. "
          + server.INSTRUCTIONS + " Usá las herramientas para responder; no inventes datos.")

# (pedido, herramientas que valen como primera llamada)
CASES: list[tuple[str, set[str]]] = [
    ("¿Qué agentes tengo?", {"list_agents"}),
    ("Creá un agente para una veterinaria que dé turnos de lunes a viernes.",
     {"create_agent", "list_agent_templates", "get_agent_schema", "get_agent_template"}),
    ("Cambiale la voz al agente Peluquería Demo por una de hombre.", {"list_agents", "list_voices", "get_agent"}),
    ("Probá el agente Peluquería Demo como si fueras un cliente que quiere un turno.",
     {"list_agents", "test_agent_start"}),
    ("¿Qué voces de mujer hay?", {"list_voices"}),
    ("Mostrame las versiones anteriores del agente Peluquería Demo.", {"list_agents", "list_agent_versions"}),
    ("¿Cómo salieron las llamadas de ayer?", {"list_calls", "get_stats", "get_daily_stats"}),
    ("Mostrame la transcripción de la última llamada.", {"list_calls"}),
    ("¿Cuántos minutos llevo usados este mes?", {"get_usage"}),
    ("Llamá al +5493515550101 con el agente de turnos para confirmarle el turno de mañana.",
     {"list_agents", "start_call", "list_phone_numbers"}),
    ("Bloqueá el número 351 555 0199, nos llama para molestar.", {"block_number"}),
    ("Cortá la llamada que está en curso ahora.", {"list_calls", "hangup_call"}),
    ("¿A qué agente va cada uno de mis números?", {"list_phone_numbers"}),
    ("Dame las llamadas por día de la última semana.", {"get_daily_stats", "list_calls"}),
    ("Cargá a Juan Pérez, 351 555 0111, con la etiqueta vip.", {"upsert_contacts"}),
    ("Buscá el contacto Martina.", {"list_contacts"}),
    ("Importá este CSV de contactos:\ntelefono,nombre\n3515550120,Ana\n3515550121,Luis", {"import_contacts"}),
    ("Dale de baja al 351 555 0103, no quiere que lo llamemos más.", {"add_optout"}),
    ("Armá una campaña de llamadas a los contactos con la etiqueta demo, sin lanzarla.",
     {"create_campaign", "list_agents", "get_campaign_plan", "list_contacts"}),
    ("¿Cómo va la campaña Recordatorio de turnos?", {"list_campaigns", "get_campaign"}),
    ("Pausá la campaña que está corriendo.", {"list_campaigns", "pause_campaign"}),
    ("Pasame el reporte de la campaña de turnos.", {"list_campaigns", "get_campaign_report"}),
    ("Sumá a Pedro Gómez, 351 555 0177, al equipo.", {"create_team_member"}),
    ("¿En qué horario deriva el área de Ventas?", {"list_handoff_areas", "get_handoff_area"}),
    ("Mostrame las derivaciones a personas de hoy.", {"list_events", "list_calls"}),
    ("¿Qué plantillas de WhatsApp tengo aprobadas?", {"list_whatsapp_accounts", "list_whatsapp_templates"}),
    ("Cambiá el agente que atiende el WhatsApp por Peluquería Demo.",
     {"list_whatsapp_accounts", "update_whatsapp_account", "list_agents"}),
    ("Quiero un link para que la gente hable con el agente desde la web.",
     {"list_agents", "create_call_link", "get_call_link"}),
    ("Regenerá el link para llamar del agente, se filtró.", {"list_agents", "get_call_link", "rotate_call_link"}),
    ("¿Qué incluye mi plan?", {"get_plan_tools", "get_plan_features"}),
    ("Mandá el resumen por mail de cada llamada a ventas@acme.com.", {"update_call_emails", "get_call_emails"}),
    ("¿Qué API keys tengo?", {"list_api_keys"}),
    ("¿Puedo hacer campañas de WhatsApp con mi plan?", {"get_plan_tools", "get_plan_features", "get_campaign_plan"}),
]


def tools_for(toolsets: str | None) -> list[dict]:
    openapi = app.openapi()
    who = server.Identity("oauth", "eval", "eval", "")
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                               "parameters": t["inputSchema"]}}
            for t in (server._describe(x, openapi) for x in server._visible(toolsets, who))]


PLAN_STUB = json.dumps({"plan": "Central", "free": False,
                        "tools": {"available": sorted(catalog.BY_NAME), "unavailable": [], "needs_oauth": []}})


def run_case(model: str, tools: list[dict], prompt: str, key: str) -> dict:
    """La primera herramienta que no sea get_plan_tools (o get_plan_tools si es lo único que llamó)."""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    calls, usage = [], {"prompt_tokens": 0, "completion_tokens": 0, "requests": 0}
    for _ in range(3):
        for attempt in range(4):
            r = httpx.post(URL, headers={"Authorization": f"Bearer {key}"}, timeout=120,
                           json={"model": model, "messages": messages, "tools": tools, "temperature": 0,
                                 "max_tokens": 1024})
            if r.status_code == 200 and r.json().get("choices"):
                break
            time.sleep(2 ** attempt)
        body = r.json()
        if not body.get("choices"):
            return {"first": None, "calls": calls, "error": str(body)[:300], **usage}
        usage["requests"] += 1
        for k in ("prompt_tokens", "completion_tokens"):
            usage[k] += body.get("usage", {}).get(k, 0)
        msg = body["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        names = [tc["function"]["name"] for tc in tool_calls]
        calls += names
        other = [n for n in names if n != "get_plan_tools"]
        if other:
            return {"first": other[0], "calls": calls, **usage}
        if not names:
            return {"first": calls[0] if calls else None, "calls": calls, "text": (msg.get("content") or "")[:200],
                    **usage}
        # Solo get_plan_tools: se le contesta con un plan con todo y se sigue.
        messages.append(msg)
        messages += [{"role": "tool", "tool_call_id": tc["id"], "content": PLAN_STUB} for tc in tool_calls]
    return {"first": "get_plan_tools", "calls": calls, **usage}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="anthropic/claude-sonnet-5.5,anthropic/claude-haiku-5.5")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("Falta OPENROUTER_API_KEY")
    configs = {"default": tools_for(None), "core": tools_for("core")}
    core_names = {t["function"]["name"] for t in configs["core"]}
    out_dir = ROOT / "scratch" / "mcp-eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    jobs = []
    for model in args.models.split(","):
        for cfg, tools in configs.items():
            for prompt, expected in CASES:
                if cfg == "core" and not expected & core_names:
                    continue
                jobs.append((model, cfg, tools, prompt, expected))
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(run_case, m, t, p, key): (m, c, p, e) for m, c, t, p, e in jobs}
        for f in concurrent.futures.as_completed(futures):
            m, c, p, e = futures[f]
            res = f.result()
            results.append({"model": m, "config": c, "prompt": p, "expected": sorted(e),
                            "ok": res.get("first") in e, **res})
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    (out_dir / f"{stamp}.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"Herramientas: default {len(configs['default'])}, core {len(configs['core'])}. "
          f"Detalle: scratch/mcp-eval/{stamp}.json\n")
    print(f"{'modelo':34} {'config':8} {'acierto':>9} {'en core':>9} {'tokens entrada/pedido':>22}")
    core_prompts = {p for p, e in CASES if e & core_names}
    for model in args.models.split(","):
        for cfg in configs:
            rows = [r for r in results if r["model"] == model and r["config"] == cfg]
            if not rows:
                continue
            ok = sum(r["ok"] for r in rows)
            in_core = [r for r in rows if r["prompt"] in core_prompts]
            ok_core = sum(r["ok"] for r in in_core)
            tokens = sum(r["prompt_tokens"] for r in rows) / max(sum(r.get("requests", 1) for r in rows), 1)
            print(f"{model:34} {cfg:8} {ok:>3}/{len(rows):<5} {ok_core:>3}/{len(in_core):<5} {tokens:>22,.0f}")
    misses = [r for r in results if not r["ok"]]
    if misses:
        print("\nErrores:")
        for r in sorted(misses, key=lambda r: (r["model"], r["config"], r["prompt"])):
            print(f"- [{r['model'].split('/')[-1]} {r['config']}] {r['prompt'][:70]!r}: {r.get('first')} "
                  f"(esperaba {', '.join(r['expected'])}){' ' + r['error'] if r.get('error') else ''}")


if __name__ == "__main__":
    main()
