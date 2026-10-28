# ruff: noqa: F811  (fixtures importadas de otros tests)
"""Terminos y condiciones (docs/features/LEGAL.md): versiones, aceptacion en el registro y en el panel, y botones de
arrepentimiento y de baja."""
import pathlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import legal
from app.api import deps
from app.legal import sync
from app.models import ConsumerRequest, LegalAcceptance, User
from app.services import legal as legal_service
from app.services import signup

from .test_api import V1, admin  # noqa: F401  (admin: fixture)
from .test_billing import (  # noqa: F401  (fixtures)
    SIGNUP,
    activate,
    landing,
    plans,
    register,
)
from .test_mail import (  # noqa: F401  (outbox: fixture)
    create_client_with_owner,
    outbox,
    setup_token,
)

# Hash de cada version publicada: una version publicada no se edita (la prueba de lo aceptado es su hash). Un
# cambio es un archivo nuevo, y se agrega aca.
PUBLISHED = {
    ("terms", "2026-10-01"): "466d608aa9d7f106b4bf4a830019323b5b1ed4bb66547213e034264df6b75a72",
    ("terms", "2026-10-25"): "fef573ead36cf3d65065ed7d62b43334c4abbdb777edfe1d203184ca46f43d51",
    ("privacy", "2026-10-25"): "1660a856675221692839dbefa7f2cd7c3efd0b3d643c4d9e76c8d61a1ec5c3dc",
    # Llamadas directas (docs/features/EQUIPO_TELEFONIA.md): grabacion siempre, No Llame, encargado del tratamiento.
    # Entrantes a 0800 (x2) y 0810 (x1,5) en los minutos del plan (app/services/quota.py).
    ("terms", "2026-10-28"): "b3b7680221daccb5d4557861033f6e51722410cf04e9238f9901e6c2f2f946dc",
    ("privacy", "2026-10-28"): "563d800a0b95561d236bfff2a7a49deb7c442069c1bd16c7376056111683a213",
}


def test_published_versions_are_not_edited():
    for doc in legal.DOCS:
        for v in legal.versions(doc.id):
            assert PUBLISHED.get((doc.id, v.version)) == v.sha256, (
                f"{doc.slug}/{v.version}.md cambio o es nueva: una version publicada no se edita (agregar una nueva "
                "y su hash en PUBLISHED)")


def test_landing_copy_is_up_to_date():
    root = pathlib.Path(__file__).parents[1] / sync.LANDING_DIR
    for rel, content in sync.render().items():
        assert (root / rel).read_text() == content, f"{sync.LANDING_DIR}/{rel} desactualizado: make legal-sync"


def test_versions_are_dates_and_links_are_permanent():
    for v in legal.current_all():
        assert len(v.version) == 10 and v.version[4] == v.version[7] == "-"
        assert v.url.endswith(f"/{v.doc.slug}/{v.version}")


# ---------- registro ----------

def test_signup_without_checkbox_is_rejected(landing):
    r = register(landing, accept_terms=False)
    assert r.status_code == 422 and r.json()["code"] == "terms_required"
    with landing.sessions() as s:
        assert s.scalar(select(User).where(User.email == "rosa@example.com")) is None


def test_signup_with_old_version_is_rejected(landing):
    r = register(landing, terms_version="2026-10-01")
    assert r.status_code == 409 and r.json()["code"] == "terms_outdated"


def test_signup_records_acceptance_and_mails_it(landing):
    r = landing.client.post(f"{V1}/demo/signup", json=SIGNUP, headers={"user-agent": "Prueba/1.0"})
    assert r.status_code == 201, r.text
    with landing.sessions() as s:
        rows = list(s.scalars(select(LegalAcceptance).order_by(LegalAcceptance.document)))
    assert {(a.document, a.version, a.sha256) for a in rows} == {
        (v.doc.id, v.version, v.sha256) for v in legal.current_all()}
    assert all(a.channel == "signup" and a.email == "rosa@example.com" and a.client_name == "Panadería Doña Rosa"
               and a.user_agent == "Prueba/1.0" and a.ip and "Leí y acepto" in a.statement for a in rows)
    mail = next(m for m in landing.outbox if m.to == "rosa@example.com")
    for v in legal.current_all():
        assert v.url in mail.text and v.sha256 in mail.text


def test_signup_user_has_nothing_pending(landing):
    c = activate(landing, register(landing))
    assert c.get(f"{V1}/auth/me").json()["legal_pending"] == []


def test_acceptance_survives_purge_of_unactivated_signup(landing):
    import datetime

    from app.db import utcnow

    assert register(landing).status_code == 201
    with landing.sessions() as s:
        assert signup.purge_unactivated(s, utcnow() + datetime.timedelta(days=30)) == 1
        s.commit()
        assert len(list(s.scalars(select(LegalAcceptance)))) == 2


# ---------- panel ----------

@pytest.fixture
def invited(admin, outbox):
    """Usuario de cliente creado por un admin (no paso por la casilla del registro), con sesion."""
    create_client_with_owner(admin, slug="acme")
    token = setup_token(outbox[-1])
    c = TestClient(admin.app)
    assert c.post(f"{V1}/auth/password-setup", json={"token": token, "password": "acme-password-1"}).status_code == 200
    return c


def _accept_body():
    return {"terms_version": legal.current("terms").version, "privacy_version": legal.current("privacy").version}


def test_invited_user_must_accept_in_panel(invited, outbox):
    pending = invited.get(f"{V1}/auth/me").json()["legal_pending"]
    assert {p["document"] for p in pending} == {"terms", "privacy"}
    r = invited.post(f"{V1}/auth/me/legal", json=_accept_body())
    assert r.status_code == 200 and r.json()["legal_pending"] == []
    assert outbox[-1].subject == "Aceptaste las condiciones de Atentina"
    # Aceptar de nuevo no duplica filas ni manda otro mail.
    sent = len(outbox)
    assert invited.post(f"{V1}/auth/me/legal", json=_accept_body()).status_code == 200
    assert len(outbox) == sent


def test_panel_acceptance_needs_current_versions(invited):
    r = invited.post(f"{V1}/auth/me/legal", json={**_accept_body(), "terms_version": "2026-10-01"})
    assert r.status_code == 409 and r.json()["code"] == "terms_outdated"


def test_new_version_is_pending_again(invited, monkeypatch):
    assert invited.post(f"{V1}/auth/me/legal", json=_accept_body()).status_code == 200
    original = legal.versions
    old = original("terms")
    newer = legal.Version(old[-1].doc, "2099-01-01", "f" * 64, "texto nuevo")
    monkeypatch.setattr(legal, "versions", lambda doc_id: (*old, newer) if doc_id == "terms" else original(doc_id))
    pending = invited.get(f"{V1}/auth/me").json()["legal_pending"]
    assert [(p["document"], p["version"]) for p in pending] == [("terms", "2099-01-01")]


def test_admin_has_nothing_pending(admin):
    assert admin.get(f"{V1}/auth/me").json()["legal_pending"] == []


# ---------- botones de arrepentimiento y de baja ----------

@pytest.fixture
def buttons(landing, monkeypatch):
    async def fake_verify(token, ip):
        return landing.turnstile_ok

    monkeypatch.setattr(legal_service, "verify_turnstile", fake_verify)
    legal_service.limiter.reset()
    return landing


def _request(api, **extra):
    body = {"kind": "cancellation", "name": "Rosa Gómez", "email": "Rosa@Example.com", "company": "Doña Rosa",
            "turnstile_token": "ok", **extra}
    return api.client.post(f"{V1}/demo/consumer-requests", json=body)


def test_consumer_request_sends_code_without_account(buttons):
    r = _request(buttons, kind="revocation")
    assert r.status_code == 201, r.text
    code = r.json()["code"]
    assert code.startswith("ARR-") and len(code) == 12
    mail = next(m for m in buttons.outbox if m.to == "rosa@example.com")
    assert code in mail.subject and code in mail.text
    with buttons.sessions() as s:
        row = s.scalar(select(ConsumerRequest))
    assert (row.kind, row.status, row.email_status, row.client_id) == ("revocation", "open", "sent", None)


def test_consumer_request_links_existing_client(buttons):
    assert register(buttons).status_code == 201
    assert _request(buttons).json()["code"].startswith("BAJ-")
    with buttons.sessions() as s:
        row = s.scalar(select(ConsumerRequest))
        user = s.scalar(select(User).where(User.email == "rosa@example.com"))
    assert row.client_id == user.client_id


def test_consumer_request_needs_turnstile_and_has_ip_limit(buttons):
    buttons.turnstile_ok = False
    assert _request(buttons).status_code == 403
    buttons.turnstile_ok = True
    assert all(_request(buttons).status_code == 201 for _ in range(5))
    assert _request(buttons).status_code == 429


def test_admin_lists_and_resolves_requests(buttons, admin):
    _request(buttons)
    rows = admin.get(f"{V1}/consumer-requests?status=open").json()
    assert len(rows) == 1
    r = admin.patch(f"{V1}/consumer-requests/{rows[0]['id']}",
                           json={"status": "done", "resolution": "Plan cancelado en MP"})
    assert r.status_code == 200 and r.json()["resolved_at"] and r.json()["status"] == "done"
    assert admin.get(f"{V1}/consumer-requests?status=open").json() == []


def test_client_cannot_list_requests(buttons):
    c = activate(buttons, register(buttons))
    assert c.get(f"{V1}/consumer-requests").status_code == 403


def test_public_legal_versions(api):
    r = api.client.get(f"{V1}/demo/legal")
    assert r.status_code == 200
    assert {(v["document"], v["version"]) for v in r.json()} == {(v.doc.id, v.version) for v in legal.current_all()}


def test_admin_sees_every_version_with_text_and_acceptances(landing, admin):
    assert register(landing).status_code == 201
    rows = admin.get(f"{V1}/legal/versions").json()
    assert [(r["document"], r["version"]) for r in rows] == [
        (d.id, v.version) for d in legal.DOCS for v in reversed(legal.versions(d.id))]
    current = {v.doc.id: v.version for v in legal.current_all()}
    for r in rows:
        assert r["current"] == (r["version"] == current[r["document"]])
        assert r["acceptances"] == (1 if r["current"] else 0)
    r = admin.get(f"{V1}/legal/versions/terms/2026-10-01")
    assert r.status_code == 200
    old = legal.versions("terms")[0]
    assert (r.json()["text"], r.json()["sha256"], r.json()["current"]) == (old.text, old.sha256, False)
    assert admin.get(f"{V1}/legal/versions/terms/1999-01-01").json()["code"] == "legal_version_not_found"


def test_client_cannot_list_legal_versions(landing):
    c = activate(landing, register(landing))
    assert c.get(f"{V1}/legal/versions").status_code == 403


def test_panel_accepts_only_the_pending_document(invited, monkeypatch):
    assert invited.post(f"{V1}/auth/me/legal", json=_accept_body()).status_code == 200
    original = legal.versions
    old = original("terms")
    newer = legal.Version(old[-1].doc, "2099-01-01", "f" * 64, "texto nuevo")
    monkeypatch.setattr(legal, "versions", lambda doc_id: (*old, newer) if doc_id == "terms" else original(doc_id))
    r = invited.post(f"{V1}/auth/me/legal", json={"terms_version": "2099-01-01"})
    assert r.status_code == 200 and r.json()["legal_pending"] == []
    with invited.app.dependency_overrides[deps.get_db]().__next__() as s:
        last = s.scalars(select(LegalAcceptance).order_by(LegalAcceptance.created_at.desc())).first()
    assert (last.document, last.version, last.channel) == ("terms", "2099-01-01", "panel")
    assert "Condiciones del servicio 2099-01-01" in last.statement
