"""Juez del eval (docs/EVAL_LLM_PLAN.md, seccion 4): un LLM externo califica cada
conversacion con una rubrica de 1 a 5 (absoluto) o elige entre dos runs la mejor
conversacion del mismo escenario (pareado, con el orden al azar).

Uso: make eval-llm-juez RUN=scripts/eval/runs/<run>                  # absoluto -> juez.jsonl
     make eval-llm-juez RUN=<run A> ARGS="--pareado <run B>"          # -> pareado_<B>.json en A
El juez no tiene que ser el mismo modelo que el agente evaluado.
"""
import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

from openai import AsyncOpenAI

from app.conversation.workflow import load_workflow
from app.llm.prompt import render_workflow

from .simulador import opciones_llm

PROMPT_VERSION = "1"
DIMENSIONES = ["coherencia", "adherencia", "manejo", "naturalidad", "cierre"]

SYSTEM = """Sos un evaluador experto de agentes de voz telefónicos que hablan español rioplatense. Evaluás la actuación del AGENTE (un LLM) en una llamada con un CLIENTE simulado. El cliente no se evalúa.

Calificá de 1 (muy malo) a 5 (impecable) cada dimensión, con un motivo de una frase que cite la conversación. Sos exigente: un 5 es una llamada que un supervisor no corregiría en nada.

- coherencia: responde a lo que dijo el cliente, recuerda lo que ya sabe, no vuelve a preguntar lo respondido, no se contradice.
- adherencia: cumple las reglas del workflow y dice solo lo que está en la base de conocimiento. Listá en "alucinaciones" cada afirmación sobre el producto, el servicio, precios, fechas u opciones que no esté en la base de conocimiento, o cada dato del cliente que el agente dio por dicho sin que lo dijera.
- manejo: resuelve la objeción, la confusión, la hostilidad o la evasiva de esta persona como piden las reglas, sin discutir ni presionar y sin ceder lo que no puede ceder.
- naturalidad: suena a una persona de Córdoba hablando por teléfono, breve, con voseo, sin lenguaje de folleto ni de chat, sin muletillas repetidas.
- cierre: termina en el momento correcto (ni antes de tener lo necesario ni de más) con el cierre que corresponde a lo que pasó.

Contá también en "repreguntas" cuántas veces el agente volvió a pedir un dato que el cliente ya había dado.

Respondé solo con JSON, así:
{"coherencia": {"puntaje": 1, "motivo": ""}, "adherencia": {"puntaje": 1, "motivo": ""}, "manejo": {"puntaje": 1, "motivo": ""}, "naturalidad": {"puntaje": 1, "motivo": ""}, "cierre": {"puntaje": 1, "motivo": ""}, "alucinaciones": [], "repreguntas": 0, "resumen": "una frase con lo peor y lo mejor de la llamada"}"""

SYSTEM_PAREADO = """Sos un evaluador experto de agentes de voz telefónicos que hablan español rioplatense. Vas a ver dos llamadas, A y B, del mismo escenario (mismo workflow, misma persona del cliente) atendidas por dos agentes distintos. Elegí cuál agente conversó mejor, considerando en este orden: cumplir las reglas y no inventar, obtener los datos y cerrar bien, manejar a la persona, y sonar natural. Si son igual de buenas o igual de malas, empate.

Respondé solo con JSON: {"mejor": "A" | "B" | "empate", "motivo": "una o dos frases"}"""


def transcript(rec: dict) -> str:
    return "\n".join(f"{'AGENTE' if m['role'] == 'assistant' else 'CLIENTE'}: {m['text']}" for m in rec["mensajes"])


def contexto(rec: dict) -> str:
    wf = load_workflow(rec["agente"])
    esperado = rec.get("esperado") or {}
    return (f"WORKFLOW DEL AGENTE (YAML):\n{render_workflow(wf)}\n"
            f"PERSONA DEL CLIENTE: {rec.get('resumen', '')}\n"
            f"FICHA DEL CLIENTE (lo que realmente sabe; sirve para detectar datos inventados):\n"
            f"{json.dumps(rec.get('ficha') or {}, ensure_ascii=False, indent=1)}\n"
            f"RESULTADO ESPERADO: datos {json.dumps(esperado.get('fields') or {}, ensure_ascii=False)}; "
            f"cierre {esperado.get('outcome')}\n")


def cierre(rec: dict) -> str:
    c = rec.get("checks") or {}
    return (f"DATOS QUE EXTRAJO EL SISTEMA: {json.dumps(rec.get('fields') or {}, ensure_ascii=False)}\n"
            f"CIERRE REGISTRADO: {c.get('outcome')}  (terminó: {c.get('termino')})")


def parsear(content: str) -> dict:
    try:
        return json.loads(content)
    except ValueError:
        i, j = content.find("{"), content.rfind("}")
        return json.loads(content[i:j + 1]) if 0 <= i < j else {"error": content[:200]}


class Juez:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=120, max_retries=3)
        self.model = model
        self.extra = opciones_llm(base_url)

    async def _pedir(self, system: str, user: str) -> dict:
        r = await self.client.chat.completions.create(
            model=self.model, temperature=0.0, response_format={"type": "json_object"}, max_tokens=1000,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **self.extra)
        return parsear(r.choices[0].message.content or "")

    async def absoluto(self, rec: dict) -> dict:
        if not rec.get("mensajes"):
            return {"id": rec["id"], "error": "sin conversación"}
        out = await self._pedir(SYSTEM, f"{contexto(rec)}\nCONVERSACIÓN:\n{transcript(rec)}\n\n{cierre(rec)}")
        return {"id": rec["id"], "modelo": self.model, "prompt_version": PROMPT_VERSION, **out}

    async def pareado(self, a: dict, b: dict, rng: random.Random) -> dict:
        orden = rng.random() < 0.5      # True: A es el run A
        x, y = (a, b) if orden else (b, a)
        out = await self._pedir(SYSTEM_PAREADO, f"{contexto(a)}\nLLAMADA A:\n{transcript(x)}\n\n{cierre(x)}\n\n"
                                                f"LLAMADA B:\n{transcript(y)}\n\n{cierre(y)}")
        mejor = out.get("mejor", "empate")
        if mejor in ("A", "B") and not orden:
            mejor = "B" if mejor == "A" else "A"
        return {"id": a["id"], "grupo": a["grupo"], "persona": a["persona"], "mejor": mejor,
                "motivo": out.get("motivo", ""), "orden_mostrado": "AB" if orden else "BA"}


def leer(rundir: Path) -> list[dict]:
    return [json.loads(l) for l in (rundir / "conversaciones.jsonl").read_text().splitlines() if l.strip()]


async def juzgar_run(rundir: Path, base_url: str, api_key: str, model: str, paralelo: int = 8) -> None:
    """Califica las conversaciones que falten en juez.jsonl (se puede reanudar)."""
    juez = Juez(base_url, api_key, model)
    hechas = set()
    path = rundir / "juez.jsonl"
    if path.exists():
        hechas = {json.loads(l)["id"] for l in path.read_text().splitlines() if l.strip()}
    pendientes = [r for r in leer(rundir) if r["id"] not in hechas]
    print(f"juez {model}: {len(pendientes)} conversaciones ({len(hechas)} ya calificadas)")
    sem = asyncio.Semaphore(paralelo)

    async def una(rec):
        async with sem:
            try:
                return await juez.absoluto(rec)
            except Exception as e:  # noqa: BLE001
                return {"id": rec["id"], "error": f"{type(e).__name__}: {e}"}

    with open(path, "a", buffering=1) as out:
        for i, fut in enumerate(asyncio.as_completed([una(r) for r in pendientes]), 1):
            res = await fut
            out.write(json.dumps(res, ensure_ascii=False) + "\n")
            nota = res.get("error") or " ".join(f"{d[:3]} {res.get(d, {}).get('puntaje', '?')}" for d in DIMENSIONES)
            print(f"[{i:3}/{len(pendientes)}] {res['id']:38} {nota}")


async def pareado_runs(run_a: Path, run_b: Path, base_url: str, api_key: str, model: str, paralelo: int = 8) -> dict:
    juez = Juez(base_url, api_key, model)
    a = {r["id"]: r for r in leer(run_a)}
    b = {r["id"]: r for r in leer(run_b)}
    comunes = sorted(set(a) & set(b))
    print(f"pareado {model}: {len(comunes)} escenarios en común ({len(a)} en A, {len(b)} en B)")
    sem = asyncio.Semaphore(paralelo)
    rng = random.Random(f"{run_a.name}|{run_b.name}")

    async def uno(k):
        async with sem:
            try:
                return await juez.pareado(a[k], b[k], random.Random(f"{k}|{rng.random()}"))
            except Exception as e:  # noqa: BLE001
                return {"id": k, "grupo": a[k]["grupo"], "persona": a[k]["persona"], "mejor": "error", "motivo": str(e)}

    pares = [await f for f in asyncio.as_completed([uno(k) for k in comunes])]
    total = {"A": 0, "B": 0, "empate": 0, "error": 0}
    por_grupo: dict[str, dict] = {}
    for p in pares:
        total[p["mejor"]] = total.get(p["mejor"], 0) + 1
        g = por_grupo.setdefault(p["grupo"], {"A": 0, "B": 0, "empate": 0, "error": 0})
        g[p["mejor"]] = g.get(p["mejor"], 0) + 1
    res = {"A": str(run_a), "B": str(run_b), "juez": model, "prompt_version": PROMPT_VERSION,
           "total": total, "por_grupo": por_grupo, "pares": sorted(pares, key=lambda p: p["id"])}
    out = run_a / f"pareado_{run_b.name}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"A {total['A']}  B {total['B']}  empate {total['empate']}  -> {out}")
    for g, c in sorted(por_grupo.items()):
        print(f"  {g:16} A {c['A']:3}  B {c['B']:3}  empate {c['empate']:3}")
    return res


def main() -> None:
    from .run import EVAL_LLM_API_KEY, EVAL_LLM_BASE_URL, EVAL_LLM_MODEL
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="directorio del run")
    ap.add_argument("--pareado", default=None, help="otro run: elegir la mejor conversación de cada escenario")
    ap.add_argument("--base-url", default=EVAL_LLM_BASE_URL)
    ap.add_argument("--model", default=EVAL_LLM_MODEL)
    ap.add_argument("--paralelo", type=int, default=8)
    args = ap.parse_args()
    if not EVAL_LLM_API_KEY and "api." in args.base_url:
        sys.exit("falta EVAL_LLM_API_KEY en .env")
    from app import config
    key = EVAL_LLM_API_KEY or config.VLLM_API_KEY
    if args.pareado:
        asyncio.run(pareado_runs(Path(args.run), Path(args.pareado), args.base_url, key, args.model, args.paralelo))
    else:
        asyncio.run(juzgar_run(Path(args.run), args.base_url, key, args.model, args.paralelo))
        from . import analyze
        analyze.resumir(Path(args.run))


if __name__ == "__main__":
    main()
