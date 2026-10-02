"""Eval de calidad del LLM por tipo de agente y de cliente (docs/EVAL_LLM_PLAN.md).

Corre agentes x personas x repeticiones contra el motor conversacional por texto
(sin voz), con un cliente simulado por un LLM externo o por guion, y guarda cada
conversacion con sus metricas duras en scripts/eval/runs/<fecha>_<nombre>/.
Al terminar imprime el resumen (analyze.py) y, con --juez, califica con el juez.

Uso: make eval-llm ARGS="--reps 3"                        # todo, cliente simulado
     make eval-llm ARGS="--humo"                           # 1 cooperativo por agente
     make eval-llm ARGS="--cliente guion"                  # sin API externa
     make eval-llm ARGS="--agentes cobranza,datos --engine structured"
     make eval-llm ARGS="--llm-base-url https://api.deepseek.com/v1 --llm-model deepseek-chat --llm-api-key-env EVAL_LLM_API_KEY"
"""
import argparse
import asyncio
import datetime
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

from app import config
from app.conversation.engine import ConversationEngine
from app.conversation.store import ConversationStore
from app.agents.templates import load_reference, reference_data
from app.llm.client import LLMClient

from . import analyze, canal as canal_mod, checks
from .escenarios import FALLBACK_GUION, Escenario, escenarios, grupos_disponibles
from .simulador import PROMPT_VERSION, Guion, Simulador, es_local

RUNS_DIR = Path(__file__).resolve().parent / "runs"

# Simulador y juez: un LLM externo OpenAI-compatible. Default DeepSeek directo;
# con OpenRouter, EVAL_LLM_BASE_URL=https://openrouter.ai/api/v1 y el modelo con
# prefijo de proveedor (deepseek/deepseek-v3.2, ...).
EVAL_LLM_BASE_URL = os.getenv("EVAL_LLM_BASE_URL", "https://api.deepseek.com/v1")
EVAL_LLM_API_KEY = os.getenv("EVAL_LLM_API_KEY", "")
EVAL_LLM_MODEL = os.getenv("EVAL_LLM_MODEL", "deepseek-chat")


def llm_agente(args) -> tuple[LLMClient, dict]:
    base = args.llm_base_url or config.VLLM_LLM_BASE_URL
    model = args.llm_model or config.VLLM_LLM_MODEL
    key = os.getenv(args.llm_api_key_env, "") if args.llm_api_key_env else config.VLLM_API_KEY
    client = LLMClient(base, key, model)
    if args.llm_base_url:
        # API externa: sin top_k, min_p ni chat_template_kwargs, que son de vLLM.
        client.options = {k: v for k, v in client.options.items() if k in ("temperature", "top_p")}
    ficha = {"base_url": base, "model": model, "thinking": config.LLM_THINKING and not args.llm_base_url,
             "thinking_budget": config.LLM_THINKING_BUDGET, "temperature": client.options.get("temperature"),
             "externo": bool(args.llm_base_url)}
    return client, ficha


def git_rev() -> str:
    if os.getenv("GIT_REV"):        # el contenedor no tiene .git: lo pasa el Makefile
        return os.environ["GIT_REV"]
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return ""


def workflows_hash(escs: list[Escenario]) -> dict:
    out = {}
    for agente in sorted({e.agente for e in escs}):
        try:
            data = json.dumps(reference_data(agente), ensure_ascii=False, sort_keys=True)
        except KeyError:
            data = ""
        out[agente] = hashlib.sha1(data.encode()).hexdigest()[:8] if data else ""
    return out


async def conversar(engine: ConversationEngine, esc: Escenario, cliente, canal, sem: asyncio.Semaphore) -> dict:
    rng = random.Random(f"{esc.id}|canal")
    async with sem:
        t0 = time.time()
        error, cid, historial, dicho, wall = None, None, [], [], []
        try:
            state, opening = engine.start_conversation(esc.agente)
            cid = state.conversation_id
            historial.append(("agente", opening))
            completed = False
            for _ in range(esc.turnos_max):
                dice, corta = await cliente.responder(esc, historial)
                if not dice:
                    break
                partes = await canal.aplicar(dice, rng)
                dicho.append({"dice": dice, "llega": partes, "corta": corta})
                for parte in partes:
                    t = time.perf_counter()
                    state, turn = await engine.process_turn(cid, parte)
                    wall.append(round(time.perf_counter() - t, 3))
                    historial += [("usuario", parte), ("agente", turn.assistant_message)]
                    if turn.status == "completed":
                        completed = True
                        break
                if completed or corta:
                    break
            await engine.finish(cid)
            await engine.wait_extraction(cid)
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
        state = engine.store.get(cid) if cid else None
        mensajes = [m.model_dump() for m in state.messages] if state else []
        fields = {k: v for k, v in (state.fields if state else {}).items() if v is not None}
        outcome = state.progress.outcome if state else None
        status = state.status if state else "error"
        return {
            "id": esc.id, "grupo": esc.grupo, "agente": esc.agente, "persona": esc.persona, "rep": esc.rep,
            "resumen": esc.resumen, "cliente": cliente.nombre, "canal": canal.nombre,
            "ficha": esc.ficha, "esperado": esc.esperado, "turnos_max": esc.turnos_max,
            "mensajes": mensajes, "dicho": dicho if canal.nombre != "texto" else [],
            "fields": fields, "status": status, "outcome": outcome, "error": error,
            "duracion_s": round(time.time() - t0, 1), "turno_wall_s": wall,
            "checks": checks.evaluar(esc, fields, outcome, status, mensajes, error),
        }


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agentes", default=",".join(grupos_disponibles()),
                    help="grupos de personas (scripts/eval/personas/*.yml), separados por coma")
    ap.add_argument("--personas", default="", help="solo estas personas, separadas por coma")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1, help="semilla de las fichas y del canal")
    ap.add_argument("--cliente", choices=["simulado", "guion"], default="simulado")
    ap.add_argument("--canal", default="texto", help="texto, stt-sim, tts-stt[:tel8k_noise|tel8k_cuts]")
    ap.add_argument("--canal-voz", default="martin", help="voz del TTS para el canal tts-stt")
    ap.add_argument("--engine", choices=["classic", "structured"], default=None,
                    help="structured usa <agente>_structured; default: el del archivo de personas (classic)")
    ap.add_argument("--turnos-max", type=int, default=None)
    ap.add_argument("--paralelo", type=int, default=12, help="conversaciones a la vez")
    ap.add_argument("--llm-base-url", default=None, help="LLM del agente (default: VLLM_LLM_BASE_URL)")
    ap.add_argument("--llm-model", default=None)
    ap.add_argument("--llm-api-key-env", default=None, help="variable de entorno con la clave del LLM externo")
    ap.add_argument("--sim-base-url", default=EVAL_LLM_BASE_URL)
    ap.add_argument("--sim-model", default=EVAL_LLM_MODEL)
    ap.add_argument("--sim-temperature", type=float, default=0.7)
    ap.add_argument("--juez", action="store_true", help="calificar con el juez al terminar (juez.py)")
    ap.add_argument("--humo", action="store_true", help="1 repeticion de la persona cooperativo de cada agente")
    ap.add_argument("--lista", action="store_true", help="listar los escenarios y salir")
    ap.add_argument("--nombre", default="", help="nombre del run (default: el modelo)")
    ap.add_argument("--notas", default="")
    args = ap.parse_args()

    if args.humo:
        args.reps, args.personas = 1, "cooperativo"
    escs = escenarios(args.agentes.split(","), args.reps, args.seed,
                      [p for p in args.personas.split(",") if p] or None, args.engine, args.turnos_max)
    if args.cliente == "guion":
        sin = [e.id for e in escs if not e.guion]
        if sin:
            print(f"sin guion (se saltean): {', '.join(sorted({s.rsplit('/', 1)[0] for s in sin}))}", file=sys.stderr)
        escs = [e for e in escs if e.guion]
    if args.lista:
        for e in escs:
            print(f"{e.id:40} {e.agente:28} {'guion' if e.guion else '':6} {e.resumen}")
        print(f"{len(escs)} escenarios")
        return
    if not escs:
        sys.exit("no hay escenarios")
    for e in escs:
        load_reference(e.agente)     # falla temprano si falta una plantilla

    llm, ficha_llm = llm_agente(args)
    engine = ConversationEngine(llm, ConversationStore.for_dsn("sqlite://"))
    simulador = None
    if args.cliente == "simulado" and any(not e.solo_guion for e in escs):
        if not EVAL_LLM_API_KEY and not es_local(args.sim_base_url):
            sys.exit("falta EVAL_LLM_API_KEY en .env (o --cliente guion)")
        simulador = Simulador(args.sim_base_url, EVAL_LLM_API_KEY or config.VLLM_API_KEY, args.sim_model, args.sim_temperature)
    canal = canal_mod.crear(args.canal, voz=args.canal_voz)

    def cliente_para(esc: Escenario):
        if args.cliente == "guion" or esc.solo_guion or simulador is None:
            return Guion(esc.guion or [], FALLBACK_GUION)
        return simulador

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rundir = RUNS_DIR / f"{ts}_{slug(args.nombre or ficha_llm['model'].split('/')[-1])}"
    rundir.mkdir(parents=True)
    run = {
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"), "git": git_rev(), "notas": args.notas,
        "agente_llm": ficha_llm, "engine": args.engine or "classic",
        "simulador": {"base_url": args.sim_base_url, "model": args.sim_model, "temperature": args.sim_temperature,
                      "prompt_version": PROMPT_VERSION} if simulador else None,
        "cliente": args.cliente, "canal": args.canal, "seed": args.seed, "reps": args.reps,
        "grupos": args.agentes.split(","), "personas": args.personas or "todas",
        "workflows": workflows_hash(escs), "escenarios": len(escs), "paralelo": args.paralelo,
    }
    (rundir / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2))
    print(f"run: {rundir}\nagente: {ficha_llm['model']} @ {ficha_llm['base_url']}  |  "
          f"cliente: {args.cliente}{' (' + args.sim_model + ')' if simulador else ''}  |  canal: {args.canal}  |  "
          f"{len(escs)} conversaciones, {args.paralelo} a la vez")

    asyncio.run(correr(engine, escs, cliente_para, canal, args.paralelo, rundir))
    analyze.resumir(rundir)
    if args.juez:
        from . import juez
        asyncio.run(juez.juzgar_run(rundir, args.sim_base_url, EVAL_LLM_API_KEY or config.VLLM_API_KEY, args.sim_model,
                                    paralelo=min(args.paralelo, 8)))
        analyze.resumir(rundir)


async def correr(engine, escs, cliente_para, canal, paralelo, rundir: Path) -> None:
    sem = asyncio.Semaphore(paralelo)
    t0 = time.time()
    tareas = [asyncio.create_task(conversar(engine, e, cliente_para(e), canal, sem)) for e in escs]
    with open(rundir / "conversaciones.jsonl", "a", buffering=1) as out:
        for i, fut in enumerate(asyncio.as_completed(tareas), 1):
            rec = await fut
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            c = rec["checks"]
            estado = rec["error"] or (f"{c['outcome']}{'' if c['outcome_ok'] else ' (esperado ' + '/'.join(rec['esperado'].get('outcome') or []) + ')'}"
                                      f"  datos {c['datos_ok']}/{len(c['datos'])}  reglas {c['reglas_n']}")
            print(f"[{i:3}/{len(escs)}] {time.time() - t0:5.0f}s  {rec['id']:38} {c['turnos']:2} turnos  {estado}")


if __name__ == "__main__":
    main()
