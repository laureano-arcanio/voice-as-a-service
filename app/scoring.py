"""Motor de scoring: evalua el transcript contra el cuestionario con un LLM."""
import json
import re

import httpx

from . import config

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def _extract_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def score_call(transcript_messages: list, questions: list, bands: list) -> dict:
    """Devuelve {score, outcome, detail: [...], notes}"""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("Falta OPENAI_API_KEY en el archivo .env para el scoring")

    convo = "\n".join(f"[{m['role']}] {m['text']}" for m in transcript_messages if m.get("text"))
    qblock = json.dumps(
        [{"id": q["id"], "pregunta": q["text"], "respuesta_correcta": q["expected"],
          "puntos": q["weight"], "requerida": q["required"]} for q in questions],
        ensure_ascii=False, indent=1)

    system = (
        "Sos el evaluador de llamadas de validaci\u00f3n de AIVA Validate. Recib\u00eds el transcript de una "
        "llamada telef\u00f3nica entre una agente ejecutiva y un cliente que compr\u00f3 un plan de ahorro de un veh\u00edculo, "
        "m\u00e1s un cuestionario con la respuesta correcta de referencia y el puntaje de cada pregunta. "
        "Tu tarea: para CADA pregunta del cuestionario, determinar si la respuesta del cliente demuestra que "
        "entiende el concepto (comparada con la respuesta correcta de referencia). Si la pregunta no se lleg\u00f3 a "
        "hacer, o el cliente no supo responder o respondi\u00f3 mal, se considera NO respondida correctamente y otorga 0 puntos. "
        "No inventes: bas\u00e1te \u00fanicamente en el transcript. "
        "Respond\u00e9 SOLO con JSON v\u00e1lido, sin texto adicional, con esta forma exacta:\n"
        "{\"resultados\": [{\"id\": <id pregunta>, \"correcta\": true|false, \"respuesta_cliente\": \"resumen breve "
        "de lo que dijo el cliente o 'no respondida'\", \"justificacion\": \"por qu\u00e9 se considera correcta o no\"}], "
        "\"observaciones\": \"nota general breve sobre la llamada\"}"
    )
    user = f"CUESTIONARIO:\n{qblock}\n\nTRANSCRIPT DE LA LLAMADA:\n{convo}"

    r = httpx.post(
        OPENAI_URL,
        headers={
            "authorization": f"Bearer {config.OPENAI_API_KEY}",
            "content-type": "application/json",
        },
        json={
            "model": config.OPENAI_SCORING_MODEL,
            "max_completion_tokens": 3000,
            # Es un juicio sobre un transcript corto: sin razonamiento previo
            # responde mucho mas rapido y el JSON pedido sigue saliendo bien.
            "reasoning_effort": "none",
            # Fuerza salida JSON valida (el prompt ya lo pide; esto lo garantiza).
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=90,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"OpenAI respondi\u00f3 {r.status_code}: {r.text[:400]}")
    data = r.json()
    text = data["choices"][0]["message"].get("content") or ""
    parsed = _extract_json(text)

    by_id = {q["id"]: q for q in questions}
    detail, score = [], 0
    required_failed = False
    for res in parsed.get("resultados", []):
        q = by_id.get(res.get("id"))
        if not q:
            continue
        correct = bool(res.get("correcta"))
        points = q["weight"] if correct else 0
        score += points
        if q["required"] and not correct:
            required_failed = True
        detail.append({
            "question_id": q["id"], "question": q["text"], "weight": q["weight"],
            "required": q["required"], "correct": correct, "points": points,
            "customer_answer": res.get("respuesta_cliente", ""),
            "rationale": res.get("justificacion", ""),
        })

    outcome = ""
    for b in bands:
        if b["min_score"] <= score <= b["max_score"]:
            outcome = b["outcome"]
            break
    if not outcome:
        outcome = "a_definir"
    # Regla de preguntas requeridas: sobresee al score si este aprueba
    if required_failed and outcome == "aprobado":
        outcome = "a_definir"

    return {
        "score": score,
        "outcome": outcome,
        "detail": detail,
        "notes": parsed.get("observaciones", ""),
        "required_failed": required_failed,
    }
