"""Crea (o actualiza) en LiveKit Cloud los 3 objetos SIP de la troncal de Anura
via Asterisk (ver docs/TELEFONIA_ANURA.md):

  - inbound trunk (Asterisk -> LiveKit): acepta llamadas a +54<ANURA_DID>
    autenticadas con usuario "livekit" y LIVEKIT_SIP_PASSWORD.
  - dispatch rule: una room nueva por llamada entrante (prefijo "anura-") con
    el agente LIVEKIT_AGENT_NAME despachado. Sin metadata a proposito: el
    agente reconoce una entrante porque no trae local_call_id
    (app/livekit_agent.py).
  - outbound trunk (LiveKit -> Asterisk): a donde manda LiveKit las llamadas
    que marca el agente (create_sip_participant). Su ID va en
    LIVEKIT_SIP_TRUNK_ID.

Idempotente: busca cada objeto por nombre y, si ya existe, lo pisa con la
config actual. Volver a correrlo despues de cambiar la IP publica, el puerto o
la clave.

Uso: make livekit-sip
"""
import asyncio
import os
import re
import sys
import urllib.request

from livekit import api

INBOUND_NAME = "anura-asterisk-inbound"
OUTBOUND_NAME = "anura-asterisk-outbound"
DISPATCH_NAME = "anura-asterisk-dispatch"
# Fijo: en asterisk/conf/pjsip.conf el endpoint que recibe las salientes de
# LiveKit se identifica por el usuario del digest (identify_by=auth_username),
# y ese usuario tiene que ser igual al nombre del endpoint.
SIP_USERNAME = "livekit"
# LiveKit no tiene region en Argentina: "br" hace que las salientes salgan de
# Sao Paulo, la mas cercana a Asterisk/Anura (sin esto puede salir de EE.UU.).
DESTINATION_COUNTRY = "br"


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        sys.exit(f"Falta {name} en .env (ver docs/TELEFONIA_ANURA.md)")
    return value


def public_address() -> str:
    address = os.getenv("ASTERISK_PUBLIC_ADDRESS", "").strip()
    if address:
        return address
    # Mismo fallback que asterisk/entrypoint.sh. Este script corre en la misma
    # maquina que Asterisk, asi que ve la misma IP publica.
    with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
        return resp.read().decode().strip()


async def upsert(name, items, create, update):
    existing = [x for x in items if x.name == name]
    if existing:
        return await update(existing[0]), "actualizado"
    return await create(), "creado"


async def main() -> None:
    did = required("ANURA_DID")
    if not re.fullmatch(r"\d{10}", did):
        sys.exit("ANURA_DID tiene que ser el numero nacional de 10 digitos, sin 0 ni 15 ni +54 (ej. 1152630861)")
    number = f"+54{did}"
    password = required("LIVEKIT_SIP_PASSWORD")
    agent_name = required("LIVEKIT_AGENT_NAME")
    address = f"{public_address()}:{os.getenv('ASTERISK_SIP_PORT') or '5080'}"

    async with api.LiveKitAPI(
        url=required("LIVEKIT_URL"),
        api_key=required("LIVEKIT_API_KEY"),
        api_secret=required("LIVEKIT_API_SECRET"),
    ) as lk:
        inbound_info = api.SIPInboundTrunkInfo(
            name=INBOUND_NAME,
            numbers=[number],
            auth_username=SIP_USERNAME,
            auth_password=password,
        )
        inbound, inbound_action = await upsert(
            INBOUND_NAME,
            (await lk.sip.list_inbound_trunk(api.ListSIPInboundTrunkRequest())).items,
            lambda: lk.sip.create_inbound_trunk(api.CreateSIPInboundTrunkRequest(trunk=inbound_info)),
            lambda t: lk.sip.update_inbound_trunk(t.sip_trunk_id, inbound_info),
        )

        dispatch_info = api.SIPDispatchRuleInfo(
            name=DISPATCH_NAME,
            trunk_ids=[inbound.sip_trunk_id],
            rule=api.SIPDispatchRule(
                dispatch_rule_individual=api.SIPDispatchRuleIndividual(room_prefix="anura-"),
            ),
            room_config=api.RoomConfiguration(agents=[api.RoomAgentDispatch(agent_name=agent_name)]),
        )
        dispatch, dispatch_action = await upsert(
            DISPATCH_NAME,
            (await lk.sip.list_dispatch_rule(api.ListSIPDispatchRuleRequest())).items,
            lambda: lk.sip.create_dispatch_rule(api.CreateSIPDispatchRuleRequest(dispatch_rule=dispatch_info)),
            lambda r: lk.sip.update_dispatch_rule(r.sip_dispatch_rule_id, dispatch_info),
        )

        outbound_info = api.SIPOutboundTrunkInfo(
            name=OUTBOUND_NAME,
            address=address,
            transport=api.SIPTransport.SIP_TRANSPORT_UDP,
            numbers=[number],
            auth_username=SIP_USERNAME,
            auth_password=password,
            destination_country=DESTINATION_COUNTRY,
        )
        outbound, outbound_action = await upsert(
            OUTBOUND_NAME,
            (await lk.sip.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())).items,
            lambda: lk.sip.create_outbound_trunk(api.CreateSIPOutboundTrunkRequest(trunk=outbound_info)),
            lambda t: lk.sip.update_outbound_trunk(t.sip_trunk_id, outbound_info),
        )

    print(f"Inbound trunk  {inbound.sip_trunk_id} ({inbound_action}): acepta llamadas a {number}")
    print(f"Dispatch rule  {dispatch.sip_dispatch_rule_id} ({dispatch_action}): room anura-* -> agente {agent_name}")
    print(f"Outbound trunk {outbound.sip_trunk_id} ({outbound_action}): LiveKit -> Asterisk en {address}/udp")
    configured = os.getenv("LIVEKIT_SIP_TRUNK_ID", "")
    if configured != outbound.sip_trunk_id:
        # `make up` y no `make restart-agent`: `docker compose restart` no relee .env.
        print(f"\nFalta un paso: poner en .env\n  LIVEKIT_SIP_TRUNK_ID={outbound.sip_trunk_id}\ny correr `make up` (recrea el agente con el .env nuevo).")


if __name__ == "__main__":
    asyncio.run(main())
