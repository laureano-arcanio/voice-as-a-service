"""Una persona por usuario de cliente y rol dentro del cliente (docs/features/EQUIPO_TELEFONIA.md)."""
import pytest

from app.models import Role
from app.services.security import Principal

from .test_api import V1, admin, client_user, make_client, make_tier  # noqa: F401  (admin: fixture)
from .test_billing import landing, plans, register  # noqa: F401  (landing, plans: fixtures)
from .test_mail import outbox  # noqa: F401  (outbox: fixture)


def team(user, client_id):
    r = user.get(f"{V1}/team", params={"client_id": client_id})
    assert r.status_code == 200, r.text
    return r.json()


def make_user(admin, client, email="ana@acme.com", **extra):
    r = admin.post(f"{V1}/users", json={"email": email, "password": "cliente-password-1", "role": "client",
                                         "client_id": client["id"], **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_client_owner_and_admin_users_get_their_person(api, admin):
    r = admin.post(f"{V1}/clients", json={"name": "Acme", "slug": "acme", "tier_id": make_tier(admin)["id"],
                                           "owner_email": "Duenia@Acme.com", "owner_name": "  Dueña  "})
    assert r.status_code == 201, r.text
    client = r.json()
    [owner] = admin.get(f"{V1}/users", params={"client_id": client["id"]}).json()
    assert owner["client_role"] == "admin" and owner["name"] == "Dueña"
    [person] = team(admin, client["id"])
    assert (person["user_id"], person["name"], person["phone"]) == (owner["id"], "Dueña", None)
    assert admin.get(f"{V1}/auth/me").json()["client_role"] is None     # el admin de la plataforma no tiene rol de cliente

    # Por /users: Admin por defecto; con client_role, usuario. Cada uno con su persona y su nombre.
    ana = make_user(admin, client, name="Ana")
    beto = make_user(admin, client, email="beto@acme.com", name="", client_role="user")
    assert (ana["client_role"], beto["client_role"]) == ("admin", "user")
    people = {p["user_id"]: p for p in team(admin, client["id"])}
    assert people[ana["id"]]["name"] == "Ana" and people[beto["id"]]["name"] == "beto"
    # Un admin de la plataforma no lleva rol de cliente.
    bad = admin.post(f"{V1}/users", json={"email": "x@x.com", "password": "cliente-password-1", "role": "admin",
                                           "client_role": "user"})
    assert bad.status_code == 422


def test_signup_creates_the_person_and_the_admin_role(landing):  # noqa: F811
    from sqlalchemy import select

    from app.models import Client, User

    register(landing)
    with landing.sessions() as s:
        client = s.scalar(select(Client).where(Client.created_via == "signup"))
        user = s.scalar(select(User).where(User.client_id == client.id))
    assert user.client_role == "admin"
    # La persona existe y está vinculada (se mira por la base de la fixture).
    from app.models import TeamMember
    with landing.sessions() as s:
        member = s.scalar(select(TeamMember).where(TeamMember.user_id == user.id))
    assert member is not None and member.client_id == client.id and member.name == user.name


def test_delete_user_deletes_its_person(api, admin):
    c = make_client(admin)
    user = make_user(admin, c, client_role="user")
    assert [p["user_id"] for p in team(admin, c["id"])] == [user["id"]]
    assert admin.delete(f"{V1}/users/{user['id']}").status_code == 204
    assert team(admin, c["id"]) == []
    assert admin.get(f"{V1}/users", params={"client_id": c["id"]}).json() == []


def test_the_name_is_shared_between_the_person_and_the_user(api, admin):
    c = make_client(admin)
    ana = client_user(api, admin, c)
    ana_id = ana.get(f"{V1}/auth/me").json()["id"]
    person = team(ana, c["id"])[0]
    assert person["user_id"] == ana_id

    assert ana.patch(f"{V1}/team/{person['id']}", json={"name": "Ana Pérez"}).status_code == 200
    assert ana.get(f"{V1}/auth/me").json()["name"] == "Ana Pérez"
    assert ana.get(f"{V1}/auth/me").json()["client_role"] == "admin"

    assert ana.patch(f"{V1}/auth/me", json={"name": "Ana P."}).status_code == 200
    assert team(ana, c["id"])[0]["name"] == "Ana P."
    # Un vacío no pisa el nombre de la persona ni el del usuario.
    assert ana.patch(f"{V1}/auth/me", json={"name": "  "}).status_code == 200
    assert team(ana, c["id"])[0]["name"] == "Ana P."
    assert ana.get(f"{V1}/auth/me").json()["name"] == "Ana P."

    assert admin.patch(f"{V1}/users/{ana_id}", json={"name": "Ana desde Usuarios"}).status_code == 200
    assert team(admin, c["id"])[0]["name"] == "Ana desde Usuarios"
    assert admin.patch(f"{V1}/users/{ana_id}", json={"name": ""}).status_code == 200
    assert team(admin, c["id"])[0]["name"] == "Ana desde Usuarios"


def test_never_without_an_admin_from_users(api, admin):
    c = make_client(admin)
    ana = client_user(api, admin, c)
    ana_id = ana.get(f"{V1}/auth/me").json()["id"]
    for body in ({"active": False}, {"client_role": "user"}):
        r = admin.patch(f"{V1}/users/{ana_id}", json=body)
        assert (r.status_code, r.json()["code"]) == (409, "last_admin"), body
    r = admin.delete(f"{V1}/users/{ana_id}")
    assert (r.status_code, r.json()["code"]) == (409, "last_admin")

    # Con otro Admin activo, el primero puede quedar como Usuario; el último no se puede bajar ni borrar.
    other = make_user(admin, c, email="jefe@acme.com")
    assert admin.patch(f"{V1}/users/{ana_id}", json={"client_role": "user"}).status_code == 200
    r = admin.patch(f"{V1}/users/{other['id']}", json={"client_role": "user"})
    assert (r.status_code, r.json()["code"]) == (409, "last_admin")
    # Volver a Admin y desactivar al otro: queda uno.
    assert admin.patch(f"{V1}/users/{ana_id}", json={"client_role": "admin"}).status_code == 200
    assert admin.patch(f"{V1}/users/{other['id']}", json={"active": False}).status_code == 200
    assert admin.delete(f"{V1}/users/{ana_id}").status_code == 409


def test_client_admin_by_principal():
    is_admin = Principal("user", "a", Role.admin, None)
    support = Principal("user", "a", Role.client, "c", support=True)
    api_key = Principal("api_key", "k", Role.client, "c")
    admin_client = Principal("user", "u", Role.client, "c", client_role="admin")
    user = Principal("user", "u", Role.client, "c", client_role="user")
    legacy = Principal("user", "u", Role.client, "c")
    link = Principal("link", "l", Role.client, "c", client_role="admin")
    assert all(p.client_admin for p in (is_admin, support, api_key, admin_client, link))
    assert not user.client_admin and not legacy.client_admin
