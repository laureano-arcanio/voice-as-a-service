"""Despacho del worker de voz a una room de LiveKit y link de la llamada de prueba."""
import datetime
import json
import urllib.parse

from livekit import api

from ..config import settings


async def dispatch_call(room_name: str, metadata: dict) -> None:
    """metadata llega al worker en ctx.job.metadata (app/voice/worker.py, CallMetadata)."""
    async with api.LiveKitAPI(url=settings.livekit_url, api_key=settings.livekit_api_key,
                              api_secret=settings.livekit_api_secret) as lkapi:
        await lkapi.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
            agent_name=settings.livekit_agent_name, room=room_name, metadata=json.dumps(metadata)))


def participant_token(room_name: str, identity: str, name: str, ttl: datetime.timedelta | None = None) -> str:
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )
    if ttl is not None:
        token = token.with_ttl(ttl)
    return token.to_jwt()


def build_test_join_url(room_name: str) -> str:
    token = participant_token(room_name, f"tester-{room_name}", "Tester")
    query = urllib.parse.urlencode({"liveKitUrl": settings.livekit_url, "token": token})
    return f"https://meet.livekit.io/custom?{query}"
