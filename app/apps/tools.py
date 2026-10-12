"""Herramientas de un agente con motor assistant: las de las apps del cliente que lista
workflow.tools, mas las de la plataforma (un link por vista de cada app).

Nombres: el de la herramienta en la app; si dos apps del agente usan el mismo, <app>__<nombre>.
Las de la plataforma: vista_<vista> (o vista_<app>__<vista>).
"""
import copy
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..conversation.models import ToolGrant
from ..models import App
from ..services.errors import Invalid
from . import client as app_client
from . import links
from .registry import CONFIRM_KINDS, manifest_of, token_of

# Lo que el decoding guiado (xgrammar) no necesita y solo agranda el prompt.
DROP_KEYS = {"title", "examples", "$schema"}


@dataclass
class Tool:
    name: str                 # como lo ve el LLM
    description: str
    kind: str                 # read, write, destructive, send
    schema: dict              # argumentos (JSON Schema, sin $ref)
    app_id: str
    app_slug: str
    target: str               # herramienta de la app, o la vista (platform)
    platform: bool = False
    params: dict = field(default_factory=dict)

    @property
    def needs_confirmation(self) -> bool:
        return self.kind in CONFIRM_KINDS


def inline_refs(schema: dict) -> dict:
    """Resuelve $ref locales (#/$defs/...) y saca claves de mas. Sin ciclos (los modelos de las apps no tienen)."""
    defs = {**schema.get("$defs", {}), **schema.get("definitions", {})}

    def walk(node: Any, depth: int = 0) -> Any:
        if depth > 20:
            raise Invalid("Esquema de herramienta demasiado anidado")
        if isinstance(node, dict):
            if isinstance(node.get("$ref"), str):
                target = defs.get(node["$ref"].rsplit("/", 1)[-1])
                if target is None:
                    raise Invalid(f"Esquema con $ref desconocida: {node['$ref']}")
                return walk(copy.deepcopy(target), depth + 1)
            return {k: walk(v, depth + 1) for k, v in node.items()
                    if k not in DROP_KEYS and k not in ("$defs", "definitions")}
        if isinstance(node, list):
            return [walk(x, depth + 1) for x in node]
        return node

    def simplify(node: Any) -> Any:
        """anyOf [X, null] de pydantic -> X (opcional igual: no esta en required), y default null afuera."""
        if isinstance(node, dict):
            node = {k: simplify(v) for k, v in node.items() if not (k == "default" and v is None)}
            options = node.get("anyOf")
            if isinstance(options, list) and any(o == {"type": "null"} for o in options):
                rest = [o for o in options if o != {"type": "null"}]
                if len(rest) == 1:
                    merged = {**{k: v for k, v in node.items() if k != "anyOf"}, **rest[0]}
                    return merged
                node["anyOf"] = rest
            return node
        if isinstance(node, list):
            return [simplify(x) for x in node]
        return node

    out = simplify(walk(schema))
    out.setdefault("type", "object")
    out.setdefault("properties", {})
    return out


def _granted(grant: ToolGrant, names: list[str]) -> list[str]:
    return names if "*" in grant.tools else [n for n in names if n in grant.tools]


def apps_for(s: Session, client_id: str | None, grants: list[ToolGrant]) -> list[App]:
    """Las apps de los grants, solo si son del cliente. Las que faltan se ignoran (se valida al guardar)."""
    if not grants or client_id is None:
        return []
    slugs = [g.app for g in grants]
    return list(s.scalars(select(App).where(App.slug.in_(slugs), App.client_id == client_id)))


def check_grants(s: Session, client_id: str, grants: list[ToolGrant]) -> None:
    """Al guardar un agente: cada app existe y es del cliente, y cada herramienta esta en su manifest."""
    apps = {a.slug: a for a in apps_for(s, client_id, grants)}
    details = []
    for i, grant in enumerate(grants):
        app = apps.get(grant.app)
        if app is None:
            details.append({"path": f"tools.{i}.app", "message": f"El cliente no tiene la app {grant.app!r}"})
            continue
        known = {t.name for t in manifest_of(app).tools}
        details += [{"path": f"tools.{i}.tools", "message": f"La app {grant.app!r} no tiene la herramienta {n!r}"}
                    for n in grant.tools if n != "*" and n not in known]
    if details:
        raise Invalid("La definicion del agente no es valida", "invalid_definition", details)


def catalog(s: Session, client_id: str | None, grants: list[ToolGrant]) -> list[Tool]:
    apps = apps_for(s, client_id, grants)
    by_slug = {a.slug: a for a in apps}
    raw: list[Tool] = []
    for grant in grants:
        app = by_slug.get(grant.app)
        if app is None or app.status == "invalid":
            continue
        manifest = manifest_of(app)
        specs = {t.name: t for t in manifest.tools}
        for name in _granted(grant, list(specs)):
            spec = specs[name]
            raw.append(Tool(name=name, description=spec.description, kind=spec.kind,
                            schema=inline_refs(spec.input_schema), app_id=app.id, app_slug=app.slug, target=name))
        if view := _view_tool(app, manifest):
            raw.append(view)
    counts: dict[str, int] = {}
    for t in raw:
        counts[t.name] = counts.get(t.name, 0) + 1
    for t in raw:
        if counts[t.name] > 1:
            t.name = f"{t.app_slug}__{t.target}"
    return raw


SCALARS = ("string", "integer", "number", "boolean")


def _view_tool(app: App, manifest) -> Tool | None:
    """Una sola herramienta de plataforma por app (contrato v1.1): la vista como enum y la union de
    los parametros de todas, opcionales. Una por vista agrandaba el prompt de cada paso."""
    if not manifest.views:
        return None
    props: dict[str, dict] = {"vista": {"enum": [v.name for v in manifest.views]}}
    lines = []
    for v in manifest.views:
        for p, spec in v.params.items():
            props.setdefault(p, {"type": spec.type if spec.type in SCALARS else "string"})
        params = ", ".join(v.params) or "sin parámetros"
        lines.append(f"{v.name} («{v.title}»: {v.description} Parámetros: {params})")
    return Tool(name="abrir_vista", kind="read", app_id=app.id, app_slug=app.slug, target="", platform=True,
                description=("Devuelve un link para que el usuario vea una pantalla en su celular, como una marca "
                             "[[linkN]] que el sistema cambia por el link: ponela tal cual en tu respuesta. "
                             "Vistas: " + "; ".join(lines)),
                schema={"type": "object", "properties": props, "required": ["vista"]},
                params={v.name: list(v.params) for v in manifest.views})


async def execute(s_factory, tool: Tool, arguments: dict, actor: str, conversation_id: str | None = None) -> dict:
    """Corre la herramienta. {"ok": bool, "result": ...}. Las fallas de la app vuelven como
    ok=False con un texto, para que el LLM se lo diga al usuario. Una herramienta send que
    devuelve outbox: Atentina entrega los mensajes (app/apps/outbox.py)."""
    if tool.platform:
        view = arguments.get("vista")
        if view not in tool.params:
            return {"ok": False, "result": f"No existe la vista {view!r}"}
        params = {k: v for k, v in arguments.items() if k in tool.params[view]}
        with s_factory() as s:
            app = s.get(App, tool.app_id)
            try:
                url, _ = links.create_link(s, app, view, params, actor)
            except Invalid as e:
                return {"ok": False, "result": e.message}
            s.commit()
        return {"ok": True, "result": {"url": url}}
    with s_factory() as s:
        app = s.get(App, tool.app_id)
        base_url, token = app.base_url, token_of(app)
    try:
        out = await app_client.call_tool(base_url, token, tool.target, arguments, actor)
    except app_client.AppError:
        return {"ok": False, "result": "La aplicación no responde en este momento."}
    result = out["result"]
    if out["ok"] and tool.kind == "send" and isinstance(result, dict) and result.get("outbox"):
        from . import outbox
        result = {**result, "outbox": await outbox.deliver(s_factory, tool.app_id, result["outbox"], conversation_id)}
        out = {**out, "result": result}
    return out
