"""Agente externo minimo para Atentina (docs/AGENTE_EXTERNO_PLAN.md).

Atentina pone la voz y la telefonia; en cada turno le pide la respuesta a este endpoint, compatible con OpenAI
(`POST /v1/chat/completions`, `stream: true`). Este ejemplo antepone su propio prompt y reenvia la conversacion
a un LLM (cualquiera compatible con OpenAI), pasando tal cual las herramientas de la plataforma (`end_call` y,
si el agente deriva, `transfer_call`): cuando el LLM las llama, Atentina corta o pasa la llamada.

    pip install fastapi uvicorn openai
    AGENT_KEY=... UPSTREAM_BASE_URL=https://api.openai.com/v1 UPSTREAM_API_KEY=sk-... UPSTREAM_MODEL=gpt-4.1-mini \\
        uvicorn server:app --port 8200

En Atentina: una conexion "Compatible con OpenAI" con la URL publica de este server (https) y AGENT_KEY como
API key, y el agente con el motor external apuntando a esa conexion.
"""
import os

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

PROMPT = """Sos Sofía, la recepcionista de Acme. Hablás por teléfono: respuestas cortas, sin listas ni emojis.
Cuando la persona se despide o ya resolviste lo que necesitaba, despedite y llamá a end_call."""

app = FastAPI()
upstream = AsyncOpenAI(base_url=os.environ["UPSTREAM_BASE_URL"], api_key=os.environ["UPSTREAM_API_KEY"])


@app.post("/v1/chat/completions")
async def chat(request: Request, authorization: str = Header(""),
               x_atentina_conversation_id: str = Header(""), x_atentina_from: str = Header("")):
    if authorization != f"Bearer {os.environ['AGENT_KEY']}":
        raise HTTPException(401, "API key invalida")
    body = await request.json()
    # El historial completo llega en cada turno: no hace falta guardar estado. Si se guarda, por
    # X-Atentina-Conversation-Id, y tolerando que un turno se repita con otro texto (Atentina lo deshace
    # si la persona siguio hablando antes de escuchar la respuesta).
    messages = [{"role": "system", "content": f"{PROMPT}\nNúmero de quien llama: {x_atentina_from or 'desconocido'}."},
                *[m for m in body["messages"] if m["role"] != "system"]]
    stream = await upstream.chat.completions.create(
        model=os.environ["UPSTREAM_MODEL"], messages=messages, tools=body.get("tools") or None, stream=True)

    async def events():
        async for chunk in stream:
            yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
