import json
import urllib.parse

from livekit import api

from . import config


async def dispatch_call(room_name: str, conversation_id: str, phone: str | None, voice: str | None = None,
                        loadtest: bool = False) -> None:
    async with api.LiveKitAPI(
        url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    ) as lkapi:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=config.LIVEKIT_AGENT_NAME,
                room=room_name,
                metadata=json.dumps({"conversation_id": conversation_id, "phone": phone, "voice": voice,
                                     "loadtest": loadtest}),
            )
        )


def build_test_join_url(room_name: str) -> str:
    token = (
        api.AccessToken(config.LIVEKIT_API_KEY, config.LIVEKIT_API_SECRET)
        .with_identity(f"tester-{room_name}")
        .with_name("Tester")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )
    query = urllib.parse.urlencode({"liveKitUrl": config.LIVEKIT_URL, "token": token})
    return f"https://meet.livekit.io/custom?{query}"
