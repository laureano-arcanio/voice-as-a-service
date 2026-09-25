"""Llamadas reales de berlin_signup, con lo que dijo el cliente tal cual, contra
el motor y el LLM real. A diferencia de replay_calls.py, el cliente no contesta
segun lo que le preguntan: repite la llamada. Por corrida compara los datos
finales con los esperados y cuenta las repreguntas (veces que el agente vuelve a
pedir un dato que ya pidio y el cliente contesto).
Uso: make eval-llamadas [N=5] [S=escenario] [W=workflow] (W: berlin_signup o
berlin_signup_classic, el mismo agente con el motor clasico)
"""
import asyncio
import collections
import sys
import unicodedata

from app import config
from app.conversation.engine import ConversationEngine
from app.conversation.store import ConversationStore
from app.conversation.workflow import load_workflow
from app.llm.client import LLMClient

# Esperado por campo: texto = el valor lo contiene (sin tildes ni mayusculas);
# True/False = igual; None = sin dato (no hay que inventarlo). Los campos que
# dependen de que pregunta conteste el cliente en la repeticion no se evaluan.
# outcome: los resultados aceptables.
SCENARIOS = {
    # 80ac0e22: el STT cambia running por rolling/pruning; elige calistenia; corta antes del contacto.
    "80ac0e22": {
        "messages": ["sí, por favor.", "Mm, a mi me interesa mucho hacer uh uh rolling", "Me gustaría hacer pruning.",
                     "sí, me gustaría probar la calisteña.", "Yo estoy en Córdoba capital.",
                     "sí, tengo en mente hacer calisteña, ya te dije antes.",
                     "sí, yo vivo en capital y me gustaría que me quede cerca de mi casa.", "sí, por favor.",
                     "no, quisiera terminar la conversación."],
        "expected": {"wants_pitch": True, "activity": "calist", "zone": "capital", "wants_link": True,
                     "contact": None, "contact_name": None},
        "outcome": ("incompleta",),
    },
    # 4a89e965: llamada normal; "Sí, pasame el link" no se guardaba y lo volvia a preguntar.
    "4a89e965": {
        "messages": ["Hola Sofía. sí, decime.", "tela", "teľa", "Funcional en Nueva Córdoba.", "Sí, pasame el link.",
                     "Por favor.", "sí, por WhatsApp, por favor.", "Nahuel.", "sí, por favor."],
        "expected": {"wants_pitch": True, "activity": "funcional", "zone": "nueva cordoba", "wants_link": True,
                     "same_number": True, "contact": None, "contact_name": "nahuel"},
        "outcome": ("link",),
    },
    # 704b5d42: cliente dificil; nunca elige actividad; Villa Belgrano llega como "Villa de grano".
    "704b5d42": {
        "messages": ["Hola Sofía, ¿qué carajo es Berlín City Club?",
                     "sí, ¿cuánto sale en cada una de las clases individuales? Porque eso es lo único que me importa.",
                     "No, pero si no me decís antes cuál es el precio, yo no voy a abrirme una cuenta en la",
                     "Fijate vos el precio de una de esas clases y decime.", "¿Qué sedes tienen en Berlín Field Club?",
                     "Está a Sports Club de Gauss en Berlin Field Club.", "Cerca de mi trabajo.",
                     "no, primero quiero saber si Sports Club está In that",
                     "sí quisiera saber alguna que esté cerca del Sport Club en Gauss. Villa de grano.",
                     "sí, envíamelo.", "Pito"],
        "expected": {"wants_pitch": True, "activity": None, "zone": "grano", "wants_link": True,
                     "contact": None, "contact_name": "pito"},
        "outcome": ("incompleta", "sin terminar"),   # nunca eligio actividad: no es link
    },
}


def plain(text) -> str:
    return unicodedata.normalize("NFKD", str(text).lower()).encode("ascii", "ignore").decode()


def check(expected, value) -> str:
    """ok, falta (no guardo un dato dicho) o mal (dato equivocado o inventado)."""
    if expected is None:
        return "ok" if value is None else "mal"
    if value is None:
        return "falta"
    if isinstance(expected, bool):
        return "ok" if value is expected else "mal"
    return "ok" if expected in plain(value) else "mal"


async def run(engine, scenario, workflow_id):
    state, _ = engine.start_conversation(workflow_id)
    cid = state.conversation_id
    asks = collections.Counter({"wants_pitch": 1})   # la apertura pregunta el primero
    log = []
    for msg in scenario["messages"]:
        _, turn = await engine.process_turn(cid, msg)
        if hasattr(engine, "wait_extraction"):
            await engine.wait_extraction(cid)
        if turn.next_objective:
            asks[turn.next_objective] += 1
        log += [f"U: {msg}", f"A: {turn.assistant_message}  -> {turn.next_objective}"]
        if turn.status == "completed":
            break
    await engine.finish(cid)     # como al cortar la llamada: en el clasico, la extraccion final
    state = engine.store.get(cid)
    # El clasico no declara que pregunta: las repreguntas no se pueden contar.
    classic = load_workflow(workflow_id).engine == "classic"
    return state, log, None if classic else sum(n - 1 for n in asks.values() if n > 1)


async def main(n: int, only: str | None, verbose: bool, workflow_id: str):
    engine = ConversationEngine(LLMClient(config.VLLM_LLM_BASE_URL, config.VLLM_API_KEY, config.VLLM_LLM_MODEL),
                                ConversationStore("sqlite://"))
    total = collections.Counter()
    for name, scenario in SCENARIOS.items():
        if only and name != only:
            continue
        per_field = collections.defaultdict(collections.Counter)
        outcomes, reasks = collections.Counter(), []
        for _ in range(n):
            state, log, reask = await run(engine, scenario, workflow_id)
            for field, expected in scenario["expected"].items():
                result = check(expected, state.fields.get(field))
                per_field[field][result] += 1
                total[result] += 1
            outcome = state.progress.outcome or "sin terminar"
            outcomes[outcome] += 1
            total["outcome_ok"] += outcome in scenario["outcome"]
            total["runs"] += 1
            total["repreguntas"] += reask or 0
            reasks.append(reask)
            if verbose:
                print("\n".join(log), f"\ndatos: { {k: v for k, v in state.fields.items() if v is not None} }\n")
        print(f"=== {name} ({n} corridas) resultado: {dict(outcomes)} (esperado {' o '.join(scenario['outcome'])}), "
              f"repreguntas por corrida: {reasks}")
        for field, counts in per_field.items():
            print(f"  {field:13} {dict(counts)}")
    fields = total["ok"] + total["falta"] + total["mal"]
    print(f"\nTOTAL: datos ok {total['ok']}/{fields}, faltan {total['falta']}, mal {total['mal']}; "
          f"resultado correcto {total['outcome_ok']}/{total['runs']}; repreguntas {total['repreguntas']}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    verbose = "-v" in args
    workflow = next((a.removeprefix("-w=") for a in args if a.startswith("-w=")), "berlin_signup")
    args = [a for a in args if a != "-v" and not a.startswith("-w=")]
    asyncio.run(main(int(args[0]) if args else 1, args[1] if len(args) > 1 else None, verbose, workflow))
