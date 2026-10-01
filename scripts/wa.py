"""CLI de la Graph API de WhatsApp (docs/WHATSAPP_PLAN.md, fase 0).

  python -m scripts.wa send-text --to 54351... --text "hola" [--phone-number-id ID]
  python -m scripts.wa send-template --to ... --name NOMBRE [--language es] [--param X ...]
  python -m scripts.wa request-code --method SMS|VOICE [--language es]
  python -m scripts.wa verify-code --code 123456
  python -m scripts.wa register --pin 123456

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
    return p


async def _run(args, client: GraphClient, pid: str) -> dict:
    if args.cmd == "send-text":
        return await client.send_text(pid, args.to, args.text)
    if args.cmd == "send-template":
        return await client.send_template(pid, args.to, args.name, args.language, args.param)
    if args.cmd == "request-code":
        return await client.request_code(pid, args.method, args.language)
    if args.cmd == "verify-code":
        return await client.verify_code(pid, args.code)
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
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
