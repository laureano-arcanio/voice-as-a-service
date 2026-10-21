"""Despacho del worker de voz a una room de LiveKit, link de la llamada de prueba y
numeros de los trunks SIP."""
import datetime
import json
import logging
import urllib.parse

from livekit import api

from ..config import settings

logger = logging.getLogger(__name__)


async def dispatch_call(room_name: str, metadata: dict) -> None:
    """metadata llega al worker en ctx.job.metadata (app/voice/worker.py, CallMetadata)."""
    async with api.LiveKitAPI(url=settings.livekit_url, api_key=settings.livekit_api_key,
                              api_secret=settings.livekit_api_secret) as lkapi:
        await lkapi.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
            agent_name=settings.livekit_agent_name, room=room_name, metadata=json.dumps(metadata)))


async def delete_room(room_name: str) -> bool:
    """Cierra la room: cuelga a todos (la otra punta de la llamada incluida) y el worker termina.
    False si la room ya no existe."""
    async with api.LiveKitAPI(url=settings.livekit_url, api_key=settings.livekit_api_key,
                              api_secret=settings.livekit_api_secret) as lkapi:
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
        except api.TwirpError as e:
            if e.code == api.TwirpErrorCode.NOT_FOUND:
                return False
            raise
    return True


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


async def sync_trunk_numbers(add: list[str] = (), remove: list[str] = ()) -> None:
    """Agrega o quita numeros de los trunks SIP entrante y saliente, en caliente.

    livekit-sip lee los trunks en cada INVITE: el cambio vale desde la llamada
    siguiente, sin reiniciar nada. Sin el numero en el trunk entrante, la llamada
    vuelve con 486 "flood" (19-oct-2026). Incremental (ListUpdate), para no pisar
    la lista con una lectura parcial; `make livekit-sip` la rearma entera y crea
    los trunks si faltan (reinicio del host). Corre en segundo plano: un error
    solo se loguea.
    """
    if not (settings.livekit_sip_sync and settings.livekit_url) or not (add or remove):
        return
    update = api.ListUpdate(add=sorted(add), remove=sorted(remove))
    try:
        async with api.LiveKitAPI(url=settings.livekit_url, api_key=settings.livekit_api_key,
                                  api_secret=settings.livekit_api_secret) as lk:
            inbound = [t for t in (await lk.sip.list_inbound_trunk(api.ListSIPInboundTrunkRequest())).items
                       if t.name == settings.livekit_sip_inbound_trunk_name]
            outbound = [t for t in (await lk.sip.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())).items
                        if t.name == settings.livekit_sip_outbound_trunk_name]
            if not inbound:
                logger.warning("trunks SIP: no existe %s, correr `make livekit-sip`",
                               settings.livekit_sip_inbound_trunk_name)
            for t in inbound:
                await lk.sip.update_inbound_trunk_fields(t.sip_trunk_id, numbers=update)
            for t in outbound:
                await lk.sip.update_outbound_trunk_fields(t.sip_trunk_id, numbers=update)
        logger.info("trunks SIP: agregados %s, quitados %s", sorted(add), sorted(remove))
    except Exception:
        logger.exception("trunks SIP: no se pudieron actualizar los numeros (correr `make livekit-sip`)")
