"""Escenarios de llamada contra el motor y el LLM real, para ver en qué falla el agente.

El cliente simulado contesta según lo que le preguntan (next_objective): cada escenario
tiene una lista de respuestas por objetivo, que se usan en orden si se repregunta ("*"
para cualquier otro). Salen de llamadas reales (2026-09-23).

Por corrida imprime el resultado, los turnos y dos señales de loop: respuestas iguales
a la anterior y el mayor número de turnos seguidos pidiendo el mismo objetivo.

Uso: make eval-motor [N=3] [S=escenario]
"""
import asyncio
import statistics
import sys
import time

from app import config
from app.conversation.engine import ConversationEngine
from app.conversation.store import ConversationStore
from app.conversation.workflow import load_workflow
from app.llm.client import LLMClient

SCENARIOS = {
    # 48d528e6: pregunta y duda; terminó cerrando como "sin interés".
    "pregunta-y-duda": ("demo_booking", {
        "wants_pitch": ["sí, por favor."],
        "company_context": ["Yo tengo una concesionaria de autos, tengo treinta empleados y desconozco si llegan a horario. ¿Me podrías comentar un poco más?"],
        "demo_answer": ["No sé todavía. Quisiera saber un poco más de Browix.", "¿Qué es Browix?"],
        "callback_wanted": ["¿Qué es Browix?", "Sí, llamame la semana que viene."],
        "*": ["¿Cómo?"],
    }),
    # caec030a: pide que le expliquen antes de decidir; terminó cerrando.
    "explicame-antes": ("demo_booking", {
        "wants_pitch": ["sí"],
        "company_context": ["Somos una empresa que fabrica hornos de cocina. Tenemos cien empleados, algunos van a domicilio y otros a la oficina."],
        "demo_answer": ["¿Me podrías explicar de qué manera Browix podría solucionar mi problema?", "Ah, bueno, sí, agendemos."],
        "contact_name": ["Soy Laureano, escribime a laureano arroba gmail punto com."],
        "contact": ["laureano arroba gmail punto com"],
        "*": ["¿Cómo?"],
    }),
    # 0337ad60: dijo que sí a la demo con un "pero"; quedó como "volver a llamar".
    "si-pero": ("demo_booking", {
        "wants_pitch": ["sí, pero tengo muy poco tiempo."],
        "company_context": ["Somos una empresa que fabrica hornos de cocina y estamos buscando un software."],
        "demo_answer": ["Sí, pero antes me gustaría que me cuentes un poco más.", "Dale, sí."],
        "contact_name": ["Laureano."],
        "contact": ["Mi teléfono es tres cinco uno, cinco cinco cinco, uno dos tres cuatro."],
        "*": ["¿Cómo?"],
    }),
    # 2d0c771b: el VAD corta el dictado del email.
    "email-cortado": ("demo_booking", {
        "wants_pitch": ["Dale, contame."],
        "company_context": ["Somos una empresa de seguridad y nos cuesta saber si los vigiladores llegan a horario."],
        "demo_answer": ["Sí, me interesa."],
        "contact_name": ["Martín."],
        "contact": ["Escribime a", "martin arroba segurisur punto com"],
        "*": ["¿Cómo?"],
    }),
    "rechaza": ("demo_booking", {"wants_pitch": ["No, gracias, ahora no puedo."], "*": ["No, gracias."]}),
    # 7947fe59: atendió el buzón de voz.
    "buzon-de-voz": ("demo_booking", {"*": [
        "Bienvenido al buzón de voz claro tres cinco dos cinco cinco cero tres seis uno dos",
        "Después del tono, deja tu mensaje.",
        "Para finalizar, corta o marca la tecla numeral para más opciones.",
        "Si estás conforme con el mensaje, marca uno. Para revisar el mensaje, marca dos.",
    ]}),
}


def engine_fields(workflow_id):
    return sorted(load_workflow(workflow_id).fields, key=lambda f: load_workflow(workflow_id).fields[f].priority)


async def run(engine, workflow_id, answers, max_turns=12):
    state, opening = engine.start_conversation(workflow_id)
    # La apertura pregunta por el primer dato del workflow.
    log, used, objective = [f"A: {opening}"], {}, next(iter(engine_fields(workflow_id)))
    repeats = streak = max_streak = 0
    times = []
    last_message, last_objective = opening, None
    for _ in range(max_turns):
        options = answers.get(objective) or answers["*"]
        key = objective if objective in answers else "*"
        msg = options[min(used.get(key, 0), len(options) - 1)]
        used[key] = used.get(key, 0) + 1
        started = time.perf_counter()
        before = dict(state.fields)
        state, turn = await engine.process_turn(state.conversation_id, msg)
        times.append(time.perf_counter() - started)
        await engine.wait_extraction(state.conversation_id)
        state = engine.store.get(state.conversation_id)
        updates = {k: v for k, v in state.fields.items() if v != before.get(k)}
        log += [f"U: {msg}", f"A: {turn.assistant_message}   {updates or ''} -> {turn.next_objective}"]
        repeats += turn.assistant_message.strip() == last_message.strip()
        streak = streak + 1 if turn.next_objective and turn.next_objective == last_objective else 0
        max_streak = max(max_streak, streak)
        last_message, last_objective, objective = turn.assistant_message, turn.next_objective, turn.next_objective
        if turn.status == "completed":
            break
    return state, log, repeats, max_streak, times


async def main(n: int, only: str | None):
    engine = ConversationEngine(LLMClient(config.VLLM_LLM_BASE_URL, config.VLLM_API_KEY, config.VLLM_LLM_MODEL),
                                ConversationStore("sqlite://"))
    all_times = []
    for name, (workflow_id, answers) in SCENARIOS.items():
        if only and name != only:
            continue
        for i in range(n):
            state, log, repeats, streak, times = await run(engine, workflow_id, answers)
            all_times.extend(times)
            turns = (len(log) - 1) // 2
            known = {k: v for k, v in state.fields.items() if v is not None}
            print(f"\n=== {name} #{i + 1}: {state.progress.outcome or 'sin terminar'}, {turns} turnos, "
                  f"repetidas {repeats}, mismo objetivo seguido {streak}")
            print("\n".join(log))
            print(f"datos: {known}")
    if all_times:
        print(f"\nLLM por turno: p50 {statistics.median(all_times):.2f}s, p90 "
              f"{statistics.quantiles(all_times, n=10)[-1]:.2f}s, max {max(all_times):.2f}s ({len(all_times)} turnos)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    asyncio.run(main(int(args[0]) if args else 1, args[1] if len(args) > 1 else None))
