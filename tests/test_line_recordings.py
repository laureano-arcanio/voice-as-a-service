"""Grabacion completa (docs/features/EQUIPO_TELEFONIA.md): del spool de Asterisk a la conversacion
(app/services/line_recordings.py), el detalle, el endpoint y el header de las salientes."""
import math
import os
import struct
import time

import av
import pytest

from app.config import settings
from app.models import CallRow
from app.services import calls as call_service
from app.services import line_recordings
from app.voice.worker import full_call_headers

from .test_api import V1, admin, make_agent, make_client  # noqa: F401  (admin: fixture)

DID = "+541152630901"


@pytest.fixture
def rec_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path)
    for d in ("rec", "done", "numbers"):
        (tmp_path / "line-spool" / d).mkdir(parents=True)
    return tmp_path


def sln(path, seconds=1.0):
    """Crudo como el de MixMonitor: s16le 8 kHz estereo, tono distinto por canal, y un byte suelto al final."""
    n = int(8000 * seconds)
    path.write_bytes(b"".join(struct.pack("<hh", int(6000 * math.sin(2 * math.pi * 440 * i / 8000)),
                                          int(6000 * math.sin(2 * math.pi * 1000 * i / 8000))) for i in range(n))
                     + b"\x01")
    return path


def old(path, seconds):
    t = time.time() - seconds
    os.utime(path, (t, t))
    return path


def number(admin, client, agent, record=True):
    n = admin.post(f"{V1}/phone-numbers", json={"client_id": client["id"], "e164": DID,
                                                 "agent_id": agent["id"]}).json()
    if record:
        assert admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"record_full_call": True}).status_code == 200
    return n


def inbound(api, line_id):
    with api.sessions() as s:
        return call_service.start_inbound(s, api.engine, DID, "+5493515550000", line_id=line_id).conversation_id


def sweep(api):
    return line_recordings.sweep(api.sessions)


def test_inbound_is_linked_converted_and_served(api, admin, rec_dir):
    c = make_client(admin)
    agent = make_agent(admin, c)
    number(admin, c, agent)
    cid = inbound(api, "1731342342.17")
    with api.sessions() as s:
        assert s.get(CallRow, cid).line_id == "1731342342.17"
    src = sln(rec_dir / "line-spool" / "done" / "in-1731342342.17.sln", 2)
    # Un audio por mensaje en el mismo directorio: el detalle cuenta los WAV y aparte la grabacion completa.
    (rec_dir / cid).mkdir()
    (rec_dir / cid / "001.wav").write_bytes(b"RIFF....WAVEfmt ")
    assert admin.get(f"{V1}/calls/{cid}").json()["full_recording"] is False
    assert admin.get(f"{V1}/calls/{cid}/recording").status_code == 404

    assert sweep(api) == {"linked": 1}
    assert not src.exists()
    ogg = rec_dir / cid / "llamada.ogg"
    with av.open(str(ogg)) as f:
        stream = f.streams.audio[0]
        assert stream.codec_context.name == "opus" and stream.channels == 2
        assert 1.9 < f.duration / av.time_base < 2.1
    detail = admin.get(f"{V1}/calls/{cid}").json()
    assert detail["full_recording"] is True and detail["recordings"] == [1]
    r = admin.get(f"{V1}/calls/{cid}/recording")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/ogg" and r.content == ogg.read_bytes()
    assert "attachment" in r.headers["content-disposition"]

    # Otro cliente no la ve; el admin en "ver como cliente" si.
    other = make_client(admin, "otro")
    key = admin.post(f"{V1}/clients/{other['id']}/api-keys", json={"name": "k"}).json()["key"]
    assert api.client.get(f"{V1}/calls/{cid}/recording",
                          headers={"Authorization": f"Bearer {key}"}).status_code == 404
    assert admin.get(f"{V1}/calls/{cid}/recording", headers={"X-Atentina-Client": c["id"]}).status_code == 200
    assert api.client.get(f"{V1}/calls/{cid}/recording").status_code == 401

    # Se borra con la conversacion.
    with api.sessions() as s:
        s.query(CallRow).update({"status": "finalizada"})
        s.commit()
    assert admin.delete(f"{V1}/calls/{cid}").status_code == 204
    assert not ogg.exists()


def test_option_off_empty_and_orphans_are_dropped(api, admin, rec_dir):
    c = make_client(admin)
    agent = make_agent(admin, c)
    n = number(admin, c, agent)
    cid = inbound(api, "1731342342.18")
    done = rec_dir / "line-spool" / "done"
    # La opcion se apago despues de la llamada: la app vuelve a mirarla y borra.
    admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"record_full_call": False})
    off = sln(done / "in-1731342342.18.sln")
    empty = done / "in-1731342342.19.sln"
    empty.write_bytes(b"")             # no atendio
    fresh = sln(done / "in-1731342342.20.sln")      # sin llamada todavia: espera
    orphan = old(sln(done / "in-1731342342.21.sln"), 600)
    assert sweep(api) == {"disabled": 1, "empty": 1, "wait": 1, "no_call": 1}
    assert not off.exists() and not empty.exists() and not orphan.exists() and fresh.exists()
    assert not (rec_dir / cid / "llamada.ogg").exists()


def test_outbound_by_conversation_and_deleted_conversation(api, admin, rec_dir):
    c = make_client(admin)
    agent = make_agent(admin, c)
    number(admin, c, agent)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551234"}).json()
    cid = out["conversation_id"]
    meta = api.dispatched[-1]
    assert meta["record_full_call"] is True
    assert full_call_headers(meta, cid) == {"X-Atentina-Rec": cid}
    done = rec_dir / "line-spool" / "done"
    sln(done / f"out-{cid.replace('-', '')}.sln")
    assert sweep(api) == {"linked": 1}
    assert (rec_dir / cid / "llamada.ogg").is_file()

    # Conversacion borrada antes de procesar: queda sin llamada y se borra pasado el margen.
    gone = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551235"}).json()
    with api.sessions() as s:
        s.query(CallRow).update({"status": "finalizada"})
        s.commit()
    assert admin.delete(f"{V1}/calls/{gone['conversation_id']}").status_code == 204
    path = old(sln(done / f"out-{gone['conversation_id'].replace('-', '')}.sln"), 600)
    assert sweep(api) == {"no_call": 1} and not path.exists()
    assert not (rec_dir / gone["conversation_id"]).exists()


def test_stale_rec_is_processed_and_live_rec_is_left(api, admin, rec_dir, monkeypatch):
    monkeypatch.setattr(settings, "call_max_duration_seconds", 60)
    c = make_client(admin)
    agent = make_agent(admin, c)
    number(admin, c, agent)
    cid = inbound(api, "1731342342.30")
    rec = rec_dir / "line-spool" / "rec"
    live = sln(rec / "in-1731342342.31.sln")                 # grabando: no se toca
    crashed = old(sln(rec / "in-1731342342.30.sln"), 60 + 601)   # Asterisk se cayo a mitad: audio valido
    assert sweep(api) == {"linked": 1}
    assert live.exists() and not crashed.exists() and (rec_dir / cid / "llamada.ogg").is_file()


def test_no_header_without_the_option(api, admin, rec_dir):
    c = make_client(admin)
    agent = make_agent(admin, c)
    number(admin, c, agent, record=False)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551234"}).json()
    meta = api.dispatched[-1]
    assert meta["record_full_call"] is False
    assert full_call_headers(meta, out["conversation_id"]) == {}
    # Llamada de prueba (sin numero de origen): nunca.
    admin.post(f"{V1}/calls", json={"agent_id": agent["id"]})
    assert api.dispatched[-1]["record_full_call"] is False
