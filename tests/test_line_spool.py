"""Grabacion completa por numero (docs/features/EQUIPO_TELEFONIA.md): record_full_call en la API y el marcador
del spool que mira Asterisk (app/services/line_spool.py)."""
import datetime

import pytest

from app.config import settings
from app.models import PhoneNumber
from app.services import line_spool

from .test_api import V1, admin, client_user, make_client  # noqa: F401  (admin: fixture)
from .test_direct_calls import DID, setup


@pytest.fixture
def spool(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path)
    return tmp_path / "line-spool" / "numbers"


def marker(spool):
    return spool / DID


def test_patch_on_and_off_writes_and_removes_the_marker(api, admin, spool):
    c, n, ana, _ = setup(api, admin)
    url = f"{V1}/phone-numbers/{n['id']}"
    assert n["record_full_call"] is False and not marker(spool).exists()
    r = ana.patch(url, json={"record_full_call": True})
    assert r.status_code == 200, r.text
    assert r.json()["record_full_call"] is True and marker(spool).exists()
    assert ana.get(f"{V1}/phone-numbers").json()[0]["record_full_call"] is True
    # Otro campo no la toca; apagarla borra el marcador.
    assert ana.patch(url, json={"label": "Ventas"}).json()["record_full_call"] is True and marker(spool).exists()
    assert ana.patch(url, json={"record_full_call": False}).json()["record_full_call"] is False
    assert not marker(spool).exists()


def test_validation_and_other_client(api, admin, spool):
    c, n, ana, _ = setup(api, admin)
    url = f"{V1}/phone-numbers/{n['id']}"
    assert ana.patch(url, json={"record_full_call": None}).status_code == 422
    assert ana.patch(url, json={"record_full_call": "si"}).status_code == 422
    other = client_user(api, admin, make_client(admin, slug="otro", direct_calls=True), email="otra@acme.com")
    assert other.patch(url, json={"record_full_call": True}).status_code == 404
    assert not marker(spool).exists()
    # Un libre no se puede (solo el admin lo ve) y no deja marcador.
    free = admin.post(f"{V1}/phone-numbers", json={"e164": "+541152630899"}).json()
    r = admin.patch(f"{V1}/phone-numbers/{free['id']}", json={"record_full_call": True})
    assert r.status_code == 422 and r.json()["code"] == "number_unassigned"
    assert not (spool / "+541152630899").exists()


def test_release_and_reassign_drop_the_marker_and_the_option(api, admin, spool):
    c, n, ana, _ = setup(api, admin)
    ana.patch(f"{V1}/phone-numbers/{n['id']}", json={"record_full_call": True})
    assert marker(spool).exists()
    out = admin.post(f"{V1}/phone-numbers/{n['id']}/release").json()
    assert out["record_full_call"] is False and not marker(spool).exists()
    # Asignado a otro cliente no hereda la opcion.
    c2 = make_client(admin, slug="otro", direct_calls=True)
    out = admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": c2["id"]}).json()
    assert out["record_full_call"] is False and not marker(spool).exists()


def test_delete_drops_a_stale_marker(api, admin, spool):
    free = admin.post(f"{V1}/phone-numbers", json={"e164": "+541152630899"}).json()
    spool.mkdir(parents=True)
    (spool / "+541152630899").touch()
    assert admin.delete(f"{V1}/phone-numbers/{free['id']}").status_code == 204
    assert not (spool / "+541152630899").exists()


def test_a_spool_that_cannot_be_written_does_not_break_the_patch(api, admin, spool, monkeypatch):
    c, n, ana, _ = setup(api, admin)

    def boom(e164):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(line_spool, "_put", boom)
    r = ana.patch(f"{V1}/phone-numbers/{n['id']}", json={"record_full_call": True})
    assert r.status_code == 200 and r.json()["record_full_call"] is True


def test_reconcile_follows_the_database(api, admin, spool):
    c, n, ana, _ = setup(api, admin)
    ana.patch(f"{V1}/phone-numbers/{n['id']}", json={"record_full_call": True})
    other = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541152630862"}).json()
    ana.patch(f"{V1}/phone-numbers/{other['id']}", json={"record_full_call": True})
    # Spool perdido, un marcador de un numero que ya no graba, y archivos que no son marcadores.
    marker(spool).unlink()
    (spool / "+541152630777").touch()
    (spool / "notas.txt").touch()
    with api.sessions() as s:
        assert line_spool.reconcile(s) == (1, 1)
        assert line_spool.reconcile(s) == (0, 0)
    assert sorted(p.name for p in spool.iterdir()) == [DID, "+541152630862", "notas.txt"]
    # Suspendido (el facturador no pasa por la API) deja de grabar; al volver, vuelve.
    with api.sessions() as s:
        num = s.query(PhoneNumber).filter_by(e164=DID).one()
        num.suspended_at = datetime.datetime(2026, 11, 11)
        s.commit()
        assert line_spool.reconcile(s) == (0, 1)
        num.suspended_at = None
        s.commit()
        assert line_spool.reconcile(s) == (1, 0)
    assert marker(spool).exists()


def test_reconcile_without_a_spool_directory_creates_nothing(api, admin, spool):
    c, n, ana, _ = setup(api, admin)
    with api.sessions() as s:
        assert line_spool.reconcile(s) == (0, 0)
    assert not spool.exists()
