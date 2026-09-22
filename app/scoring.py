"""Motor de scoring: califica el lead evaluando el transcript contra el cuestionario con un LLM."""
import json
import re

import httpx

from . import config

LLM_URL = f"{config.VLLM_LLM_BASE_URL}/chat/completions"


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
    if not config.VLLM_LLM_BASE_URL:
        raise RuntimeError("Falta VLLM_LLM_BASE_URL en el archivo .env para el scoring")

    convo = "\n".join(f"[{m['role']}] {m['text']}" for m in transcript_messages if m.get("text"))
    qblock = json.dumps(
        [{"id": q["id"], "pregunta": q["text"], "criterio": q["expected"],
          "puntos": q["weight"], "requerida": q["required"]} for q in questions],
        ensure_ascii=False, indent=1)

    system = (
        f"Sos el evaluador de llamadas comerciales de {config.COMPANY_NAME}, una plataforma de gesti\u00f3n de "
        "personal (control horario y presentismo, recibos de sueldo digitales, recursos humanos y operaciones "
        "en terreno). Recib\u00eds el transcript de una llamada telef\u00f3nica entre una asesora comercial "
        "virtual y una persona interesada, m\u00e1s un cuestionario de calificaci\u00f3n del lead con el criterio "
        "de cada pregunta y su puntaje. "
        "Tu tarea: para CADA pregunta del cuestionario, determinar si lo que dijo el interesado cumple el "
        "criterio. Vale lo que el interesado haya dicho en cualquier momento de la llamada, aunque la pregunta "
        "no se haya hecho literalmente. Si el dato no surge del transcript, el interesado no lo sabe o no "
        "cumple el criterio, se considera NO cumplida y otorga 0 puntos. "
        "No inventes ni deduzcas: bas\u00e1te \u00fanicamente en lo que dice el interesado en el transcript. "
        "Lo que dice la asesora no cuenta como respuesta del interesado, salvo lo que el criterio "
        "indique expl\u00edcitamente. Por ejemplo, si nunca dijo qui\u00e9n "
        "decide, la pregunta del decisor NO se cumple aunque parezca el due\u00f1o. "
        "Respond\u00e9 SOLO con JSON v\u00e1lido, sin texto adicional, con esta forma exacta:\n"
        "{\"resultados\": [{\"id\": <id pregunta>, \"cumple\": true|false, \"respuesta_cliente\": \"resumen breve "
        "de lo que dijo el interesado o 'no respondida'\", \"justificacion\": \"por qu\u00e9 cumple o no el "
        "criterio\"}], "
        "\"observaciones\": \"resumen breve del lead para el asesor: empresa, rubro, cantidad de empleados, "
        "necesidad principal, consultas que quedaron pendientes y pr\u00f3ximo paso acordado\"}"
    )
    user = f"CUESTIONARIO:\n{qblock}\n\nTRANSCRIPT DE LA LLAMADA:\n{convo}"

    r = httpx.post(
        LLM_URL,
        headers={
            "authorization": f"Bearer {config.VLLM_API_KEY}",
            "content-type": "application/json",
        },
        json={
            "model": config.VLLM_SCORING_MODEL,
            "max_completion_tokens": 3000,
            # Es un juicio sobre un transcript corto: sin razonamiento previo
            # responde mucho mas rapido y el JSON pedido sigue saliendo bien.
            # Probado que vLLM respeta este campo igual que OpenAI.
            "reasoning_effort": "none",
            # Fuerza salida JSON valida (el prompt ya lo pide; esto lo garantiza;
            # probado contra vllm-llm).
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=90,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"El LLM local respondi\u00f3 {r.status_code}: {r.text[:400]}")
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
        correct = bool(res.get("cumple"))
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
        outcome = "tibio"
    # Regla de preguntas requeridas: sobresee al score -- un lead no puede
    # quedar caliente si falla una requerida (ej. no acepto la demo).
    if required_failed and outcome == "caliente":
        outcome = "tibio"

    return {
        "score": score,
        "outcome": outcome,
        "detail": detail,
        "notes": parsed.get("observaciones", ""),
        "required_failed": required_failed,
    }
