"""scripts/livekit_sip_setup.py: --if-missing solo escribe si falta algún objeto; el resto, actualiza por ID."""
import asyncio
from types import SimpleNamespace as NS

import pytest

from scripts import livekit_sip_setup as setup


class FakeSip:
    def __init__(self, inbound=True, dispatch=True, outbound=True):
        self.inbound = [NS(name=setup.INBOUND_NAME, sip_trunk_id="ST_in")] if inbound else []
        self.rules = [NS(name=setup.DISPATCH_NAME, sip_dispatch_rule_id="SDR_1")] if dispatch else []
        self.outbound = [NS(name=setup.OUTBOUND_NAME, sip_trunk_id="ST_out")] if outbound else []
        self.writes = []

    async def list_inbound_trunk(self, _):
        return NS(items=self.inbound)

    async def list_dispatch_rule(self, _):
        return NS(items=self.rules)

    async def list_outbound_trunk(self, _):
        return NS(items=self.outbound)

    def _write(self, kind, result):
        async def call(*_args):
            self.writes.append(kind)
            return result
        return call

    def __getattr__(self, name):
        if name.startswith(("create_", "update_")):
            obj = NS(sip_trunk_id=f"ST_{name}", sip_dispatch_rule_id=f"SDR_{name}")
            return self._write(name, obj)
        raise AttributeError(name)


class FakeLK:
    def __init__(self, sip):
        self.sip = sip

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


@pytest.fixture
def env(monkeypatch):
    for k, v in {"ANURA_DID": "1100000000", "LIVEKIT_SIP_PASSWORD": "x", "LIVEKIT_AGENT_NAME": "a",
                 "LIVEKIT_URL": "ws://lk:7880", "LIVEKIT_API_KEY": "k", "LIVEKIT_API_SECRET": "s",
                 "LIVEKIT_SIP_OUTBOUND_ADDRESS": "127.0.0.1:5080"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(setup, "wait_for_livekit", lambda _url: None)
    monkeypatch.setattr(setup, "client_numbers", lambda: [])

    def use(sip):
        monkeypatch.setattr(setup.api, "LiveKitAPI", lambda **_: FakeLK(sip))
        return sip
    return use


def test_if_missing_con_todo_no_escribe_ni_imprime(env, capsys):
    sip = env(FakeSip())
    asyncio.run(setup.main(if_missing=True))
    assert sip.writes == []
    assert capsys.readouterr().out == ""


def test_if_missing_sin_dispatch_crea_solo_lo_que_falta(env, capsys):
    sip = env(FakeSip(dispatch=False))
    asyncio.run(setup.main(if_missing=True))
    assert sip.writes == ["update_inbound_trunk", "create_dispatch_rule", "update_outbound_trunk"]
    assert "(creado)" in capsys.readouterr().out


def test_sin_flag_actualiza_por_id_sin_recrear(env):
    sip = env(FakeSip())
    asyncio.run(setup.main())
    assert sip.writes == ["update_inbound_trunk", "update_dispatch_rule", "update_outbound_trunk"]
