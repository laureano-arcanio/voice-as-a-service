"""Dispara una llamada saliente despachando el agente de LiveKit a una nueva room.

A diferencia de Vapi (donde `start_call` disparaba la llamada via una API REST y
Vapi nos avisaba el resultado por webhook), acá solo despachamos un job al worker
del agente (`app/livekit_agent.py`); el propio worker es quien marca la llamada
al cliente y escribe el resultado directo en la base de datos.
"""
import json

from livekit import api

from . import config


async def dispatch_call(room_name: str, local_call_id: int) -> None:
    if not (config.LIVEKIT_URL and config.LIVEKIT_API_KEY and config.LIVEKIT_API_SECRET):
        raise RuntimeError("Faltan LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET en el archivo .env")
    async with api.LiveKitAPI(
        url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    ) as lkapi:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=config.LIVEKIT_AGENT_NAME,
                room=room_name,
                metadata=json.dumps({"local_call_id": local_call_id}),
            )
        )
