import json
import re

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from sqlalchemy import text as sql_text
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, livekit_dispatch, scoring
from .db import Band, Call, Question, SessionLocal, init_db

app = FastAPI(title="AIVA Validate Demo")

templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "static")), name="static")


@app.on_event("startup")
def _startup():
    init_db(seed=True)


# ---------- paginas ----------

@app.get("/")
def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/config")
def page_config(request: Request):
    return templates.TemplateResponse("config.html", {"request": request})


@app.get("/calls/{call_id}")
def page_call(request: Request, call_id: int):
    return templates.TemplateResponse("call.html", {"request": request, "call_id": call_id})


@app.get("/health")
def health():
    return {"ok": True}


# ---------- API: preguntas ----------

@app.get("/api/questions")
def list_questions():
    with SessionLocal() as s:
        qs = s.query(Question).order_by(Question.position, Question.id).all()
        return [q.as_dict() for q in qs]


@app.post("/api/questions")
async def create_question(request: Request):
    data = await request.json()
    with SessionLocal() as s:
        q = Question(
            position=int(data.get("position") or 0),
            text=(data.get("text") or "").strip(),
            expected=(data.get("expected") or "").strip(),
            weight=int(data.get("weight") or 0),
            required=bool(data.get("required")),
            active=bool(data.get("active", True)),
        )
        if not q.text:
            raise HTTPException(422, "La pregunta no puede estar vac\u00eda")
        s.add(q)
        s.commit()
        return q.as_dict()


@app.put("/api/questions/{qid}")
async def update_question(qid: int, request: Request):
    data = await request.json()
    with SessionLocal() as s:
        q = s.get(Question, qid)
        if not q:
            raise HTTPException(404)
        for field in ("text", "expected"):
            if field in data:
                setattr(q, field, (data[field] or "").strip())
        if "position" in data:
            q.position = int(data["position"] or 0)
        if "weight" in data:
            q.weight = int(data["weight"] or 0)
        if "required" in data:
            q.required = bool(data["required"])
        if "active" in data:
            q.active = bool(data["active"])
        s.commit()
        return q.as_dict()


@app.delete("/api/questions/{qid}")
def delete_question(qid: int):
    with SessionLocal() as s:
        q = s.get(Question, qid)
        if q:
            s.delete(q)
            s.commit()
    return {"ok": True}


# ---------- API: bandas de score ----------

@app.get("/api/bands")
def list_bands():
    with SessionLocal() as s:
        return [b.as_dict() for b in s.query(Band).order_by(Band.min_score).all()]


@app.put("/api/bands")
async def replace_bands(request: Request):
    data = await request.json()
    bands = data.get("bands", [])
    if not bands:
        raise HTTPException(422, "Debe haber al menos una banda")
    for b in bands:
        if b.get("outcome") not in ("rechazado", "a_definir", "aprobado"):
            raise HTTPException(422, "Resultado inv\u00e1lido en una banda")
        if int(b.get("min_score", 0)) > int(b.get("max_score", 0)):
            raise HTTPException(422, "Una banda tiene m\u00ednimo mayor que m\u00e1ximo")
    with SessionLocal() as s:
        s.query(Band).delete()
        for b in bands:
            s.add(Band(min_score=int(b["min_score"]), max_score=int(b["max_score"]), outcome=b["outcome"]))
        s.commit()
    return list_bands()


# ---------- API: llamadas ----------

def _phone_normalize(raw: str) -> str:
    p = re.sub(r"[\s()\-\.]", "", raw or "")
    if not p:
        raise HTTPException(422, "Ingres\u00e1 un n\u00famero de tel\u00e9fono")
    if not p.startswith("+"):
        p = "+" + p
    if not re.fullmatch(r"\+\d{8,15}", p):
        raise HTTPException(422, "N\u00famero inv\u00e1lido: usar formato internacional, ej. +5491155551234")
    return p


@app.post("/api/calls")
async def start_call(request: Request):
    data = await request.json()
    phone = _phone_normalize(data.get("phone", ""))
    gender = data.get("client_gender", "")
    if gender not in ("", "masculino", "femenino"):
        raise HTTPException(422, "G\u00e9nero inv\u00e1lido")
    client = {
        "name": (data.get("client_name") or "").strip()[:120],
        "gender": gender,
        "notes": (data.get("client_notes") or "").strip()[:2000],
    }
    with SessionLocal() as s:
        questions = [q.as_dict() for q in s.query(Question)
                     .filter(Question.active.is_(True))
                     .order_by(Question.position, Question.id).all()]
        bands = [b.as_dict() for b in s.query(Band).order_by(Band.min_score).all()]
        if not questions:
            raise HTTPException(422, "No hay preguntas activas configuradas")
        call = Call(
            phone=phone, status="pendiente", provider="livekit",
            client_name=client["name"], client_gender=client["gender"],
            client_notes=client["notes"],
            questions_snapshot=json.dumps(questions, ensure_ascii=False),
            bands_snapshot=json.dumps(bands, ensure_ascii=False),
        )
        s.add(call)
        s.commit()
        room_name = f"call-{call.id}"
        try:
            await livekit_dispatch.dispatch_call(room_name=room_name, local_call_id=call.id)
            call.provider_call_id = room_name
        except Exception as e:  # noqa: BLE001
            call.status = "fallida"
            call.score_error = str(e)
        s.commit()
        if call.status == "fallida":
            raise HTTPException(502, f"No se pudo iniciar la llamada: {call.score_error}")
        return call.as_dict()


@app.get("/api/calls")
def list_calls(limit: int = 100):
    with SessionLocal() as s:
        calls = s.query(Call).order_by(Call.id.desc()).limit(limit).all()
        return [c.as_dict() for c in calls]


@app.get("/api/calls/{call_id}")
def get_call(call_id: int):
    with SessionLocal() as s:
        c = s.get(Call, call_id)
        if not c:
            raise HTTPException(404)
        return c.as_dict(full=True)


@app.get("/api/stats")
def stats():
    with SessionLocal() as s:
        calls = s.query(Call).all()
    total = len(calls)
    done = [c for c in calls if c.status == "finalizada"]
    scored = [c for c in done if c.outcome]
    apr = sum(1 for c in scored if c.outcome == "aprobado")
    adef = sum(1 for c in scored if c.outcome == "a_definir")
    rech = sum(1 for c in scored if c.outcome == "rechazado")
    avg = round(sum(c.score or 0 for c in scored) / len(scored), 1) if scored else 0
    mins = round(sum(c.duration_seconds for c in done) / 60.0, 1)
    return {
        "total_calls": total, "completed": len(done), "scored": len(scored),
        "approved": apr, "a_definir": adef, "rejected": rech,
        "approval_pct": round(100.0 * apr / len(scored), 1) if scored else 0,
        "avg_score": avg, "total_minutes": mins,
    }


@app.get("/api/chart")
def chart(bucket: str = "day", date_from: str = "", date_to: str = ""):
    """Serie temporal para el grafico del dashboard: cantidad de llamadas por
    periodo + % de aprobadas y rechazadas (sobre las que tienen resultado)."""
    fmt = {"day": "%Y-%m-%d", "week": "%x-S%v", "month": "%Y-%m"}.get(bucket, "%Y-%m-%d")
    where, params = ["1=1"], {"fmt": fmt}
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_from or ""):
        where.append("created_at >= :df")
        params["df"] = date_from
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_to or ""):
        where.append("created_at < DATE_ADD(:dt, INTERVAL 1 DAY)")
        params["dt"] = date_to
    q = sql_text(
        "SELECT DATE_FORMAT(created_at, :fmt) AS b, COUNT(*) AS total, "
        "SUM(outcome='aprobado') AS apr, SUM(outcome='rechazado') AS rech, "
        "SUM(outcome='a_definir') AS adef "
        f"FROM calls WHERE {' AND '.join(where)} GROUP BY b ORDER BY b"
    )
    with SessionLocal() as s:
        rows = s.execute(q, params).all()
    labels, totals, apr_pct, rech_pct = [], [], [], []
    for b, total, apr, rech, adef in rows:
        labels.append(b)
        totals.append(int(total))
        scored = int(apr or 0) + int(rech or 0) + int(adef or 0)
        apr_pct.append(round(100.0 * int(apr or 0) / scored, 1) if scored else None)
        rech_pct.append(round(100.0 * int(rech or 0) / scored, 1) if scored else None)
    return {"labels": labels, "totals": totals, "apr_pct": apr_pct, "rech_pct": rech_pct}


@app.post("/api/calls/{call_id}/rescore")
def rescore(call_id: int, background: BackgroundTasks):
    with SessionLocal() as s:
        c = s.get(Call, call_id)
        if not c or not c.transcript_json:
            raise HTTPException(422, "La llamada no tiene transcript para evaluar")
    background.add_task(_run_scoring, call_id)
    return {"ok": True}


def _run_scoring(call_id: int):
    with SessionLocal() as s:
        c = s.get(Call, call_id)
        if not c or not c.transcript_json:
            return
        try:
            result = scoring.score_call(
                json.loads(c.transcript_json),
                json.loads(c.questions_snapshot or "[]"),
                json.loads(c.bands_snapshot or "[]"),
            )
            c.score = result["score"]
            c.outcome = result["outcome"]
            c.score_detail = json.dumps(result, ensure_ascii=False)
            c.score_error = ""
        except Exception as e:  # noqa: BLE001
            c.score_error = str(e)
        s.commit()


# ---------- audio ----------

@app.get("/recordings/{fname}")
def recording(fname: str):
    if "/" in fname or ".." in fname:
        raise HTTPException(404)
    path = config.RECORDINGS_DIR / fname
    if not path.exists():
        raise HTTPException(404)
    media = "audio/wav" if fname.endswith(".wav") else "audio/mpeg"
    return FileResponse(path, media_type=media)
