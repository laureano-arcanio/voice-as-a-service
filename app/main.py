import datetime
import re

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import config, livekit_dispatch, voices
from .calls import CallLog
from .conversation.engine import ConversationEngine
from .conversation.models import ConversationState, Progress
from .conversation.workflow import INCOMPLETE, is_required, load_workflow, outcome_for, workflow_ids
from .deps import get_calls, get_engine

app = FastAPI(title="Voice agent")
templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "static")), name="static")


class StartRequest(BaseModel):
    workflow_id: str = config.WORKFLOW_ID


class TurnRequest(BaseModel):
    message: str


class CallRequest(BaseModel):
    workflow_id: str = config.WORKFLOW_ID
    phone: str | None = None
    # Voz del TTS para esta llamada; sin voz, la del workflow (agent.voice).
    voice: str | None = None
    # Llamada del loadtest (scripts/loadtest/): como la de prueba, pero el agente
    # no corta al completar el workflow, asi dura los turnos que pide el caller.
    loadtest: bool = False


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/conversations")
def start_conversation(req: StartRequest, engine: ConversationEngine = Depends(get_engine)):
    try:
        state, message = engine.start_conversation(req.workflow_id)
    except KeyError:
        raise HTTPException(404, "Workflow inexistente")
    return {"conversation_id": state.conversation_id, "message": message, "state": state}


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, engine: ConversationEngine = Depends(get_engine)):
    state = engine.store.get(conversation_id)
    if state is None:
        raise HTTPException(404)
    return state


@app.post("/conversations/{conversation_id}/turn")
async def turn(conversation_id: str, req: TurnRequest, engine: ConversationEngine = Depends(get_engine)):
    try:
        _, result = await engine.process_turn(conversation_id, req.message)
    except KeyError:
        raise HTTPException(404)
    # Por la API no hay audio que tape la extraccion: se espera y se devuelve el estado con los datos.
    await engine.wait_extraction(conversation_id)
    state = engine.store.get(conversation_id)
    return {"message": result.assistant_message, "state": state, "next_objective": result.next_objective, "status": result.status}


@app.post("/calls")
async def start_call(req: CallRequest, engine: ConversationEngine = Depends(get_engine),
                     calls: CallLog = Depends(get_calls)):
    phone = None
    if req.phone:
        phone = re.sub(r"[\s()\-.]", "", req.phone)
        if not re.fullmatch(r"\+\d{8,15}", phone):
            raise HTTPException(422, "Número inválido: usar formato internacional, ej. +5491155551234")
        if req.loadtest:
            raise HTTPException(422, "El loadtest no marca teléfonos")
    voice = req.voice.strip().lower() if req.voice else None
    if voice and voice not in voices.catalog():
        raise HTTPException(422, f"Voz inexistente: {voice}")
    try:
        state, _ = engine.start_conversation(req.workflow_id)
    except KeyError:
        raise HTTPException(404, "Workflow inexistente")
    room = f"call-{state.conversation_id}"
    mode = "saliente" if phone else "loadtest" if req.loadtest else "prueba"
    calls.create(state.conversation_id, mode, phone)
    try:
        await livekit_dispatch.dispatch_call(room, state.conversation_id, phone, voice, req.loadtest)
    except Exception as e:
        calls.update(state.conversation_id, status="fallida", error=str(e)[:2000], ended_reason="dispatch_failed")
        raise HTTPException(502, f"No se pudo iniciar la llamada: {e}")
    result = {"conversation_id": state.conversation_id, "room": room}
    if phone is None:
        result["join_url"] = livekit_dispatch.build_test_join_url(room)
    return result


# ---------- dashboard ----------

@app.get("/")
def page_dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/calls/{conversation_id}")
def page_call(request: Request, conversation_id: str):
    return templates.TemplateResponse(request, "call.html", {"conversation_id": conversation_id})


@app.get("/workflow")
def page_workflow(request: Request):
    return templates.TemplateResponse(request, "workflow.html")


def _iso(dt: datetime.datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _outcome(workflow, conv):
    """Resultado de una conversacion completa (el guardado, o calculado si es anterior a outcomes)."""
    if workflow is None or conv.status != "completed":
        return None
    progress = conv.progress if isinstance(conv.progress, Progress) else Progress.model_validate(conv.progress or {})
    saved = progress.outcome
    outcome = next((o for o in [*workflow.completion.outcomes, INCOMPLETE] if o.id == saved), None)
    if outcome is None:
        # conv es la fila de la base (id) o un ConversationState (conversation_id), segun quien llama.
        conv_id = conv.conversation_id if isinstance(conv, ConversationState) else conv.id
        outcome = outcome_for(workflow, ConversationState(conversation_id=conv_id, workflow_id=conv.workflow_id,
                                                          fields=conv.fields, progress=Progress()))
    return outcome


def _summary(conv, call) -> dict:
    """Fila del dashboard: conversacion + llamada (si la hubo)."""
    try:
        workflow = load_workflow(conv.workflow_id)
        required = [n for n, spec in workflow.fields.items() if is_required(spec, conv.fields)]
    except KeyError:
        workflow, required = None, list(conv.fields)
    f = conv.fields
    outcome = _outcome(workflow, conv)
    lat = (call.latency or {}).get("stats", {}).get("total") if call else None
    return {
        "id": conv.id, "workflow_id": conv.workflow_id, "workflow_status": conv.status,
        "created_at": _iso(conv.created_at),
        "contact_name": f.get("contact_name"),
        "company": f.get("company_name") or f.get("company_context"),
        "outcome": outcome.label if outcome else None, "goal": bool(outcome and outcome.goal),
        "captured": sum(f.get(n) is not None for n in required), "required": len(required),
        "mode": call.mode if call else "api", "phone": call.phone if call else None,
        "status": call.status if call else None,
        "duration_seconds": call.duration_seconds if call else 0,
        "ended_reason": call.ended_reason if call else "",
        "latency_avg": lat["avg"] if lat else None,
    }


@app.get("/api/calls")
def list_calls(limit: int = 200, calls: CallLog = Depends(get_calls)):
    return [_summary(conv, call) for conv, call in calls.list(limit=limit)]


@app.get("/api/calls/{conversation_id}")
def get_call(conversation_id: str, engine: ConversationEngine = Depends(get_engine),
             calls: CallLog = Depends(get_calls)):
    state = engine.store.get(conversation_id)
    if state is None:
        raise HTTPException(404)
    call = calls.get(conversation_id)
    try:
        workflow = load_workflow(state.workflow_id)
        specs = sorted(workflow.fields.items(), key=lambda kv: kv[1].priority)
        fields = [{"name": n, "description": spec.description.strip(), "value": state.fields.get(n),
                   "required": is_required(spec, state.fields)} for n, spec in specs]
    except KeyError:
        workflow = None
        fields = [{"name": n, "description": n, "value": v, "required": True} for n, v in state.fields.items()]
    outcome = _outcome(workflow, state)
    for f in fields:
        f["rejected"] = state.progress.rejected.get(f["name"])
    return {
        "id": state.conversation_id, "workflow_id": state.workflow_id,
        "created_at": _iso(calls.created_at(conversation_id)),
        "workflow_status": state.status, "fields": fields,
        "outcome": None if outcome is None else {"label": outcome.label, "goal": outcome.goal},
        "messages": [m.model_dump() for m in state.messages],
        "call": None if call is None else {
            "mode": call.mode, "phone": call.phone, "status": call.status,
            "ended_reason": call.ended_reason, "error": call.error,
            "duration_seconds": call.duration_seconds, "latency": call.latency,
            "created_at": _iso(call.created_at), "started_at": _iso(call.started_at),
        },
    }


@app.get("/api/stats")
def stats(calls: CallLog = Depends(get_calls)):
    rows = [_summary(conv, call) for conv, call in calls.list()]
    phone_calls = [r for r in rows if r["mode"] != "api"]
    done = [r for r in phone_calls if r["status"] == "finalizada"]
    completed = [r for r in rows if r["workflow_status"] == "completed"]
    goal = [r for r in rows if r["goal"]]
    latencies = [r["latency_avg"] for r in done if r["latency_avg"] is not None]
    pct = lambda n, d: round(100 * n / d, 1) if d else 0
    return {
        "total": len(rows), "calls": len(phone_calls), "finished": len(done),
        "failed": sum(r["status"] == "fallida" for r in phone_calls),
        "completed": len(completed), "completed_pct": pct(len(completed), len(rows)),
        "goal": len(goal), "goal_pct": pct(len(goal), len(rows)),
        "total_minutes": round(sum(r["duration_seconds"] for r in done) / 60, 1),
        "avg_duration": round(sum(r["duration_seconds"] for r in done) / len(done)) if done else 0,
        "latency_avg": round(sum(latencies) / len(latencies), 2) if latencies else None,
    }


@app.get("/api/chart")
def chart(date_from: datetime.date, date_to: datetime.date, calls: CallLog = Depends(get_calls)):
    """Conversaciones por dia + % con workflow completo y % que cumplen el objetivo."""
    since = datetime.datetime.combine(date_from, datetime.time())
    days = [date_from + datetime.timedelta(d) for d in range((date_to - date_from).days + 1)]
    buckets = {d: [] for d in days}
    for conv, call in calls.list(since=since):
        day = conv.created_at.date()
        if day in buckets:
            buckets[day].append(_summary(conv, call))
    pct = lambda rows, key: round(100 * sum(key(r) for r in rows) / len(rows), 1) if rows else None
    return {
        "labels": [d.isoformat() for d in days],
        "totals": [len(buckets[d]) for d in days],
        "completed_pct": [pct(buckets[d], lambda r: r["workflow_status"] == "completed") for d in days],
        "goal_pct": [pct(buckets[d], lambda r: r["goal"]) for d in days],
    }


@app.get("/api/workflows")
def list_workflows():
    """Para elegir con que agente llamar: el default (WORKFLOW_ID) primero."""
    workflows = [load_workflow(w) for w in workflow_ids()]
    workflows.sort(key=lambda w: w.id != config.WORKFLOW_ID)
    return [{"id": w.id, "engine": w.engine, "agent": f"{w.agent.name}, {w.agent.role}", "voice": w.agent.voice}
            for w in workflows]


@app.get("/api/voices")
def list_voices(genero: str | None = None, wer_max: float | None = None,
                car_min: float | None = None, car_max: float | None = None):
    """Voces del TTS con sus metricas (tts/finetune/voces.tsv), filtradas; de menor a mayor WER."""
    return voices.search(genero or None, wer_max, car_min, car_max)


@app.get("/api/workflow")
def workflow_definition(workflow_id: str = config.WORKFLOW_ID):
    try:
        return load_workflow(workflow_id)
    except KeyError:
        raise HTTPException(404, "Workflow inexistente")
