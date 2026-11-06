import io
from decimal import Decimal

import pytest
from conftest import FORM_EJEMPLO
from sqlalchemy import func, select

from registros import cli
from registros.auth import api_key_hash
from registros.models import ApiKey, PersonPhone, Tenant, User


def _tenant(session, slug="uno") -> Tenant:
    session.expire_all()
    return session.scalar(select(Tenant).where(Tenant.slug == slug))


def test_create_tenant(session):
    assert cli.main(["create-tenant", "--slug", "uno", "--name", "Uno", "--amount", "1500.50"]) == 0
    tenant = _tenant(session)
    assert (tenant.name, tenant.charge_amount, tenant.currency) == ("Uno", Decimal("1500.50"), "ARS")


@pytest.mark.parametrize("amount", ["abc", "-1", "NaN"])
def test_create_tenant_monto_invalido(amount, session, capsys):
    assert cli.main(["create-tenant", "--slug", "uno", "--name", "Uno", "--amount", amount]) == 1
    assert _tenant(session) is None


def test_create_tenant_repetido(make_tenant, capsys):
    make_tenant()
    assert cli.main(["create-tenant", "--slug", "uno", "--name", "Otro", "--amount", "1"]) == 1
    assert "Ya existe" in capsys.readouterr().err


def test_load_form_carga_y_rehace_los_telefonos(make_tenant, make_person, session):
    # El tenant arranca sin rutas de contacto: el contacto no cuenta hasta cargar el formulario.
    from conftest import MANIFEST

    tenant = make_tenant(manifest={**MANIFEST, "contact_phone_paths": []})
    person = make_person(tenant, celular="351 000 0001", contactos=["351 000 0002"])
    count = select(func.count()).select_from(PersonPhone).where(PersonPhone.person_id == person.id)
    assert session.scalar(count) == 1

    assert cli.main(["load-form", "--tenant", "uno", "--dir", str(FORM_EJEMPLO)]) == 0
    tenant = _tenant(session)
    assert "datos.nombre" in tenant.form_html
    assert tenant.manifest["contact_phone_paths"] == ["contactos[*].telefono"]
    assert tenant.form_schema["type"] == "object"
    assert session.scalar(count) == 2


@pytest.mark.parametrize("name, content, message", [
    ("manifest.json", '{"name": "x"}', "manifest.json"),
    ("manifest.json", "no es json", "JSON"),
    ("schema.json", '{"type": "no-existe"}', "schema.json"),
])
def test_load_form_invalido_no_cambia_nada(make_tenant, session, tmp_path, capsys, name, content, message):
    make_tenant(manifest={})
    for file in FORM_EJEMPLO.iterdir():
        (tmp_path / file.name).write_text(file.read_text())
    (tmp_path / name).write_text(content)
    assert cli.main(["load-form", "--tenant", "uno", "--dir", str(tmp_path)]) == 1
    assert message in capsys.readouterr().err
    assert _tenant(session).form_html is None


def test_load_form_sin_archivos(make_tenant, tmp_path, capsys):
    make_tenant()
    assert cli.main(["load-form", "--tenant", "uno", "--dir", str(tmp_path)]) == 1


def test_comando_con_tenant_inexistente(capsys):
    assert cli.main(["create-key", "--tenant", "no", "--scope", "read", "--name", "x"]) == 1
    assert "No existe" in capsys.readouterr().err


def _password(monkeypatch, value):
    monkeypatch.setattr("sys.stdin", io.StringIO(value + "\n"))


def test_create_user_y_login(client, make_tenant, login, monkeypatch):
    tenant = make_tenant()
    _password(monkeypatch, "una-clave-larga")
    assert cli.main(["create-user", "--tenant", "uno", "--email", "Ana@Example.com", "--password-stdin"]) == 0
    assert login(client, tenant, email="ana@example.com", password="una-clave-larga").status_code == 200


def test_create_user_existente_cambia_la_clave_y_cierra_sesiones(client, make_tenant, make_user, login, monkeypatch,
                                                                session):
    tenant = make_tenant()
    make_user(tenant)
    login(client, tenant)
    assert client.get("/auth/me").status_code == 200

    _password(monkeypatch, "clave-nueva-larga")
    assert cli.main(["create-user", "--tenant", "uno", "--email", "ana@example.com", "--password-stdin"]) == 0
    assert client.get("/auth/me").status_code == 401
    assert session.scalar(select(func.count()).select_from(User)) == 1
    assert login(client, tenant, password="clave-nueva-larga").status_code == 200


def test_create_user_clave_corta(make_tenant, monkeypatch, capsys):
    make_tenant()
    _password(monkeypatch, "corta")
    assert cli.main(["create-user", "--tenant", "uno", "--email", "a@b.c", "--password-stdin"]) == 1


def test_create_key_muestra_la_clave_una_vez_y_guarda_el_hash(make_tenant, session, capsys):
    tenant = make_tenant()
    assert cli.main(["create-key", "--tenant", "uno", "--scope", "charge", "--name", "post-call"]) == 0
    key = capsys.readouterr().out.strip()
    row = session.scalar(select(ApiKey))
    assert (row.tenant_id, row.scope, row.name) == (tenant.id, "charge", "post-call")
    assert row.key_hash == api_key_hash(key) and key not in row.key_hash


def test_create_key_alcance_invalido(make_tenant):
    make_tenant()
    with pytest.raises(SystemExit):
        cli.main(["create-key", "--tenant", "uno", "--scope", "admin", "--name", "x"])


@pytest.mark.parametrize("slug", ["admin", "Uno", "-uno", "u", "uno dos"])
def test_create_tenant_slug_invalido(slug, session, capsys):
    assert cli.main(["create-tenant", f"--slug={slug}", "--name", "Uno", "--amount", "1"]) == 1
    assert "Slug inválido" in capsys.readouterr().err
    assert session.scalar(select(func.count()).select_from(Tenant)) == 0


def test_create_admin_alta_y_login(client, monkeypatch, session):
    _password(monkeypatch, "clave-del-admin-larga")
    assert cli.main(["create-admin", "--email", "Admin@Example.com", "--password-stdin"]) == 0
    tenant = _tenant(session, "admin")
    assert (tenant.is_admin, tenant.name, tenant.charge_amount) == (True, "Administración", Decimal("0"))
    r = client.post("/auth/login", json={"tenant": "admin", "email": "admin@example.com",
                                         "password": "clave-del-admin-larga"})
    assert r.status_code == 200
    assert client.get("/admin/api/tenants").status_code == 200


def test_create_admin_existente_resetea_la_clave_y_cierra_sesiones(client, monkeypatch, session):
    _password(monkeypatch, "clave-del-admin-larga")
    cli.main(["create-admin", "--email", "admin@example.com", "--password-stdin"])
    client.post("/auth/login", json={"tenant": "admin", "email": "admin@example.com",
                                     "password": "clave-del-admin-larga"})
    assert client.get("/auth/me").status_code == 200

    _password(monkeypatch, "otra-clave-del-admin")
    assert cli.main(["create-admin", "--email", "admin@example.com", "--password-stdin"]) == 0
    assert client.get("/auth/me").status_code == 401
    assert session.scalar(select(func.count()).select_from(Tenant)) == 1
    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_create_admin_clave_corta(monkeypatch, session):
    _password(monkeypatch, "once-chars!")  # 11
    assert cli.main(["create-admin", "--email", "admin@example.com", "--password-stdin"]) == 1
    assert session.scalar(select(func.count()).select_from(Tenant)) == 0


def test_create_admin_con_un_tenant_admin_comun_se_niega(make_tenant, monkeypatch, session, capsys):
    make_tenant("admin")
    _password(monkeypatch, "clave-del-admin-larga")
    assert cli.main(["create-admin", "--email", "admin@example.com", "--password-stdin"]) == 1
    assert "admin común" in capsys.readouterr().err
    assert _tenant(session, "admin").is_admin is False
    assert session.scalar(select(func.count()).select_from(User)) == 0


def test_comandos_comunes_no_tocan_el_tenant_admin(monkeypatch, session, capsys):
    _password(monkeypatch, "clave-del-admin-larga")
    cli.main(["create-admin", "--email", "admin@example.com", "--password-stdin"])
    _password(monkeypatch, "una-clave-larga")
    assert cli.main(["create-user", "--tenant", "admin", "--email", "otro@example.com", "--password-stdin"]) == 1
    assert cli.main(["create-key", "--tenant", "admin", "--scope", "read", "--name", "x"]) == 1
    assert session.scalar(select(func.count()).select_from(User)) == 1
    assert session.scalar(select(func.count()).select_from(ApiKey)) == 0


def test_cli_no_escribe_en_audit_log(make_tenant, monkeypatch, session):
    from registros.models import AuditLog

    assert cli.main(["create-tenant", "--slug", "uno", "--name", "Uno", "--amount", "1"]) == 0
    assert cli.main(["load-form", "--tenant", "uno", "--dir", str(FORM_EJEMPLO)]) == 0
    _password(monkeypatch, "una-clave-larga")
    assert cli.main(["create-user", "--tenant", "uno", "--email", "a@b.c", "--password-stdin"]) == 0
    assert cli.main(["create-key", "--tenant", "uno", "--scope", "read", "--name", "x"]) == 0
    _password(monkeypatch, "clave-del-admin-larga")
    assert cli.main(["create-admin", "--email", "admin@example.com", "--password-stdin"]) == 0
    assert session.scalar(select(func.count()).select_from(AuditLog)) == 0
