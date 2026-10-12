"""Casos de uso de una app (atentina-apps) contra el motor assistant real: el LLM del stack, la app y el
OCR de archivos. Los casos son de cada app (clients/<cliente>/<app>/casos/casos.yaml, formato en su
encabezado); este runner es genérico.

Lo lanza `make casos A=<cliente>/<app>` desde atentina-apps (copia descartable de la app con su seed),
adentro de la imagen de app (tesseract, red atentina-apps, vllm-llm) y con una base SQLite propia:

  docker compose run --rm --no-deps -e DB_DSN=sqlite:////tmp/casos.db -e APP_TOKEN=... -e APP_BASE_URL=... \\
    -v <dir de la app>:/cliente:ro -v $PWD/scripts:/app/scripts:ro -v $PWD/scratch:/app/scratch \\
    app python scripts/apps/casos.py /cliente/casos/casos.yaml

Reporte en scratch/casos_apps/<slug>/<fecha>/ (report.md y casos.json). CASOS=1.1,2.4 corre solo esos.
"""
import asyncio
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import yaml

from app.agents.definitions import DbDefinitions
from app.apps import attachments, registry
from app.apps import jobs as app_jobs
from app.config import settings
from app.conversation.engine import ConversationEngine
from app.conversation.store import ConversationStore
from app.db import create_schema, make_engine, make_sessions
from app.llm.client import LLMClient
from app.models import Client, Tier
from app.services import agents as agent_service

ACTOR = "wa:5490000000000"
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".pdf": "application/pdf"}


def definition(spec: dict, base: pathlib.Path) -> dict:
    """El agente assistant de los casos: su definición (agent, objective, conversation.rules, knowledge) es
    configuración de la app (`agente: agente.yaml`, o inline), con todas las herramientas de la app."""
    agente = spec["agente"]
    if isinstance(agente, str):
        agente = yaml.safe_load((base / agente).read_text())
    return {"engine": "assistant", "conversation": {"opening": "Hola", "rules": []},
            "completion": {"outcomes": [{"id": "default", "label": "Conversación", "message": "Chau"}]},
            **agente, "tools": [{"app": spec["app"], "tools": ["*"]}]}


def calls(turns: list[dict], tool: str) -> list[str]:
    """Las entradas de las llamadas a la herramienta (no las pendientes ni los controles)."""
    return [h for t in turns for h in t["herramientas"] if h.startswith(tool + " ")]


def check(turns: list[dict], rules: list[dict]) -> list[str]:
    used = {h.split(" ", 1)[0] for t in turns for h in t["herramientas"] if "->" in h}
    reply = " ".join(t["asistente"] for t in turns)
    fails = []
    for rule in rules:
        (kind, value), = rule.items()
        if kind == "usa" and not set(value.split("|")) & used:
            fails.append(f"no usó {value}")
        elif kind == "no_usa" and value in used:
            fails.append(f"usó {value}")
        elif kind == "ultimo_no_usa" and calls(turns[-1:], value):
            fails.append(f"en el último mensaje usó {value}")
        elif kind == "dice" and not re.search(value, reply, re.DOTALL):
            fails.append(f"la respuesta no dice /{value}/")
        elif kind == "no_dice" and re.search(value, reply, re.DOTALL):
            fails.append(f"la respuesta dice /{value}/")
        elif kind in ("args", "args_no"):
            tool, pattern = value
            hit = any(re.search(pattern, c.split(" -> ")[0]) for t in tool.split("|") for c in calls(turns, t))
            if kind == "args" and not hit:
                fails.append(f"{tool} sin /{pattern}/ en los argumentos")
            elif kind == "args_no" and hit:
                fails.append(f"{tool} con /{pattern}/ en los argumentos")
    return fails


async def text_of(message, base: pathlib.Path) -> str:
    if isinstance(message, str):
        return message
    path = base / "archivos" / message["archivo"]
    data = path.read_bytes()
    return attachments.turn_text(data, await attachments.read(data, MIME.get(path.suffix.lower(), "image/png")),
                                 message.get("texto"))


async def main(path: pathlib.Path) -> None:
    spec = yaml.safe_load(path.read_text())
    now = app_jobs.local_now()
    out = pathlib.Path("scratch/casos_apps") / spec["app"] / now.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    engine_db = make_engine(os.environ["DB_DSN"])
    create_schema(engine_db)
    sessions = make_sessions(engine_db)
    with sessions() as s:
        tier = Tier(name="Casos")
        s.add(tier)
        s.flush()
        client = Client(name="Casos", slug="casos", tier_id=tier.id)
        s.add(client)
        s.flush()
        app = registry.register(s, spec["app"], os.environ["APP_BASE_URL"], os.environ["APP_TOKEN"])
        app.client_id = client.id
        s.flush()
        agent = agent_service.create_agent(s, client, name="Asistente", slug="asistente", description="",
                                           definition=definition(spec, path.parent.parent), template_id=None, user_id=None)
        s.commit()
        client_id, agent_id, app_id = client.id, agent.id, app.id
    llm = LLMClient(settings.vllm_llm_base_url, settings.vllm_api_key, settings.vllm_llm_model)
    engine = ConversationEngine(llm, ConversationStore(sessions), DbDefinitions(sessions))
    only = set(filter(None, os.environ.get("CASOS", "").split(",")))
    results = []
    for case in spec["casos"]:
        if only and case["id"] not in only:
            continue
        state, _ = engine.start_conversation(agent_id, client_id, channel="whatsapp", opening=False)
        turns, started = [], time.perf_counter()
        for message in case["mensajes"]:
            t0 = time.perf_counter()
            state, turn = await engine.process_turn(state.conversation_id, await text_of(message, path.parent),
                                                    actor=ACTOR)
            trace = state.messages[-1].llm or []
            turns.append({"usuario": message if isinstance(message, str) else f"[archivo {message['archivo']}]",
                          "asistente": turn.assistant_message, "ms": round((time.perf_counter() - t0) * 1000),
                          "pasos": sum(t["kind"] == "paso" for t in trace),
                          "pasos_ms": [t["ms"] for t in trace if t["kind"] == "paso"],
                          "pasos_chars": [(len(t.get("reasoning") or ""), len(t.get("output") or ""))
                                          for t in trace if t["kind"] == "paso"],
                          "herramientas": [f"{t['input'][:200]} -> {t['output'][:300]}" for t in trace
                                           if t["kind"] in ("herramienta", "pendiente", "control")]})
        fails = check(turns, case.get("chequeos", []))
        results.append({"caso": case["id"], "proceso": case["proceso"], "ok": not fails, "fallas": fails,
                        "turnos": turns, "ms": round((time.perf_counter() - started) * 1000)})
        print(f"{'OK ' if not fails else 'MAL'} {case['id']:5} {case['proceso']:34} {results[-1]['ms']:6} ms  "
              f"{'; '.join(fails)}", flush=True)
    for job in spec.get("jobs", []):
        if only:
            break
        r = await app_jobs.run_job(sessions, app_id, job)
        results.append({"caso": f"job:{job}", "proceso": "Aviso programado", "ok": bool(r["message"]), "fallas": [],
                        "turnos": [{"usuario": "(a su hora)", "asistente": r["message"] or "", "ms": 0, "pasos": 0,
                                    "herramientas": [json.dumps(r["entregas"])]}], "ms": 0})
    (out / "casos.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    ok = sum(r["ok"] for r in results)
    lines = [f"# Casos de {spec['app']} ({now:%d-%m-%Y %H:%M}, {settings.vllm_llm_model})", "",
             f"{ok} de {len(results)} pasan los chequeos automáticos.", ""]
    for r in results:
        lines.append(f"## {r['caso']} · {r['proceso']} · {'OK' if r['ok'] else 'MAL: ' + '; '.join(r['fallas'])}")
        for t in r["turnos"]:
            lines += ["", f"**Usuario:** {t['usuario']}", "", f"**Asistente** ({t['ms']} ms, {t['pasos']} pasos):",
                      "", t["asistente"], ""]
            lines += [f"- `{h}`" for h in t["herramientas"]]
        lines.append("")
    (out / "report.md").write_text("\n".join(lines))
    print(f"\n{ok}/{len(results)} OK. Reporte: {out}/report.md")


if __name__ == "__main__":
    asyncio.run(main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/cliente/casos/casos.yaml")))
