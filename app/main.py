import datetime
import re

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import config, livekit_dispatch
from .calls import CallLog
from .conversation.engine import ConversationEngine
from .conversation.workflow import is_required, load_workflow
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
        state, result = await engine.process_turn(conversation_id, req.message)
    except KeyError:
        raise HTTPException(404)
    return {"message": result.assistant_message, "state": state, "next_objective": result.next_objective, "status": result.status}


@app.post("/calls")
async def start_call(req: CallRequest, engine: ConversationEngine = Depends(get_engine),
                     calls: CallLog = Depends(get_calls)):
    phone = None
    if req.phone:
        phone = re.sub(r"[\s()\-.]", "", req.phone)
        if not re.fullmatch(r"\+\d{8,15}", phone):
            raise HTTPException(422, "Número inválido: usar formato internacional, ej. +5491155551234")
    try:
        state, _ = engine.start_conversation(req.workflow_id)
    except KeyError:
        raise HTTPException(404, "Workflow inexistente")
    room = f"call-{state.conversation_id}"
    calls.create(state.conversation_id, "saliente" if phone else "prueba", phone)
    try:
        await livekit_dispatch.dispatch_call(room, state.conversation_id, phone)
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


def _summary(conv, call) -> dict:
    """Fila del dashboard: conversacion + llamada (si la hubo)."""
    try:
        workflow = load_workflow(conv.workflow_id)
        required = [n for n, spec in workflow.fields.items() if is_required(spec, conv.fields)]
    except KeyError:
        required = list(conv.fields)
    f = conv.fields
    lat = (call.latency or {}).get("stats", {}).get("total") if call else None
    return {
        "id": conv.id, "workflow_id": conv.workflow_id, "workflow_status": conv.status,
        "created_at": _iso(conv.created_at),
        "contact_name": f.get("contact_name"), "company_name": f.get("company_name"),
        "wants_demo": f.get("wants_demo"),
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
        fields = [{"name": n, "description": n, "value": v, "required": True} for n, v in state.fields.items()]
    return {
        "id": state.conversation_id, "workflow_id": state.workflow_id,
        "created_at": _iso(calls.created_at(conversation_id)),
        "workflow_status": state.status, "fields": fields,
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
    demo = [r for r in rows if r["wants_demo"] is True]
    latencies = [r["latency_avg"] for r in done if r["latency_avg"] is not None]
    pct = lambda n, d: round(100 * n / d, 1) if d else 0
    return {
        "total": len(rows), "calls": len(phone_calls), "finished": len(done),
        "failed": sum(r["status"] == "fallida" for r in phone_calls),
        "completed": len(completed), "completed_pct": pct(len(completed), len(rows)),
        "demo": len(demo), "demo_pct": pct(len(demo), len(rows)),
        "total_minutes": round(sum(r["duration_seconds"] for r in done) / 60, 1),
        "avg_duration": round(sum(r["duration_seconds"] for r in done) / len(done)) if done else 0,
        "latency_avg": round(sum(latencies) / len(latencies), 2) if latencies else None,
    }


@app.get("/api/chart")
def chart(date_from: datetime.date, date_to: datetime.date, calls: CallLog = Depends(get_calls)):
    """Conversaciones por dia + % con workflow completo y % que piden demo."""
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
        "demo_pct": [pct(buckets[d], lambda r: r["wants_demo"] is True) for d in days],
    }


@app.get("/api/workflow")
def workflow_definition(workflow_id: str = config.WORKFLOW_ID):
    try:
        return load_workflow(workflow_id)
    except KeyError:
        raise HTTPException(404, "Workflow inexistente")
