"""Acceso al panel desde Tu equipo y escritura solo de Admin (docs/features/EQUIPO_TELEFONIA.md)."""
import pytest
from sqlalchemy import select

from app.config import settings
from app.models import User
from app.services.security import create_password_setup_token, decode_password_setup_token

from .test_api import V1, admin, client_user, make_client  # noqa: F401  (admin: fixture)
from .test_oauth import setup  # noqa: F401  (setup: fixture)


def new_member(client, cid, **body):
    r = client.post(f"{V1}/team", params={"client_id": cid}, json={"name": "Sara", **body})
    assert r.status_code == 201, r.text
    return r.json()


def team(client, cid):
    return client.get(f"{V1}/team", params={"client_id": cid}).json()


def person_of(user, cid):
    me = user.get(f"{V1}/auth/me").json()["id"]
    return next(p for p in user.get(f"{V1}/team").json() if p["user_id"] == me)


def test_giving_access_creates_the_user_and_sends_the_invite(api, admin):
    c = make_client(admin)
    owner = client_user(api, admin, c)      # Admin con sesión del panel
    m = new_member(owner, c["id"], email="Sara@Acme.com", role="user")
    assert (m["email"], m["role"], m["panel_access"], m["last_login_at"]) == ("sara@acme.com", "user", True, None)
    assert m["invite"]["email"] == "sara@acme.com" and m["invite"]["status"] == "disabled"   # sin Resend
    with api.sessions() as s:
        user = s.get(User, m["user_id"])
        assert (user.email, user.role, user.client_role, user.client_id) == ("sara@acme.com", "client", "user",
                                                                             c["id"])
        token, _ = create_password_setup_token(user.id, user.password_hash)
        assert decode_password_setup_token(token)["sub"] == user.id
    # Sin rol indicado, es Usuario; con el teléfono, la misma persona sirve para derivar.
    assert new_member(owner, c["id"], name="Juan", phone="3516775617")["role"] is None
    assert new_member(owner, c["id"], name="Ana", email="ana2@acme.com")["role"] == "user"


def test_email_taken_client_id_and_user_id_in_the_body(api, admin):
    c, other = make_client(admin, slug="acme"), make_client(admin, slug="otro")
    owner = client_user(api, admin, c)
    client_user(api, admin, other, email="otro@otro.com")
    r = owner.post(f"{V1}/team", params={"client_id": c["id"]},
                   json={"name": "X", "email": "otro@otro.com"})
    assert (r.status_code, r.json()["code"]) == (409, "email_taken")
    r = owner.post(f"{V1}/team", params={"client_id": c["id"]}, json={"name": "X", "email": "admin@example.com"})
    assert (r.status_code, r.json()["code"]) == (409, "email_taken")
    # El cliente sale del query para un admin; ni client_id ni el viejo user_id van en el cuerpo.
    base = {"name": "X", "email": "x@acme.com"}
    for extra in ({"client_id": c["id"]}, {"user_id": "nope"}):
        assert owner.post(f"{V1}/team", params={"client_id": c["id"]}, json={**base, **extra}).status_code == 422


def test_panel_operations_need_the_panel_session(api, admin):
    c = make_client(admin)
    owner = client_user(api, admin, c)
    key = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "crm"}).json()["key"]
    hdr = {"Authorization": f"Bearer {key}"}
    # Una key (Admin del cliente) sigue sumando personas sin acceso.
    r = api.client.post(f"{V1}/team", params={"client_id": c["id"]}, json={"name": "Juan", "phone": "3516775617"},
                        headers=hdr)
    assert r.status_code == 201, r.text
    person = r.json()
    # Con acceso, rol, invitación o borrar a una persona con usuario: sesión del panel.
    r = api.client.post(f"{V1}/team", params={"client_id": c["id"]}, json={"name": "X", "email": "x@acme.com"},
                        headers=hdr)
    assert (r.status_code, r.json()["code"]) == (403, "panel_user_required")
    assert api.client.patch(f"{V1}/team/{person['id']}", json={"email": "y@acme.com"},
                            headers=hdr).status_code == 403
    assert api.client.patch(f"{V1}/team/{person['id']}", json={"role": "admin"}, headers=hdr).status_code == 403
    assert api.client.post(f"{V1}/team/{person['id']}/invite", headers=hdr).status_code == 403
    with_email = new_member(owner, c["id"], email="sara@acme.com")
    r = api.client.delete(f"{V1}/team/{with_email['id']}", headers=hdr)
    assert (r.status_code, r.json()["code"]) == (403, "panel_user_required")
    # Sin usuario, la key la borra y no se pide el panel.
    assert api.client.delete(f"{V1}/team/{person['id']}", headers=hdr).status_code == 204


def test_a_user_cannot_give_access_or_write_the_team(api, admin):
    c = make_client(admin, direct_calls=True)
    client_user(api, admin, c)                                  # Admin
    user = client_user(api, admin, c, email="operador@acme.com", client_role="user")
    r = user.post(f"{V1}/team", json={"name": "X", "email": "x@acme.com"})
    assert (r.status_code, r.json()["code"]) == (403, "client_admin_required")
    assert user.post(f"{V1}/team", json={"name": "X", "phone": "3516775617"}).status_code == 403
    assert user.patch(f"{V1}/handoff-areas/nope", json={"name": "X"}).status_code == 403
    assert user.delete(f"{V1}/handoff-areas/nope").status_code == 403
    assert user.post(f"{V1}/handoff-areas", json={"name": "Ventas"}).status_code == 403
    # Ve el equipo, las áreas y la presencia, y marca su propia disponibilidad.
    assert user.get(f"{V1}/team").status_code == 200
    assert user.get(f"{V1}/handoff-areas").status_code == 200
    assert user.get(f"{V1}/team/presence").status_code == 200
    assert user.put(f"{V1}/me/presence", json={"available": True}).status_code == 200


def test_change_access_role_and_resend(api, admin):
    c = make_client(admin)
    owner = client_user(api, admin, c)
    m = new_member(owner, c["id"], name="Sara", phone="3516775617")   # sin acceso
    # Dar acceso después: email + rol; la persona sigue siendo la misma.
    r = owner.patch(f"{V1}/team/{m['id']}", json={"email": "sara@acme.com", "role": "admin"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert (out["id"], out["email"], out["role"], out["panel_access"]) == (m["id"], "sara@acme.com", "admin", True)
    assert out["invite"]["status"] == "disabled"
    # El email ya no se cambia desde el equipo; sí el rol y el acceso.
    r = owner.patch(f"{V1}/team/{m['id']}", json={"email": "otro@acme.com"})
    assert (r.status_code, r.json()["code"]) == (422, "email_readonly")
    assert owner.patch(f"{V1}/team/{m['id']}", json={"role": "user"}).json()["role"] == "user"
    assert owner.patch(f"{V1}/team/{m['id']}", json={"panel_access": False}).json()["panel_access"] is False
    assert owner.patch(f"{V1}/team/{m['id']}", json={"panel_access": True}).json()["panel_access"] is True
    # Reenviar la invitación: solo con acceso activo; una persona sin usuario da 422.
    assert owner.post(f"{V1}/team/{m['id']}/invite").json()["status"] == "disabled"
    other = new_member(owner, c["id"], name="Luis", phone="3512222222")
    r = owner.post(f"{V1}/team/{other['id']}/invite")
    assert (r.status_code, r.json()["code"]) == (422, "invalid_user")
    assert owner.patch(f"{V1}/team/{other['id']}", json={"role": "admin"}).status_code == 422


def test_removing_access_closes_the_session(api, admin):
    c = make_client(admin)
    admin_user = client_user(api, admin, c)
    user = client_user(api, admin, c, email="operador@acme.com", client_role="user")
    uid = user.get(f"{V1}/auth/me").json()["id"]
    person = person_of(user, c["id"])
    r = admin_user.patch(f"{V1}/team/{person['id']}", json={"panel_access": False})
    assert r.status_code == 200 and r.json()["panel_access"] is False
    assert user.get(f"{V1}/auth/me").status_code == 401
    assert admin_user.patch(f"{V1}/team/{person['id']}", json={"panel_access": True}).status_code == 200
    assert api.login("operador@acme.com", "cliente-password-1").get(f"{V1}/auth/me").json()["id"] == uid


def test_nobody_removes_their_own_access_or_member(api, admin):
    c = make_client(admin)
    owner = client_user(api, admin, c)
    person = person_of(owner, c["id"])
    r = owner.patch(f"{V1}/team/{person['id']}", json={"panel_access": False})
    assert (r.status_code, r.json()["code"]) == (422, "own_access")
    r = owner.delete(f"{V1}/team/{person['id']}")
    assert (r.status_code, r.json()["code"]) == (422, "own_member")
    # Bajarse de rol sí, si queda otro Admin.
    other = new_member(owner, c["id"], name="Jefe", email="jefe@acme.com", role="admin")
    assert owner.patch(f"{V1}/team/{person['id']}", json={"role": "user"}).json()["role"] == "user"
    # El último Admin no se baja ni se desactiva, desde el equipo ni desde Usuarios.
    r = admin.patch(f"{V1}/team/{other['id']}", json={"role": "user"})
    assert (r.status_code, r.json()["code"]) == (409, "last_admin")
    r = admin.patch(f"{V1}/team/{other['id']}", json={"panel_access": False})
    assert (r.status_code, r.json()["code"]) == (409, "last_admin")
    r = admin.delete(f"{V1}/team/{other['id']}")
    assert (r.status_code, r.json()["code"]) == (409, "last_admin")


def test_delete_with_user_deletes_the_user_too(api, admin):
    c = make_client(admin)
    client_user(api, admin, c)
    m = new_member(admin, c["id"], name="Sara", email="sara@acme.com")
    assert admin.delete(f"{V1}/team/{m['id']}").status_code == 204
    assert all(p["user_id"] != m["user_id"] for p in team(admin, c["id"]))
    with api.sessions() as s:
        assert s.scalar(select(User).where(User.email == "sara@acme.com")) is None


def test_another_client_cannot_touch_it(api, admin):
    a, b = make_client(admin, slug="acme"), make_client(admin, slug="otro")
    client_user(api, admin, a)
    mb = client_user(api, admin, b, email="otro@otro.com")
    m = new_member(admin, a["id"], name="Sara", email="sara@acme.com")
    assert mb.patch(f"{V1}/team/{m['id']}", json={"name": "X"}).status_code == 404
    assert mb.post(f"{V1}/team/{m['id']}/invite").status_code == 404
    assert mb.delete(f"{V1}/team/{m['id']}").status_code == 404


def test_cap_and_invites_per_hour(api, admin, monkeypatch):
    c = make_client(admin, max_team_members=2)      # el Admin ya ocupa una
    owner = client_user(api, admin, c)
    new_member(owner, c["id"], name="Uno", email="uno@acme.com")
    r = owner.post(f"{V1}/team", params={"client_id": c["id"]},
                   json={"name": "Dos", "email": "dos@acme.com"})
    assert (r.status_code, r.json()["code"]) == (429, "team_members_limit")

    monkeypatch.setattr(settings, "team_invites_per_hour", 2)
    c2 = make_client(admin, slug="otro")
    owner2 = client_user(api, admin, c2, email="owner2@otro.com")
    for i in range(2):
        new_member(owner2, c2["id"], name=f"P{i}", email=f"p{i}@otro.com")
    r = owner2.post(f"{V1}/team", params={"client_id": c2["id"]}, json={"name": "P3", "email": "p3@otro.com"})
    assert (r.status_code, r.json()["code"]) == (429, "too_many_invites")


def test_oauth_admin_cannot_give_access_from_the_mcp(api, setup):  # noqa: F811
    """El MCP no da accesos: email, rol e invitación son del panel (403 panel_user_required)."""
    from .test_oauth import connect, mcp

    c, agent, user, app_client = setup
    access = connect(api, (c, agent, user, app_client))["access_token"]
    out = mcp(api, access, params={"name": "create_team_member",
                                   "arguments": {"name": "Sara", "email": "sara@acme.com"}}).json()["result"]
    assert out["isError"] and out["structuredContent"]["code"] == "panel_user_required"
