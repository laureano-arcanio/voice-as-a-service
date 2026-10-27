"""Formato de una herramienta del cliente (docs/TOOLS_PLAN.md, secciones 4 y 5).

Dos tipos, con el mismo encabezado (descripcion, confirmacion, frases de voz y respuesta):
- http: Atentina llama a una API. El pedido se separa en path, query, headers y body, y cada parametro
  tiene un solo origen: lo llena el modelo (tiene `description` y no `value`) o es fijo (`value`, que
  puede ser un template). El modelo solo ve los que llena. Es el formato de ElevenLabs (webhook tool).
- code: una funcion `export default async function ({ args, secrets, call, vars })` en JavaScript,
  que corre en el sandbox (tools-runner). `parameters` es el JSON Schema de args.

Templates en los valores fijos: {{secrets.NOMBRE}}, {{call.id|channel|mode|from|to}}, {{agent.slug|version}},
{{now}}, {{today}}, {{fields.x}}, {{contact.x}}, {{vars.x}}.
"""
import re
from typing import Any, Literal
from urllib.parse import urlparse

import jsonschema
from pydantic import BaseModel, Field, field_validator, model_validator

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SECRET_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
HEADER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_]{0,63}$")
PARAM_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]{0,63}$")
TEMPLATE_RE = re.compile(r"\{\{\s*([a-z]+)(?:\.([A-Za-z0-9_]+))?\s*\}\}")
# {variable} de la ruta, sin confundirla con un template {{...}}.
PATH_VAR_RE = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")
HOST_RE = re.compile(r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+(:\d{1,5})?$")

# Los nombres de las herramientas de la plataforma: el cliente no los puede usar.
RESERVED = {"end_call", "transfer_call", "abrir_vista"}
CALL_KEYS = {"id", "channel", "mode", "from", "to"}
AGENT_KEYS = {"slug", "version"}
NAMESPACES = {"secrets", "call", "agent", "fields", "contact", "vars", "now", "today"}
# Headers que arma el cliente HTTP o la plataforma.
FORBIDDEN_HEADERS = {"host", "content-length", "transfer-encoding", "connection", "user-agent",
                     "idempotency-key", "x-atentina-signature", "x-atentina-conversation-id", "x-atentina-tool"}
SCALARS = ("string", "integer", "number", "boolean")
MAX_CODE_CHARS = 20_000
MAX_SECRET_CHARS = 10_000


def templates(text: str) -> list[tuple[str, str | None]]:
    return [(m.group(1), m.group(2)) for m in TEMPLATE_RE.finditer(text)]


def check_template(text: str, where: str) -> None:
    for ns, key in templates(text):
        if ns not in NAMESPACES:
            raise ValueError(f"{where}: variable desconocida {{{{{ns}}}}} (usá secrets, call, agent, fields, contact, "
                             "vars, now o today)")
        if ns in ("now", "today"):
            if key is not None:
                raise ValueError(f"{where}: {{{{{ns}}}}} va sin punto")
            continue
        if key is None:
            raise ValueError(f"{where}: {{{{{ns}}}}} necesita un nombre ({{{{{ns}.nombre}}}})")
        if ns == "secrets" and not SECRET_RE.fullmatch(key):
            raise ValueError(f"{where}: secreto {key!r}: mayúsculas, números y _ (ej. CRM_TOKEN)")
        if ns == "call" and key not in CALL_KEYS:
            raise ValueError(f"{where}: {{{{call.{key}}}}} no existe (id, channel, mode, from, to)")
        if ns == "agent" and key not in AGENT_KEYS:
            raise ValueError(f"{where}: {{{{agent.{key}}}}} no existe (slug, version)")


def secrets_in(text: str) -> set[str]:
    return {key for ns, key in templates(text) if ns == "secrets" and key}


class Param(BaseModel):
    """Un parametro de path o query (escalar; en query tambien un array de escalares)."""
    model_config = {"extra": "forbid"}
    type: Literal["string", "integer", "number", "boolean", "array"] = "string"
    description: str | None = Field(default=None, max_length=500)
    enum: list[str | int | float] | None = None
    format: str | None = Field(default=None, max_length=32)
    items: dict[str, Any] | None = None
    # Fijo: literal o template. Con value el modelo no lo ve.
    value: str | int | float | bool | list[str | int | float | bool] | None = None
    required: bool = False

    @property
    def by_llm(self) -> bool:
        return self.value is None

    def llm_schema(self) -> dict:
        out: dict[str, Any] = {"type": self.type}
        if self.description:
            out["description"] = self.description
        if self.enum:
            out["enum"] = self.enum
        if self.format:
            out["format"] = self.format
        if self.type == "array":
            out["items"] = self.items or {"type": "string"}
        return out


class Delayed(BaseModel):
    model_config = {"extra": "forbid"}
    after_ms: int = Field(default=3000, ge=500, le=30000)
    text: str = Field(min_length=1, max_length=200)


class Messages(BaseModel):
    """Frases de voz: al empezar, si tarda y si falla."""
    model_config = {"extra": "forbid"}
    start: str | None = Field(default=None, max_length=200)
    delayed: Delayed | None = None
    failed: str | None = Field(default=None, max_length=200)


class ResponseConfig(BaseModel):
    model_config = {"extra": "forbid"}
    # Rutas con puntos y [i] que se quedan del resultado (vacio = todo).
    pick: list[str] = Field(default_factory=list, max_length=30)
    max_chars: int = Field(default=4000, ge=200, le=15000)

    @field_validator("pick")
    @classmethod
    def _paths(cls, value: list[str]) -> list[str]:
        for p in value:
            if not re.fullmatch(r"[A-Za-z0-9_\-]+(\[\d+\])*(\.[A-Za-z0-9_\-]+(\[\d+\])*)*", p):
                raise ValueError(f"response.pick: ruta invalida {p!r} (ej. data.items[0].nombre)")
        return value


class Assign(BaseModel):
    """Guarda un valor del resultado en vars, para otras herramientas ({{vars.x}})."""
    model_config = {"extra": "forbid"}
    var: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    path: str = Field(min_length=1, max_length=200)
    # Se guarda pero no va al modelo.
    hide: bool = False


class Auth(BaseModel):
    type: Literal["none", "bearer", "api_key", "basic", "oauth2_client_credentials"] = "none"
    # El secreto del agente que se usa: token, key, clave o client secret.
    secret: str | None = None
    header: str | None = None          # bearer y api_key en header
    prefix: str | None = None          # bearer: "Bearer " por default
    name: str | None = None            # api_key: nombre del header o del parametro
    in_: Literal["header", "query"] | None = Field(default=None, alias="in")
    username: str | None = None        # basic (literal o template)
    token_url: str | None = None       # oauth2
    client_id: str | None = None
    scope: str | None = None
    audience: str | None = None
    client_auth: Literal["body", "basic"] = "body"

    model_config = {"extra": "forbid", "populate_by_name": True}

    @model_validator(mode="after")
    def _consistent(self) -> "Auth":
        if self.type == "none":
            return self
        if not self.secret or not SECRET_RE.fullmatch(self.secret):
            raise ValueError("auth.secret: el nombre del secreto del agente (ej. CRM_TOKEN)")
        if self.type == "api_key":
            if not self.name or not (HEADER_RE.fullmatch(self.name) if (self.in_ or "header") == "header"
                                     else PARAM_RE.fullmatch(self.name)):
                raise ValueError("auth.name: el nombre del header o del parametro de la key (ej. X-API-Key)")
            if (self.in_ or "header") == "header" and self.name.lower() in FORBIDDEN_HEADERS:
                raise ValueError(f"auth.name: {self.name} lo pone la plataforma")
        if self.type == "bearer" and self.header and (not HEADER_RE.fullmatch(self.header)
                                                      or self.header.lower() in FORBIDDEN_HEADERS):
            raise ValueError("auth.header: nombre de header invalido")
        if self.type == "basic":
            if not self.username:
                raise ValueError("auth.username: obligatorio con basic")
            check_template(self.username, "auth.username")
        if self.type == "oauth2_client_credentials":
            if not self.token_url or not self.client_id:
                raise ValueError("auth: token_url y client_id son obligatorios con oauth2_client_credentials")
            check_url(self.token_url, "auth.token_url", allow_templates=False)
            check_template(self.client_id, "auth.client_id")
        return self

    def header_name(self) -> str | None:
        if self.type == "bearer":
            return self.header or "Authorization"
        if self.type == "api_key" and (self.in_ or "header") == "header":
            return self.name
        if self.type in ("basic", "oauth2_client_credentials"):
            return "Authorization"
        return None

    def secret_names(self) -> set[str]:
        out = {self.secret} if self.type != "none" and self.secret else set()
        for text in (self.username, self.client_id):
            if text:
                out |= secrets_in(text)
        return out


def check_url(url: str, where: str, *, allow_templates: bool = True) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"{where}: tiene que ser una URL http(s) completa")
    if parsed.username or parsed.password:
        raise ValueError(f"{where}: sin usuario ni clave en la URL (usá auth)")
    if "{{" in (parsed.hostname or "") or "{" in (parsed.netloc or ""):
        raise ValueError(f"{where}: el host no puede tener variables")
    if not allow_templates and "{{" in url:
        raise ValueError(f"{where}: sin variables")
    if parsed.fragment:
        raise ValueError(f"{where}: sin #fragmento")


class ToolBase(BaseModel):
    """Lo comun a los dos tipos. El slug va aparte (columna de la tabla), igual que el tipo."""
    description: str = Field(min_length=1, max_length=1000,
                             description="Para el modelo: qué hace y cuándo usarla")
    # La descripcion que ve el modelo pide confirmar con la persona antes de usarla. No hay confirmacion de
    # plataforma: decide el modelo (AGENTS.md, "Reglas de desarrollo").
    confirm: bool = False
    messages: Messages = Field(default_factory=Messages)
    response: ResponseConfig = Field(default_factory=ResponseConfig)
    assign: list[Assign] = Field(default_factory=list, max_length=10)


class HttpConfig(BaseModel):
    model_config = {"extra": "forbid"}
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    url: str = Field(min_length=8, max_length=2000)
    path: dict[str, Param] = Field(default_factory=dict)
    query: dict[str, Param] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    # JSON Schema de tipo object; una propiedad de primer nivel con "value" es fija.
    body: dict[str, Any] | None = None
    content_type: Literal["application/json", "application/x-www-form-urlencoded"] = "application/json"
    auth: Auth = Field(default_factory=Auth)
    timeout_ms: int = Field(default=8000, ge=500, le=30000)
    retries: int = Field(default=0, ge=0, le=2)
    # Firma HMAC-SHA256 (X-Atentina-Signature) con el secreto ATENTINA_SIGNING_SECRET del agente.
    sign: bool = False

    @model_validator(mode="after")
    def _consistent(self) -> "HttpConfig":
        check_url(self.url, "http.url")
        check_template(PATH_VAR_RE.sub("", self.url), "http.url")
        url_vars = set(PATH_VAR_RE.findall(urlparse(self.url).path))
        if url_vars != set(self.path):
            missing, extra = url_vars - set(self.path), set(self.path) - url_vars
            parts = ([f"faltan en path: {', '.join(sorted(missing))}"] if missing else []) + \
                    ([f"no están en la URL: {', '.join(sorted(extra))}"] if extra else [])
            raise ValueError("http.path: las {variables} de la URL y path tienen que coincidir (" + "; ".join(parts) + ")")
        for where, params in (("path", self.path), ("query", self.query)):
            for name, p in params.items():
                if not PARAM_RE.fullmatch(name):
                    raise ValueError(f"http.{where}.{name}: nombre invalido")
                if where == "path" and p.type == "array":
                    raise ValueError(f"http.path.{name}: un parametro de la ruta no puede ser un array")
                _check_param(p, f"http.{where}.{name}")
        for name, value in self.headers.items():
            if not HEADER_RE.fullmatch(name):
                raise ValueError(f"http.headers.{name}: nombre de header invalido")
            if name.lower() in FORBIDDEN_HEADERS:
                raise ValueError(f"http.headers.{name}: lo pone la plataforma")
            check_template(value, f"http.headers.{name}")
        if (auth_header := self.auth.header_name()) and auth_header.lower() in {h.lower() for h in self.headers}:
            raise ValueError(f"http.headers.{auth_header}: ya lo pone auth")
        if self.body is not None:
            if self.method in ("GET", "DELETE"):
                raise ValueError(f"http.body: {self.method} va sin body (usá query)")
            _check_body(self.body)
            if self.content_type == "application/x-www-form-urlencoded":
                for name, prop in (self.body.get("properties") or {}).items():
                    if prop.get("type") in ("object", "array"):
                        raise ValueError(f"http.body.{name}: un formulario solo lleva valores simples")
        names = [n for n, p in {**self.path, **self.query}.items() if p.by_llm] + body_llm_names(self.body)
        if dup := {n for n in names if names.count(n) > 1}:
            raise ValueError(f"http: parametros repetidos entre path, query y body: {', '.join(sorted(dup))}")
        return self


def _check_param(p: Param, where: str) -> None:
    if p.value is None:
        if not p.description:
            raise ValueError(f"{where}: lleva description (lo completa el agente) o value (fijo)")
        return
    values = p.value if isinstance(p.value, list) else [p.value]
    for v in values:
        if isinstance(v, str):
            check_template(v, where)


def _check_body(body: dict) -> None:
    if body.get("type", "object") != "object":
        raise ValueError("http.body: tiene que ser un JSON Schema de tipo object")
    props = body.get("properties")
    if not isinstance(props, dict):
        raise ValueError("http.body.properties: obligatorio")
    for name, prop in props.items():
        if not isinstance(prop, dict):
            raise ValueError(f"http.body.{name}: tiene que ser un objeto")
        if "value" in prop:
            values = prop["value"] if isinstance(prop["value"], list) else [prop["value"]]
            for v in values:
                if isinstance(v, str):
                    check_template(v, f"http.body.{name}")
        elif not prop.get("description") and prop.get("type") != "object":
            raise ValueError(f"http.body.{name}: lleva description (lo completa el agente) o value (fijo)")
    try:
        jsonschema.Draft202012Validator.check_schema(llm_body_schema(body) or {"type": "object"})
    except jsonschema.SchemaError as e:
        raise ValueError(f"http.body: JSON Schema invalido: {e.message}") from None


def llm_body_schema(body: dict | None) -> dict | None:
    """El body sin las propiedades fijas: lo que completa el modelo."""
    if not body:
        return None
    props = {k: v for k, v in (body.get("properties") or {}).items() if "value" not in v}
    if not props:
        return None
    required = [r for r in body.get("required") or [] if r in props]
    return {"type": "object", "properties": props, **({"required": required} if required else {})}


def body_llm_names(body: dict | None) -> list[str]:
    schema = llm_body_schema(body)
    return list(schema["properties"]) if schema else []


def _body_secrets(body: dict | None) -> set[str]:
    out: set[str] = set()
    for prop in (body or {}).get("properties", {}).values():
        values = prop.get("value") if isinstance(prop, dict) else None
        for v in values if isinstance(values, list) else [values]:
            if isinstance(v, str):
                out |= secrets_in(v)
    return out


class HttpTool(ToolBase):
    model_config = {"extra": "forbid"}
    http: HttpConfig


class CodeTool(ToolBase):
    model_config = {"extra": "forbid"}
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})
    code: str = Field(min_length=20, max_length=MAX_CODE_CHARS)
    secrets: list[str] = Field(default_factory=list, max_length=20)
    allowed_hosts: list[str] = Field(default_factory=list, max_length=20)
    timeout_ms: int = Field(default=5000, ge=500, le=30000)

    @model_validator(mode="after")
    def _consistent(self) -> "CodeTool":
        if self.parameters.get("type", "object") != "object" or not isinstance(self.parameters.get("properties", {}), dict):
            raise ValueError("parameters: tiene que ser un JSON Schema de tipo object")
        try:
            jsonschema.Draft202012Validator.check_schema(self.parameters)
        except jsonschema.SchemaError as e:
            raise ValueError(f"parameters: JSON Schema invalido: {e.message}") from None
        for name in self.secrets:
            if not SECRET_RE.fullmatch(name):
                raise ValueError(f"secrets: {name!r}: mayúsculas, números y _ (ej. CRM_TOKEN)")
        self.allowed_hosts = [h.strip().lower() for h in self.allowed_hosts]
        for host in self.allowed_hosts:
            if not HOST_RE.fullmatch(host):
                raise ValueError(f"allowed_hosts: {host!r}: un dominio, con puerto si no es el 443, sin https:// ni ruta "
                                 "(ej. api.ejemplo.com)")
        if not re.search(r"export\s+default", self.code):
            raise ValueError("code: el módulo necesita un export default async function")
        return self


ToolType = Literal["http", "code"]


def parse(tool_type: str, definition: dict) -> HttpTool | CodeTool:
    """La definicion validada; ValueError (de pydantic) si no vale."""
    if tool_type == "http":
        return HttpTool.model_validate(definition)
    if tool_type == "code":
        return CodeTool.model_validate(definition)
    raise ValueError("type: http o code")


def check_slug(slug: str) -> str:
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("slug: minúsculas, números y _ (ej. consultar_turnos), de 2 a 64")
    if slug in RESERVED:
        raise ValueError(f"slug: {slug} es de la plataforma")
    return slug


def required_secrets(tool: HttpTool | CodeTool) -> set[str]:
    """Los secretos que tiene que tener el agente para usar la herramienta."""
    if isinstance(tool, CodeTool):
        return set(tool.secrets)
    h = tool.http
    out = secrets_in(h.url) | h.auth.secret_names() | _body_secrets(h.body)
    for value in h.headers.values():
        out |= secrets_in(value)
    for p in [*h.path.values(), *h.query.values()]:
        for v in p.value if isinstance(p.value, list) else [p.value]:
            if isinstance(v, str):
                out |= secrets_in(v)
    if h.sign:
        out.add(SIGNING_SECRET)
    return out


SIGNING_SECRET = "ATENTINA_SIGNING_SECRET"


def llm_parameters(tool: HttpTool | CodeTool) -> dict:
    """El JSON Schema de los argumentos que completa el modelo."""
    if isinstance(tool, CodeTool):
        return {"type": "object", **tool.parameters, "properties": tool.parameters.get("properties", {})}
    h = tool.http
    props: dict[str, Any] = {}
    required: list[str] = []
    for name, p in h.path.items():
        if p.by_llm:
            props[name] = p.llm_schema()
            required.append(name)
    for name, p in h.query.items():
        if p.by_llm:
            props[name] = p.llm_schema()
            if p.required:
                required.append(name)
    if body := llm_body_schema(h.body):
        props.update(body["properties"])
        required += body.get("required", [])
    return {"type": "object", "properties": props, **({"required": required} if required else {})}


# Protocolo del resultado (lo que devuelve runtime.finish), al final de cada descripcion.
RESULT_NOTE = 'Devuelve {"ok": true, "data": ...} o {"ok": false, "error": ...}.'
CONFIRM_NOTE = "Antes de usarla, confirmá con la persona lo que vas a hacer."


def openai_tool(slug: str, tool: HttpTool | CodeTool) -> dict:
    """Formato de function calling de OpenAI (chat completions), el que hablan todos los proveedores."""
    description = " ".join(p for p in (tool.description.strip(), CONFIRM_NOTE if tool.confirm else "", RESULT_NOTE) if p)
    return {"type": "function", "function": {"name": slug, "description": description,
                                             "parameters": llm_parameters(tool)}}


def validate_args(tool: HttpTool | CodeTool, args: Any) -> str | None:
    """None si los argumentos del modelo cumplen el esquema; si no, el error para devolverle."""
    if not isinstance(args, dict):
        return "los argumentos tienen que ser un objeto JSON"
    validator = jsonschema.Draft202012Validator(llm_parameters(tool))
    errors = sorted(validator.iter_errors(args), key=lambda e: list(e.path))
    if not errors:
        return None
    e = errors[0]
    where = ".".join(str(p) for p in e.path) or "argumentos"
    return f"{where}: {e.message}"
