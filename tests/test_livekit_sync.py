"""Numeros de los trunks SIP en caliente al cargar o borrar numeros (services/livekit.py)."""
import asyncio
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services import livekit


class FakeSip:
    def __init__(self, inbound=("anura-asterisk-inbound",), outbound=("anura-asterisk-outbound",)):
        self.inbound = [SimpleNamespace(sip_trunk_id=f"IN_{n}", name=n) for n in inbound]
        self.outbound = [SimpleNamespace(sip_trunk_id=f"OUT_{n}", name=n) for n in outbound]
        self.updates = []

    async def list_inbound_trunk(self, _):
        return SimpleNamespace(items=self.inbound)

    async def list_outbound_trunk(self, _):
        return SimpleNamespace(items=self.outbound)

    async def update_inbound_trunk_fields(self, trunk_id, *, numbers):
        self.updates.append((trunk_id, list(numbers.add), list(numbers.remove)))

    async def update_outbound_trunk_fields(self, trunk_id, *, numbers):
        self.updates.append((trunk_id, list(numbers.add), list(numbers.remove)))


@pytest.fixture
def fake_lk(monkeypatch):
    sip = FakeSip()

    class FakeAPI:
        def __init__(self, **_):
            self.sip = sip

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

    monkeypatch.setattr(settings, "livekit_sip_sync", True)
    monkeypatch.setattr(settings, "livekit_url", "ws://livekit.test")
    monkeypatch.setattr(livekit.api, "LiveKitAPI", FakeAPI)
    return sip


def test_agrega_y_quita_en_los_dos_trunks(fake_lk):
    asyncio.run(livekit.sync_trunk_numbers(add=["+548102200605"], remove=["+541100000000"]))
    assert fake_lk.updates == [
        ("IN_anura-asterisk-inbound", ["+548102200605"], ["+541100000000"]),
        ("OUT_anura-asterisk-outbound", ["+548102200605"], ["+541100000000"]),
    ]


def test_sin_trunk_no_falla(fake_lk):
    fake_lk.inbound, fake_lk.outbound = [], []
    asyncio.run(livekit.sync_trunk_numbers(add=["+548102200605"]))
    assert fake_lk.updates == []


def test_apagado_o_sin_cambios_no_llama(fake_lk, monkeypatch):
    asyncio.run(livekit.sync_trunk_numbers())
    monkeypatch.setattr(settings, "livekit_sip_sync", False)
    asyncio.run(livekit.sync_trunk_numbers(add=["+548102200605"]))
    assert fake_lk.updates == []
