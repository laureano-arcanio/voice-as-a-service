"""CLI de la Graph API de WhatsApp (docs/WHATSAPP_PLAN.md, fase 0).

  python -m scripts.wa send-text --to 54351... --text "hola" [--phone-number-id ID]
  python -m scripts.wa send-template --to ... --name NOMBRE [--language es] [--param X ...]
  python -m scripts.wa request-code --method SMS|VOICE [--language es]
  python -m scripts.wa verify-code --code 123456
  python -m scripts.wa register --pin 123456
  python -m scripts.wa calling-status
  python -m scripts.wa calling-enable --sip-host sip.atentina.com.ar [--sip-port 5061]
  python -m scripts.wa calling-disable
  python -m scripts.wa sip-password     (imprime SOLO la clave SIP de Meta, para make wa-sip-password)

Lee WA_ACCESS_TOKEN y WA_GRAPH_VERSION (env o app.config.settings) y el
phone_number_id de --phone-number-id o WA_PHONE_NUMBER_ID. No imprime el token.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from app.whatsapp.graph import GraphClient, GraphError


def _setting(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    if v:
        return v
    try:
        from app.config import settings
        return getattr(settings, name.lower(), "") or default
    except Exception:
        return default


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wa", description=__doc__.split("\n")[0])
    p.add_argument("--phone-number-id", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send-text")
    s.add_argument("--to", required=True)
    s.add_argument("--text", required=True)
    s = sub.add_parser("send-template")
    s.add_argument("--to", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--language", default="es")
    s.add_argument("--param", action="append", default=[])
    s = sub.add_parser("request-code")
    s.add_argument("--method", required=True, choices=["SMS", "VOICE", "sms", "voice"])
    s.add_argument("--language", default="es")
    s = sub.add_parser("verify-code")
    s.add_argument("--code", required=True)
    s = sub.add_parser("register")
    s.add_argument("--pin", required=True)
    sub.add_parser("calling-status")
    s = sub.add_parser("calling-enable")
    s.add_argument("--sip-host", required=True)
    s.add_argument("--sip-port", type=int, default=5061)
    sub.add_parser("calling-disable")
    sub.add_parser("sip-password")
    return p


# Llamadas de WhatsApp por SIP (docs/WHATSAPP_PLAN.md, fase 5): Meta -> TLS -> Asterisk.
# PCMA para que Asterisk no transcodifique (Anura y LiveKit van en A-law); SDES porque
# Asterisk lo hace sin ICE ni DTLS.
def _calling_enabled(host: str, port: int) -> dict:
    return {
        "status": "ENABLED",
        "call_icon_visibility": "DEFAULT",
        "srtp_key_exchange_protocol": "SDES",
        "audio": {"additional_codecs": ["PCMA"]},
        "sip": {"status": "ENABLED", "servers": [{"hostname": host, "port": port}]},
    }


# Con el cliente de la app (sin metodos propios: el contenedor de `app` solo monta scripts/).
async def _get_settings(client: GraphClient, pid: str, sip_credentials: bool = False) -> dict:
    params = {"include_sip_credentials": "true"} if sip_credentials else None
    return await client._request("GET", client._url(pid, "settings"), params=params)


async def _set_calling(client: GraphClient, pid: str, calling: dict) -> dict:
    return await client._request("POST", client._url(pid, "settings"), json={"calling": calling})


def _sip_password(settings: dict) -> str:
    servers = ((settings.get("calling") or {}).get("sip") or {}).get("servers") or []
    return next((s.get("sip_user_password") for s in servers if s.get("sip_user_password")), "")


async def _run(args, client: GraphClient, pid: str) -> dict:
    if args.cmd == "send-text":
        return await client.send_text(pid, args.to, args.text)
    if args.cmd == "send-template":
        return await client.send_template(pid, args.to, args.name, args.language, args.param)
    if args.cmd == "request-code":
        return await client.request_code(pid, args.method, args.language)
    if args.cmd == "verify-code":
        return await client.verify_code(pid, args.code)
    if args.cmd == "calling-status":
        return await _get_settings(client, pid)
    if args.cmd == "calling-enable":
        await _set_calling(client, pid, _calling_enabled(args.sip_host, args.sip_port))
        return await _get_settings(client, pid)
    if args.cmd == "calling-disable":
        # SIP primero en DISABLED: es lo que borra la config de servidores en Meta.
        await _set_calling(client, pid, {"status": "DISABLED", "sip": {"status": "DISABLED"}})
        return await _get_settings(client, pid)
    if args.cmd == "sip-password":
        return {"password": _sip_password(await _get_settings(client, pid, sip_credentials=True))}
    return await client.register(pid, args.pin)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    token = _setting("WA_ACCESS_TOKEN")
    pid = args.phone_number_id or _setting("WA_PHONE_NUMBER_ID")
    if not token:
        print("Falta WA_ACCESS_TOKEN", file=sys.stderr)
        return 2
    if not pid:
        print("Falta el phone_number_id (--phone-number-id o WA_PHONE_NUMBER_ID)", file=sys.stderr)
        return 2
    client = GraphClient(token, _setting("WA_GRAPH_VERSION", "v25.0"))

    async def go():
        try:
            return await _run(args, client, pid)
        finally:
            await client.aclose()

    try:
        out = asyncio.run(go())
    except (GraphError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.cmd == "sip-password":
        if not out["password"]:
            print("Meta no devolvio sip_user_password (¿SIP sin habilitar?)", file=sys.stderr)
            return 1
        print(out["password"])
        return 0
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
