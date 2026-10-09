"""Crea (o actualiza) en LiveKit Cloud los 3 objetos SIP de la troncal de Anura
via Asterisk (ver docs/TELEFONIA_ANURA.md):

  - inbound trunk (Asterisk -> LiveKit): acepta llamadas a los numeros de los
    clientes (tabla phone_numbers; +54<ANURA_DID> si la base no responde o no
    tiene ninguno) autenticadas con usuario "livekit" y LIVEKIT_SIP_PASSWORD.
  - dispatch rule: una room nueva por llamada entrante (prefijo "anura-") con
    el agente LIVEKIT_AGENT_NAME despachado. Sin metadata a proposito: el
    agente reconoce una entrante porque no trae conversation_id y la rutea por
    el numero marcado al agente de ese numero (app/voice/worker.py).
  - outbound trunk (LiveKit -> Asterisk): a donde manda LiveKit las llamadas
    que marca el agente (create_sip_participant). Su ID va en
    LIVEKIT_SIP_TRUNK_ID.

Con LiveKit propio (docker-compose.livekit.yml) el trunk saliente apunta a
LIVEKIT_SIP_OUTBOUND_ADDRESS (Asterisk en este host), que pone el override.
Idempotente: busca cada objeto por nombre y, si ya existe, lo pisa con la
config actual. Volver a correrlo despues de cambiar la IP publica, el puerto o
la clave.

Con LiveKit propio, `make up` lo corre solo al final: su Redis no persiste
(--save "" en el override), asi que cada reinicio del host borra los tres
objetos y las entrantes vuelven con 486 hasta recrearlos. Como el ID del trunk
saliente cambia cada vez, con LiveKit propio conviene dejar LIVEKIT_SIP_TRUNK_ID
vacio: el agente lo busca por nombre (OUTBOUND_NAME) al marcar.

Al agregar o quitar numeros en la UI, volver a correrlo. Anura y Asterisk tienen
que entregar esos numeros (docs/TELEFONIA_ANURA.md).

El trunk entrante corta toda llamada a los CALL_DURATION_CEILING_SECONDS: respaldo del
corte del worker (tope del tier), por si este se cae sin colgar.

Uso: make livekit-sip
     python -m scripts.livekit_sip_setup --check   (healthcheck: no crea nada; exit 1 si
     faltan los trunks, la dispatch rule o numeros de phone_numbers en el trunk entrante)
"""
import argparse
import asyncio
import os
import re
import sys
import time
import urllib.error
import urllib.request

from google.protobuf.duration_pb2 import Duration

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


def ceiling_seconds() -> int:
    """CALL_DURATION_CEILING_SECONDS, con el mismo default que la app."""
    from app.config import settings

    return settings.call_duration_ceiling_seconds


def wait_for_livekit(url: str, timeout: float = 90.0) -> None:
    """Espera a que el server responda en LIVEKIT_URL (GET / devuelve "OK").

    `make up` vuelve antes de que livekit escuche; sin esto, la primera llamada
    a la API falla con connection refused.
    """
    http = re.sub(r"^ws", "http", url)
    deadline = time.monotonic() + timeout
    while True:
        try:
            with urllib.request.urlopen(http, timeout=3) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError, TimeoutError):
            pass
        if time.monotonic() > deadline:
            sys.exit(f"LiveKit no responde en {http} despues de {int(timeout)} s")
        time.sleep(2)


async def upsert(name, items, create, update):
    existing = [x for x in items if x.name == name]
    if existing:
        return await update(existing[0]), "actualizado"
    return await create(), "creado"


def client_numbers() -> list[str]:
    """Numeros E.164 de la tabla phone_numbers ([] si la base no responde)."""
    try:
        from sqlalchemy import select

        from app.db import get_sessionmaker
        from app.models import PhoneNumber

        with get_sessionmaker()() as s:
            return sorted(s.scalars(select(PhoneNumber.e164)))
    except Exception as e:  # noqa: BLE001
        print(f"aviso: no se pudieron leer los numeros de la base ({e}); uso ANURA_DID", file=sys.stderr)
        return []


def expected_numbers() -> list[str]:
    did = required("ANURA_DID")
    if not re.fullmatch(r"\d{10}", did):
        sys.exit("ANURA_DID tiene que ser el numero nacional de 10 digitos, sin 0 ni 15 ni +54 (ej. 1152630861)")
    return sorted({f"+54{did}", *client_numbers()})


def find(items, name):
    return next((x for x in items if x.name == name), None)


async def check() -> int:
    """Solo mira: 0 si estan los tres objetos y el trunk entrante acepta todos los numeros;
    si no, 1 con un renglon por problema. Para el healthcheck (el Redis de LiveKit propio
    no persiste: un reinicio de livekit sin `make livekit-sip` deja las entrantes en 486)."""
    numbers = expected_numbers()
    wait_for_livekit(required("LIVEKIT_URL"), timeout=10)
    async with api.LiveKitAPI(
        url=required("LIVEKIT_URL"),
        api_key=required("LIVEKIT_API_KEY"),
        api_secret=required("LIVEKIT_API_SECRET"),
    ) as lk:
        inbound = find((await lk.sip.list_inbound_trunk(api.ListSIPInboundTrunkRequest())).items, INBOUND_NAME)
        dispatch = find((await lk.sip.list_dispatch_rule(api.ListSIPDispatchRuleRequest())).items, DISPATCH_NAME)
        outbound = find((await lk.sip.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())).items, OUTBOUND_NAME)
    problems = []
    if inbound is None:
        problems.append(f"falta el trunk entrante {INBOUND_NAME}")
    else:
        if missing := sorted(set(numbers) - set(inbound.numbers)):
            problems.append(f"el trunk entrante no acepta {', '.join(missing)}")
        if not inbound.max_call_duration.seconds:
            problems.append("el trunk entrante no tiene max_call_duration")
    if dispatch is None:
        problems.append(f"falta la dispatch rule {DISPATCH_NAME}")
    elif inbound is not None and inbound.sip_trunk_id not in dispatch.trunk_ids:
        problems.append(f"la dispatch rule {DISPATCH_NAME} no apunta al trunk entrante")
    if outbound is None:
        problems.append(f"falta el trunk saliente {OUTBOUND_NAME}")
    for problem in problems:
        print(f"SIP de LiveKit: {problem} (correr `make livekit-sip`)")
    if not problems:
        print(f"SIP de LiveKit: ok ({len(numbers)} numeros)")
    return 1 if problems else 0


async def main() -> None:
    numbers = expected_numbers()
    password = required("LIVEKIT_SIP_PASSWORD")
    agent_name = required("LIVEKIT_AGENT_NAME")
    address = (os.getenv("LIVEKIT_SIP_OUTBOUND_ADDRESS", "").strip()
               or f"{public_address()}:{os.getenv('ASTERISK_SIP_PORT') or '5080'}")

    wait_for_livekit(required("LIVEKIT_URL"))
    async with api.LiveKitAPI(
        url=required("LIVEKIT_URL"),
        api_key=required("LIVEKIT_API_KEY"),
        api_secret=required("LIVEKIT_API_SECRET"),
    ) as lk:
        inbound_info = api.SIPInboundTrunkInfo(
            name=INBOUND_NAME,
            numbers=numbers,
            auth_username=SIP_USERNAME,
            auth_password=password,
            max_call_duration=Duration(seconds=ceiling_seconds()),
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
            # Caller IDs posibles: el numero del cliente que llama (sip_number).
            numbers=numbers,
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

    print(f"Inbound trunk  {inbound.sip_trunk_id} ({inbound_action}): acepta llamadas a {', '.join(numbers)}"
          f" (corta a los {ceiling_seconds()} s)")
    print(f"Dispatch rule  {dispatch.sip_dispatch_rule_id} ({dispatch_action}): room anura-* -> agente {agent_name}")
    print(f"Outbound trunk {outbound.sip_trunk_id} ({outbound_action}): LiveKit -> Asterisk en {address}/udp")
    configured = os.getenv("LIVEKIT_SIP_TRUNK_ID", "")
    if not configured:
        print(f"LIVEKIT_SIP_TRUNK_ID vacio: el agente usa el trunk saliente por nombre ({OUTBOUND_NAME}).")
    elif configured != outbound.sip_trunk_id:
        # `make up` y no `make restart-agent`: `docker compose restart` no relee .env.
        print(f"\nOJO: .env tiene LIVEKIT_SIP_TRUNK_ID={configured}, que ya no es el trunk saliente."
              f"\nDejarlo vacio (el agente lo busca por nombre) o poner {outbound.sip_trunk_id},"
              f"\ny correr `make up` (recrea el agente con el .env nuevo).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trunks SIP y dispatch rule de LiveKit para Anura")
    parser.add_argument("--check", action="store_true", help="solo verificar (exit 1 si falta algo)")
    if parser.parse_args().check:
        sys.exit(asyncio.run(check()))
    asyncio.run(main())
