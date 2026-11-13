"""Migracion 0057: las definiciones guardadas pasan a la forma con prompt y las herramientas a {{x}}.

Ida y vuelta en SQLite: la definicion vieja (con external, opening_audio y required_if) y la herramienta con
{{vars.}}/{{contact.}} vuelven iguales; analysis.fields queda como lista en el orden de priority leido de la base;
una definicion ya nueva no se toca; el downgrade aborta si hay filas nuevas sin copia.
"""
import json

import pytest
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

OLD = {
    "id": "ventas", "version": 3,
    "agent": {"name": "Sofía", "role": "asesora", "language": "es-AR", "voice": "sofia"},
    "objective": {"description": "Vender el plan."},
    "conversation": {"opening": "Hola, te habla Sofía.", "opening_audio": True, "opening_delay_ms": 300,
                     "rules": ["Sé breve."]},
    "knowledge": "La empresa vende planes.", "external": {"connection": "abc"},
    "fields": {
        "z": {"type": "string", "description": "Zeta", "priority": 2, "question": "¿Z?"},
        "deuda": {"type": "digits", "description": "Deuda", "priority": 1, "required_if": {"z": "si"}},
        "a": {"type": "choice", "options": ["si", "no"], "description": "A", "priority": 1},
    },
    "completion": {"outcomes": [{"id": "vendio", "label": "Vendió", "when": {"z": "si"}, "message": "Chau"},
                                {"id": "otro", "label": "Otro"}]},
}
NEW = {"id": "nuevo", "version": 2, "agent": {"name": "Ana", "language": "es-AR"}, "prompt": "Hola {{nombre}}"}
TOOL = {"description": "Consulta", "url": "https://api.example.com/x",
        "headers": {"Authorization": "Bearer {{vars.token}}"},
        "path": {"id": {"value": "{{contact.nombre}}"}},
        "body": {"properties": {"dato": {"value": "{{secrets.KEY}} y {{vars.token}}", "description": "d"}},
                 "required": ["dato"]}}
TOOL_PLAIN = {"description": "Sin templates", "url": "https://api.example.com/y", "headers": {}}


def _insert(engine, sql, **values):
    with engine.begin() as conn:
        conn.execute(sa.text(sql), values)


def _client(engine):
    _insert(engine, "INSERT INTO tiers (id, name, description, created_at, updated_at) "
                    "VALUES ('t', 'T', '', '2026-01-01', '2026-01-01')")
    _insert(engine, "INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                    "VALUES ('c', 'C', 'c', 't', 1, '2026-01-01', '2026-01-01')")


def _agent(engine, definition, version=None, agent_id="a1", slug="ventas"):
    _insert(engine, "INSERT INTO agents (id, client_id, name, slug, description, version, definition, archived_at, "
                    "created_at, updated_at) VALUES (:id, 'c', 'Agente', :slug, '', :version, :definition, NULL, "
                    "'2026-01-01', '2026-01-01')",
            id=agent_id, slug=slug, version=version or definition["version"],
            definition=json.dumps(definition, ensure_ascii=False))
    for v in range(1, (version or definition["version"]) + 1):
        _insert(engine, "INSERT INTO agent_versions (agent_id, version, definition, created_at, created_by) "
                        "VALUES (:id, :version, :definition, '2026-01-01', NULL)",
                id=agent_id, version=v, definition=json.dumps(definition, ensure_ascii=False))


def _tool(engine, definition, tool_id="t1", slug="consulta", revision=1):
    _insert(engine, "INSERT INTO tools (id, client_id, slug, type, definition, revision, created_by, "
                    "last_test_at, last_test_ok, last_test_detail, created_at, updated_at) "
                    "VALUES (:id, 'c', :slug, 'http', :definition, :revision, NULL, NULL, NULL, '', '2026-01-01', "
                    "'2026-01-01')",
            id=tool_id, slug=slug, revision=revision, definition=json.dumps(definition, ensure_ascii=False))
    _insert(engine, "INSERT INTO tool_versions (id, tool_id, revision, type, definition, created_by, created_at) "
                    "VALUES (:vid, :id, :revision, 'http', :definition, NULL, '2026-01-01')",
            vid=f"tv-{tool_id}", id=tool_id, revision=revision,
            definition=json.dumps(definition, ensure_ascii=False))


def _value(engine, sql, **params):
    with engine.connect() as conn:
        value = conn.execute(sa.text(sql), params).scalar_one()
    return json.loads(value) if isinstance(value, str) else value


def _cols(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def test_0057_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0056")
    _client(engine)
    _agent(engine, OLD)
    _tool(engine, TOOL)
    _tool(engine, TOOL_PLAIN, tool_id="t2", slug="plana")

    _run(engine, command.upgrade, "0057")
    for table in ("agents", "agent_versions", "tools", "tool_versions"):
        assert "definition_legacy" in _cols(engine, table)

    # La vieja: copiada tal cual y en la forma nueva, con id y version intactos.
    legacy = _value(engine, "SELECT definition_legacy FROM agents WHERE id = 'a1'")
    assert legacy == OLD
    definition = _value(engine, "SELECT definition FROM agents WHERE id = 'a1'")
    assert definition["id"] == "ventas" and definition["version"] == 3
    assert definition["external"] == {"connection": "abc"}
    for gone in ("objective", "conversation", "knowledge", "fields", "completion"):
        assert gone not in definition
    assert "role" not in definition["agent"]
    assert definition["first_message"] == "Hola, te habla Sofía."
    assert definition["first_message_audio"] is True and definition["first_message_delay_ms"] == 300
    assert "Vender el plan." in definition["prompt"] and definition["agent"]["name"] in definition["prompt"]
    # La forma nueva: fields como lista y en el orden de priority, leido de vuelta de la base.
    fields = definition["analysis"]["fields"]
    assert isinstance(fields, list) and [f["name"] for f in fields] == ["deuda", "a", "z"]
    assert [f["type"] for f in fields][0] == "string"          # digits pasa a string
    assert [o["id"] for o in definition["analysis"]["outcomes"]] == ["vendio", "otro"]
    assert definition["analysis"]["summary"] is True
    # Las versiones, igual que la vigente.
    version = _value(engine, "SELECT definition FROM agent_versions WHERE agent_id = 'a1' AND version = 3")
    assert version == definition
    assert _value(engine, "SELECT definition_legacy FROM agent_versions WHERE agent_id = 'a1' AND version = 1") == OLD

    # La herramienta con {{vars.}}/{{contact.}} pasa a {{x}}; la que no los tiene queda sin copia.
    tool = _value(engine, "SELECT definition FROM tools WHERE id = 't1'")
    assert tool["headers"]["Authorization"] == "Bearer {{token}}"
    assert tool["path"]["id"]["value"] == "{{nombre}}"
    assert tool["body"]["properties"]["dato"]["value"] == "{{secrets.KEY}} y {{token}}"
    assert _value(engine, "SELECT definition_legacy FROM tools WHERE id = 't1'") == TOOL
    assert _value(engine, "SELECT definition FROM tool_versions WHERE id = 'tv-t1'") == tool
    assert _value(engine, "SELECT definition FROM tools WHERE id = 't2'") == TOOL_PLAIN
    assert _value(engine, "SELECT definition_legacy FROM tools WHERE id = 't2'") is None

    _run(engine, command.downgrade, "0056")
    assert _value(engine, "SELECT definition FROM agents WHERE id = 'a1'") == OLD
    assert _value(engine, "SELECT definition FROM agent_versions WHERE agent_id = 'a1' AND version = 3") == OLD
    assert _value(engine, "SELECT definition FROM tools WHERE id = 't1'") == TOOL
    assert _value(engine, "SELECT definition FROM tool_versions WHERE id = 'tv-t1'") == TOOL
    for table in ("agents", "agent_versions", "tools", "tool_versions"):
        assert "definition_legacy" not in _cols(engine, table)

    _run(engine, command.upgrade, "0057")
    assert _value(engine, "SELECT definition FROM agents WHERE id = 'a1'") == definition
    assert _value(engine, "SELECT definition FROM tools WHERE id = 't1'") == tool


def test_0057_una_definicion_nueva_no_cambia(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0056")
    _client(engine)
    _agent(engine, NEW, agent_id="a2", slug="nuevo")
    _tool(engine, {"description": "Solo secretos", "url": "https://api.example.com/z",
                   "headers": {"X-Key": "{{secrets.KEY}}"}}, tool_id="t3", slug="secretos")

    _run(engine, command.upgrade, "0057")
    assert _value(engine, "SELECT definition FROM agents WHERE id = 'a2'") == NEW
    assert _value(engine, "SELECT definition_legacy FROM agents WHERE id = 'a2'") is None
    assert _value(engine, "SELECT definition FROM agent_versions WHERE agent_id = 'a2' AND version = 2") == NEW
    tool = _value(engine, "SELECT definition FROM tools WHERE id = 't3'")
    assert tool == {"description": "Solo secretos", "url": "https://api.example.com/z",
                    "headers": {"X-Key": "{{secrets.KEY}}"}}
    assert _value(engine, "SELECT definition_legacy FROM tools WHERE id = 't3'") is None


def test_0057_downgrade_aborta_con_una_fila_nueva(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0056")
    _client(engine)
    _agent(engine, OLD)
    # Guardada despues de la 0057: la 0056 no sabe leerla y no hay copia de donde restaurarla.
    _agent(engine, NEW, agent_id="a2", slug="nuevo")

    _run(engine, command.upgrade, "0057")
    with pytest.raises(RuntimeError, match="no puede deshacerse"):
        _run(engine, command.downgrade, "0056")
    # No toco nada: sigue en la 0057 y con lo migrado.
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "0057"
    assert "definition_legacy" in _cols(engine, "agents")
    assert _value(engine, "SELECT definition FROM agents WHERE id = 'a2'") == NEW
    assert _value(engine, "SELECT definition_legacy FROM agents WHERE id = 'a1'") == OLD


def test_0057_downgrade_aborta_con_una_herramienta_nueva(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0056")
    _client(engine)
    _tool(engine, TOOL)
    _tool(engine, {"description": "Con variable", "url": "https://api.example.com/v",
                   "headers": {"X-Deuda": "{{deuda}}"}}, tool_id="t4", slug="variable")

    _run(engine, command.upgrade, "0057")
    with pytest.raises(RuntimeError, match=r"1 en tools con \{\{x\}\}"):
        _run(engine, command.downgrade, "0056")
    # Aborto antes de restaurar nada: la herramienta con copia sigue en la forma nueva.
    assert _value(engine, "SELECT definition FROM tools WHERE id = 't1'")["headers"]["Authorization"] == "Bearer {{token}}"
