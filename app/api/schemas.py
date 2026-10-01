"""Contratos de la API (entrada y salida). La UI genera sus tipos del OpenAPI
que salen de aca (web/, `npm run gen:api`)."""
import datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

# La base guarda UTC sin zona; la API la explicita (2026-09-29T13:57:52+00:00) para
# que el navegador no la tome como hora local.
UTCDateTime = Annotated[datetime.datetime,
                        AfterValidator(lambda d: d if d.tzinfo else d.replace(tzinfo=datetime.UTC))]

SLUG = r"^[a-z0-9][a-z0-9_]{0,63}$"
E164 = r"^\+\d{8,15}$"


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorOut(BaseModel):
    detail: str
    code: str | None = None
    errors: list[dict] = []


# ---------- auth ----------

class LoginIn(BaseModel):
    # Sin validar formato: el login solo compara contra lo guardado.
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class MeOut(BaseModel):
    id: str
    email: str
    name: str
    role: Literal["admin", "client"]
    client_id: str | None
    client_name: str | None


# ---------- tiers ----------

class TierIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    # None: ilimitado.
    max_concurrent_calls: int | None = Field(default=None, ge=0)
    inbound_minutes: int | None = Field(default=None, ge=0, description="Minutos entrantes por mes")
    outbound_minutes: int | None = Field(default=None, ge=0, description="Minutos salientes por mes")
    max_phone_numbers: int | None = Field(default=None, ge=0, description="Numeros que puede tener el cliente")


class TierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    max_concurrent_calls: int | None = Field(default=None, ge=0)
    inbound_minutes: int | None = Field(default=None, ge=0)
    outbound_minutes: int | None = Field(default=None, ge=0)
    max_phone_numbers: int | None = Field(default=None, ge=0)


class TierOut(ORM):
    id: str
    name: str
    description: str
    max_concurrent_calls: int | None
    inbound_minutes: int | None
    outbound_minutes: int | None
    max_phone_numbers: int | None
    created_at: UTCDateTime
    clients_count: int = 0


# ---------- clientes ----------

class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str = Field(pattern=SLUG)
    tier_id: str
    active: bool = True


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    tier_id: str | None = None
    active: bool | None = None


class TierBrief(ORM):
    id: str
    name: str


class ClientOut(ORM):
    id: str
    name: str
    slug: str
    active: bool
    tier: TierBrief
    created_at: UTCDateTime
    agents_count: int = 0
    numbers_count: int = 0


class MinutesUsageOut(BaseModel):
    used_seconds: int
    used_minutes: float
    limit_minutes: int | None
    remaining_minutes: float | None


class NumbersUsageOut(BaseModel):
    used: int
    limit: int | None


class UsageOut(BaseModel):
    month: str
    period_start: UTCDateTime
    period_end: UTCDateTime
    active_calls: int
    max_concurrent_calls: int | None
    inbound: MinutesUsageOut
    outbound: MinutesUsageOut
    phone_numbers: NumbersUsageOut


# ---------- numeros ----------

class PhoneNumberIn(BaseModel):
    e164: str = Field(pattern=E164, examples=["+541152630861"])
    label: str = Field(default="", max_length=64)
    provider: str = Field(default="anura", max_length=32)
    # Opcional: asignarlo en el mismo paso (con el tope del tier) y rutearlo.
    client_id: str | None = None
    agent_id: str | None = Field(default=None, description="Agente que atiende las entrantes")


class PhoneNumberBulkIn(BaseModel):
    """Carga al inventario: uno por elemento, en E.164 o con espacios y guiones."""
    numbers: list[str] = Field(min_length=1, max_length=1000)
    label: str = Field(default="", max_length=64)
    provider: str = Field(default="anura", max_length=32)


class PhoneNumberUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=64)
    agent_id: str | None = None


class AssignIn(BaseModel):
    client_id: str


class PhoneNumberOut(ORM):
    id: str
    e164: str
    label: str
    provider: str
    client_id: str | None
    client_name: str | None = None
    agent_id: str | None
    agent_name: str | None = None
    assigned_at: UTCDateTime | None
    created_at: UTCDateTime


class SkippedNumber(BaseModel):
    number: str
    reason: str


class PhoneNumberBulkOut(BaseModel):
    created: list[PhoneNumberOut]
    skipped: list[SkippedNumber]


# ---------- whatsapp ----------

class WaAccountIn(BaseModel):
    client_id: str
    agent_id: str = Field(description="Agente del cliente que atiende los mensajes")
    phone_number_id: str = Field(pattern=r"^\d{1,32}$", description="ID del numero en Meta")
    waba_id: str = Field(min_length=1, max_length=32)
    display_phone_number: str = Field(min_length=1, max_length=32, examples=["+1 555 145 6632"])
    name: str = Field(default="", max_length=128)
    access_token: str | None = Field(default=None, description="Sin token: el del system user (WA_ACCESS_TOKEN)")


class WaAccountPatch(BaseModel):
    agent_id: str | None = None
    display_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, max_length=128)
    access_token: str | None = Field(default=None, description="\"\" lo borra: vuelve al token global")
    active: bool | None = None


class WaAccountOut(BaseModel):
    """El token nunca sale: solo si la cuenta tiene uno propio."""
    id: str
    client_id: str
    client_name: str | None = None
    agent_id: str
    agent_name: str | None = None
    phone_number_id: str
    waba_id: str
    display_phone_number: str
    name: str
    has_token: bool
    active: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime


# ---------- agentes ----------

class AgentCreate(BaseModel):
    client_id: str
    name: str = Field(min_length=1, max_length=128)
    slug: str | None = Field(default=None, pattern=SLUG, description="Sin slug, se arma del nombre")
    description: str = ""
    # Uno de los dos: la definicion (workflow JSON) o una plantilla de partida.
    definition: dict[str, Any] | None = None
    template_id: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    archived: bool | None = None


class DefinitionIn(BaseModel):
    definition: dict[str, Any]


class ValidationOut(BaseModel):
    valid: bool
    errors: list[dict] = []


class AgentOut(ORM):
    id: str
    client_id: str
    name: str
    slug: str
    description: str
    version: int
    archived: bool
    engine: str
    voice: str | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class AgentDetail(AgentOut):
    definition: dict[str, Any]


class AgentVersionOut(ORM):
    version: int
    created_at: UTCDateTime
    created_by: str | None
    created_by_email: str | None = None
    definition: dict[str, Any] | None = None


class TemplateOut(BaseModel):
    id: str
    engine: str
    agent: str
    voice: str | None
    objective: str


# ---------- usuarios y API keys ----------

class UserIn(BaseModel):
    email: EmailStr
    name: str = Field(default="", max_length=128)
    password: str = Field(min_length=10, max_length=256)
    role: Literal["admin", "client"]
    client_id: str | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, min_length=10, max_length=256)
    active: bool | None = None


class UserOut(ORM):
    id: str
    email: str
    name: str
    role: str
    client_id: str | None
    client_name: str | None = None
    active: bool
    created_at: UTCDateTime
    last_login_at: UTCDateTime | None


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class ApiKeyOut(ORM):
    id: str
    client_id: str
    name: str
    prefix: str
    created_at: UTCDateTime
    last_used_at: UTCDateTime | None
    revoked_at: UTCDateTime | None


class ApiKeyCreated(ApiKeyOut):
    key: str = Field(description="Se muestra una sola vez")


# ---------- llamadas ----------

class CallIn(BaseModel):
    agent_id: str
    phone: str | None = Field(default=None, description="E.164; sin telefono es una llamada de prueba")
    from_number_id: str | None = Field(default=None, description="Numero del cliente para el caller ID")
    voice: str | None = None
    loadtest: bool = False


class CallStartedOut(BaseModel):
    conversation_id: str
    room: str
    mode: str
    join_url: str | None = None


class CallSummary(BaseModel):
    id: str
    client_id: str | None
    client_name: str | None
    agent_id: str | None
    agent_name: str | None
    agent_version: int | None
    workflow_status: str
    created_at: str | None
    contact_name: Any = None
    company: Any = None
    outcome: str | None
    goal: bool
    captured: int
    required: int
    mode: str
    phone: str | None
    status: str | None
    duration_seconds: int
    ended_reason: str
    latency_avg: float | None


class CallPage(BaseModel):
    items: list[CallSummary]
    total: int


class FieldValue(BaseModel):
    name: str
    description: str
    value: Any
    required: bool
    rejected: Any = None


class CallInfo(BaseModel):
    mode: str
    phone: str | None
    client_number: str | None
    status: str
    ended_reason: str
    error: str
    duration_seconds: int
    latency: dict | None
    created_at: str | None
    started_at: str | None
    ended_at: str | None


class OutcomeOut(BaseModel):
    label: str
    goal: bool


class LlmCall(BaseModel):
    """Una llamada al LLM en un turno (conversacion o extraccion), tal cual."""
    kind: str
    input: str
    ms: int | None = None
    reasoning: str | None = None
    output: str | None = None


class MessageOut(BaseModel):
    role: Literal["assistant", "user"]
    text: str
    llm: list[LlmCall] | None = None
    # WhatsApp: del usuario, transcripcion de una nota de voz; del agente, enviada como nota de voz.
    voice_note: bool = False


class WhatsAppInfo(BaseModel):
    """La conversacion por WhatsApp: contacto, numero del negocio y envios fallidos."""
    wa_id: str
    contact_name: str | None
    business_number: str | None
    account_id: str
    last_user_at: str | None
    failed_messages: int
    last_error: dict | None


class CallDetail(BaseModel):
    id: str
    client_id: str | None
    client_name: str | None
    agent_id: str | None
    agent_name: str | None
    agent_version: int | None
    created_at: str | None
    workflow_status: str
    fields: list[FieldValue]
    outcome: OutcomeOut | None
    messages: list[MessageOut]
    call: CallInfo | None
    whatsapp: WhatsAppInfo | None = None


class StatsOut(BaseModel):
    total: int
    calls: int
    finished: int
    failed: int
    rejected: int
    completed: int
    completed_pct: float
    goal: int
    goal_pct: float
    total_minutes: float
    avg_duration: int
    latency_avg: float | None
    whatsapp: int = 0


class DailyOut(BaseModel):
    labels: list[str]
    totals: list[int]
    completed_pct: list[float | None]
    goal_pct: list[float | None]


# ---------- conversaciones por texto ----------

class ConversationIn(BaseModel):
    agent_id: str


class TurnIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ConversationStateOut(BaseModel):
    conversation_id: str
    agent_id: str
    agent_version: int
    client_id: str | None
    status: Literal["active", "completed"]
    fields: dict[str, Any]
    messages: list[MessageOut]


class ConversationStartOut(BaseModel):
    conversation_id: str
    message: str
    state: ConversationStateOut


class TurnOut(BaseModel):
    message: str
    state: ConversationStateOut
    next_objective: str | None
    status: Literal["active", "completed"]


# ---------- voces ----------

class VoiceOut(BaseModel):
    nombre: str
    genero: str
    wer: float | None
    car_s: float | None


class TtsPreviewIn(BaseModel):
    voice: str
    text: str = Field(max_length=600)


# ---------- demo de la landing ----------

class DemoSessionIn(BaseModel):
    turnstile_token: str = Field(min_length=1, max_length=2048)


class DemoSessionOut(BaseModel):
    token: str
    expires_in: int


class DemoCallIn(BaseModel):
    agent: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=64)
    voice: str | None = Field(default=None, max_length=32)


class DemoCallOut(BaseModel):
    conversation_id: str
    room: str
    livekit_url: str
    token: str
    max_duration_seconds: int
    result_token: str


class DemoField(BaseModel):
    name: str
    label: str
    type: str
    value: Any


class DemoOutcome(BaseModel):
    label: str
    goal: bool


class DemoMessage(BaseModel):
    role: Literal["assistant", "user"]
    text: str


class DemoCallResult(BaseModel):
    final: bool
    status: str
    ended_reason: str
    duration_seconds: int
    agent_name: str
    completed: bool
    outcome: DemoOutcome | None
    fields: list[DemoField]
    messages: list[DemoMessage]


class DemoTtsIn(BaseModel):
    voice: str = Field(max_length=32)
    text: str = Field(min_length=1, max_length=600)
