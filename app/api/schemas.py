"""Contratos de la API (entrada y salida). La UI genera sus tipos del OpenAPI
que salen de aca (web/, `npm run gen:api`)."""
import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

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


class PasswordSetupCheckIn(BaseModel):
    token: str = Field(min_length=10, max_length=2048)


class PasswordSetupIn(PasswordSetupCheckIn):
    password: str = Field(min_length=10, max_length=256)


class PasswordSetupInfo(BaseModel):
    email: str
    name: str
    client_name: str | None


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
    max_calls_per_hour: int | None = Field(default=None, ge=0, description="Llamadas por hora calendario")
    max_calls_per_day: int | None = Field(default=None, ge=0, description="Llamadas por dia calendario")
    max_calls_per_month: int | None = Field(default=None, ge=0, description="Llamadas por mes calendario")
    # API de inferencia (solo uso por API key; no cuenta los agentes integrados). None: ilimitado; 0: no incluido.
    api_llm_input_tokens: int | None = Field(default=0, ge=0, description="Tokens de entrada del LLM por mes")
    api_llm_output_tokens: int | None = Field(default=0, ge=0, description="Tokens generados por el LLM por mes")
    api_tts_minutes: int | None = Field(default=0, ge=0, description="Minutos de audio sintetizado por mes")
    api_stt_minutes: int | None = Field(default=0, ge=0, description="Minutos de audio transcripto por mes")
    api_rate_limit: int | None = Field(default=60, ge=0, description="Pedidos por minuto a la API de inferencia")


class TierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    max_concurrent_calls: int | None = Field(default=None, ge=0)
    inbound_minutes: int | None = Field(default=None, ge=0)
    outbound_minutes: int | None = Field(default=None, ge=0)
    max_phone_numbers: int | None = Field(default=None, ge=0)
    max_calls_per_hour: int | None = Field(default=None, ge=0)
    max_calls_per_day: int | None = Field(default=None, ge=0)
    max_calls_per_month: int | None = Field(default=None, ge=0)
    api_llm_input_tokens: int | None = Field(default=None, ge=0)
    api_llm_output_tokens: int | None = Field(default=None, ge=0)
    api_tts_minutes: int | None = Field(default=None, ge=0)
    api_stt_minutes: int | None = Field(default=None, ge=0)
    api_rate_limit: int | None = Field(default=None, ge=0)


class TierOut(ORM):
    id: str
    name: str
    description: str
    max_concurrent_calls: int | None
    inbound_minutes: int | None
    outbound_minutes: int | None
    max_phone_numbers: int | None
    max_calls_per_hour: int | None
    max_calls_per_day: int | None
    max_calls_per_month: int | None
    api_llm_input_tokens: int | None
    api_llm_output_tokens: int | None
    api_tts_minutes: int | None
    api_stt_minutes: int | None
    api_rate_limit: int | None
    created_at: UTCDateTime
    clients_count: int = 0


# ---------- clientes ----------

class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str = Field(pattern=SLUG)
    tier_id: str
    active: bool = True
    owner_email: EmailStr | None = Field(
        default=None,
        description="Si viene, se crea el usuario del cliente y se le manda un mail para crear su clave")
    owner_name: str = Field(default="", max_length=128, description="Nombre del usuario (saludo del mail)")


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
    adjustments_count: int = Field(default=0, description="Ajustes de limites vigentes hoy")


# ---------- ajustes de limites por cliente ----------

# Los campos de Tier que se pueden ajustar (igual a services/limits.LIMIT_FIELDS; un test lo verifica).
LimitField = Literal[
    "max_concurrent_calls", "max_calls_per_hour", "max_calls_per_day", "max_calls_per_month",
    "inbound_minutes", "outbound_minutes", "max_phone_numbers",
    "api_llm_input_tokens", "api_llm_output_tokens", "api_tts_minutes", "api_stt_minutes", "api_rate_limit",
]


class LimitAdjustmentIn(BaseModel):
    """`add` suma `value` al limite del tier; `set` lo reemplaza (value null = ilimitado). Sin fechas
    es permanente; con ellas, vale entre `starts_on` y `ends_on`, ambos inclusive."""
    field: LimitField
    mode: Literal["add", "set"]
    value: int | None = Field(default=None, ge=0, description="Cantidad (minutos, numeros, llamadas, tokens)")
    starts_on: datetime.date | None = None
    ends_on: datetime.date | None = None
    note: str = Field(default="", max_length=255, description="Para que se dio (queda en el registro)")

    @model_validator(mode="after")
    def _coherent(self):
        if self.mode == "add" and not self.value:
            raise ValueError("Un ajuste de tipo add necesita una cantidad mayor que 0")
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on no puede ser anterior a starts_on")
        return self


class LimitAdjustmentOut(ORM):
    id: str
    field: LimitField
    mode: Literal["add", "set"]
    value: int | None
    starts_on: datetime.date | None
    ends_on: datetime.date | None
    note: str
    status: Literal["active", "scheduled", "expired"]
    created_at: UTCDateTime
    created_by_email: str | None = None


class LimitRowOut(BaseModel):
    field: LimitField
    tier: int | None = Field(description="Valor del tier (null = ilimitado)")
    effective: int | None = Field(description="Valor que rige hoy, con los ajustes vigentes")


class ClientLimitsOut(BaseModel):
    tier_name: str
    limits: list[LimitRowOut]
    adjustments: list[LimitAdjustmentOut]


class InviteOut(BaseModel):
    """Resultado del mail para crear la clave. disabled: el servidor no tiene RESEND_API_KEY."""
    email: str
    status: Literal["sent", "failed", "disabled"]
    error: str | None = None


class ClientCreatedOut(ClientOut):
    invite: InviteOut | None = None


class MinutesUsageOut(BaseModel):
    used_seconds: int
    used_minutes: float
    limit_minutes: int | None
    remaining_minutes: float | None


class NumbersUsageOut(BaseModel):
    used: int
    limit: int | None


class CallsUsageOut(BaseModel):
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
    calls_hour: CallsUsageOut = Field(description="Llamadas de la hora en curso")
    calls_day: CallsUsageOut = Field(description="Llamadas del dia en curso")
    calls_month: CallsUsageOut = Field(description="Llamadas del mes pedido")


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
    """Usuario del cliente: solo agent_id, name y active. El resto, admin."""
    agent_id: str | None = None
    display_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, max_length=128)
    access_token: str | None = Field(default=None, description="\"\" lo borra: vuelve al token global")
    active: bool | None = None


class WaAccountOut(BaseModel):
    """El token y el PIN nunca salen: solo si la cuenta tiene uno propio."""
    id: str
    client_id: str
    client_name: str | None = None
    agent_id: str
    agent_name: str | None = None
    phone_number_id: str
    waba_id: str
    business_id: str | None = None
    display_phone_number: str
    name: str
    has_token: bool
    has_pin: bool = False
    active: bool
    status: Literal["connected", "pending", "disconnected"] = Field(
        description="connected: atiende. pending: falta suscribir o registrar (reintentar). "
                    "disconnected: Meta rechazo el token o el cliente quito el acceso")
    status_reason: str | None = None
    status_changed_at: UTCDateTime | None = None
    quality_rating: str | None = Field(default=None, description="GREEN, YELLOW, RED, NA o UNKNOWN (Meta)")
    messaging_limit: str | None = Field(default=None, description="current_limit de phone_number_quality_update")
    source: Literal["manual", "embedded_signup", "coexistence"] = "manual"
    created_at: UTCDateTime
    updated_at: UTCDateTime


class WaConfigOut(BaseModel):
    """Lo que necesita la UI para lanzar Embedded Signup. enabled=false: el boton va
    deshabilitado y se muestra reason."""
    enabled: bool
    reason: str | None = None
    app_id: str | None = None
    config_id: str | None = None
    graph_version: str
    sdk_locale: str


class WaSignupIn(BaseModel):
    """Lo que devuelve el popup de Embedded Signup: el codigo de FB.login (vence a los
    30 s) y los IDs del mensaje WA_EMBEDDED_SIGNUP."""
    code: str = Field(min_length=1, max_length=2048)
    waba_id: str = Field(pattern=r"^\d{1,32}$")
    phone_number_id: str = Field(default="", pattern=r"^\d{0,32}$",
                                 description="Vacio con FINISH_ONLY_WABA (se rechaza) o en coexistencia "
                                             "(se toma el unico numero de la WABA)")
    business_id: str | None = Field(default=None, pattern=r"^\d{1,32}$")
    event: Literal["FINISH", "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING", "FINISH_ONLY_WABA"] = "FINISH"
    agent_id: str = Field(description="Agente del cliente que atiende los mensajes")
    client_id: str | None = Field(default=None, description="Solo admin; a un usuario de cliente se le fuerza el suyo")
    pin: str | None = Field(default=None, pattern=r"^\d{6}$",
                            description="PIN de dos pasos del numero; sin el, se genera uno y se guarda cifrado")


class WaRegisterIn(BaseModel):
    pin: str | None = Field(default=None, pattern=r"^\d{6}$")


class WaTemplateOut(BaseModel):
    id: str
    name: str
    language: str
    category: str
    status: str
    rejected_reason: str | None = None
    components: list[dict[str, Any]] = []


class WaTemplateButton(BaseModel):
    """URL: abre la pagina (url fija, https). QUICK_REPLY: respuesta rapida; su texto llega
    como mensaje del contacto ("No me interesa" da la baja de las campañas)."""
    type: Literal["URL", "QUICK_REPLY"]
    text: str = Field(min_length=1, max_length=25)
    url: str | None = Field(default=None, max_length=2000)


class WaTemplateIn(BaseModel):
    """Plantilla de texto. Variables posicionales {{1}}, {{2}}... en el cuerpo, con un
    ejemplo por variable (Meta los usa para revisarla). Botones opcionales."""
    name: str = Field(pattern=r"^[a-z0-9_]{1,512}$", description="Minusculas, numeros y _")
    language: str = Field(default="es_AR", pattern=r"^[a-z]{2,3}(_[A-Z]{2})?$")
    category: Literal["UTILITY", "MARKETING", "AUTHENTICATION"]
    body: str = Field(min_length=1, max_length=1024)
    examples: list[Annotated[str, Field(max_length=200)]] = Field(default=[], max_length=20)
    header_text: str | None = Field(default=None, max_length=60)
    footer_text: str | None = Field(default=None, max_length=60)
    buttons: list[WaTemplateButton] = Field(default=[], max_length=10)


class WaTemplateCreated(BaseModel):
    id: str
    status: str | None = None
    category: str | None = None


class WaRecipientIn(BaseModel):
    phone: str = Field(min_length=3, max_length=32, examples=["+54 9 351 555-1234", "3515551234"])
    name: str | None = Field(default=None, max_length=128)
    params: list[Annotated[str, Field(max_length=1024)]] = Field(
        default=[], max_length=20, description="Valores de {{1}}, {{2}}... del cuerpo de la plantilla")


class WaRecipientsIn(BaseModel):
    """Contactos por lista o por CSV (o los dos). CSV con encabezado: columna telefono (o
    celular, phone, whatsapp), nombre opcional, y las demas en orden son {{1}}, {{2}}..."""
    recipients: list[WaRecipientIn] = Field(default=[], max_length=10_000)
    csv: str | None = Field(default=None, max_length=900_000)


class WaCampaignIn(WaRecipientsIn):
    account_id: str = Field(description="Numero de WhatsApp que manda la campaña")
    name: str = Field(min_length=1, max_length=128)
    template_name: str = Field(pattern=r"^[a-z0-9_]{1,512}$", description="Plantilla aprobada de la WABA del numero")
    template_language: str = Field(default="es_AR", pattern=r"^[a-z]{2,3}(_[A-Z]{2})?$")
    agent_id: str | None = Field(default=None, description="Agente que atiende las respuestas; sin el, el del numero")
    rate_per_minute: int = Field(default=20, ge=1, le=600)
    window_start: int = Field(default=9, ge=0, le=23, description="Hora local de inicio (BILLING_TIMEZONE)")
    window_end: int = Field(default=20, ge=1, le=24, description="Hora local de fin, sin incluir")


class WaCampaignPatch(BaseModel):
    """En borrador o pausada. agent_id null: responde el agente del numero."""
    name: str | None = Field(default=None, min_length=1, max_length=128)
    agent_id: str | None = None
    rate_per_minute: int | None = Field(default=None, ge=1, le=600)
    window_start: int | None = Field(default=None, ge=0, le=23)
    window_end: int | None = Field(default=None, ge=1, le=24)


class WaCampaignStats(BaseModel):
    """sent, delivered y read son acumulativos (uno leido tambien fue entregado y enviado)."""
    total: int
    pending: int
    sent: int
    delivered: int
    read: int
    replied: int
    failed: int
    skipped: int
    opted_out: int = Field(description="Recibieron la campaña y despues pidieron la baja")


class WaCampaignOut(BaseModel):
    id: str
    client_id: str
    client_name: str | None = None
    account_id: str
    display_phone_number: str | None = None
    agent_id: str | None = None
    agent_name: str | None = Field(default=None, description="El de la campaña o, sin uno, el del numero")
    name: str
    template_name: str
    template_language: str
    template_category: str
    template_body: str
    template_params: int
    status: Literal["draft", "running", "paused", "done", "cancelled"]
    status_reason: str | None = None
    rate_per_minute: int
    window_start: int
    window_end: int
    timezone: str
    stats: WaCampaignStats
    started_at: UTCDateTime | None = None
    finished_at: UTCDateTime | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class WaRecipientSkipped(BaseModel):
    phone: str
    reason: str
    line: int | None = Field(default=None, description="Fila del CSV (la 1 es el encabezado)")


class WaRecipientsAdded(BaseModel):
    added: int
    skipped: list[WaRecipientSkipped]


class WaCampaignCreated(WaRecipientsAdded):
    campaign: WaCampaignOut


class WaRecipientOut(BaseModel):
    id: str
    wa_id: str
    name: str | None = None
    params: list[str]
    status: Literal["pending", "sent", "delivered", "read", "replied", "failed", "skipped"]
    error: dict[str, Any] | None = None
    sent_at: UTCDateTime | None = None
    replied_at: UTCDateTime | None = None
    conversation_id: str | None = None


class WaRecipientPage(BaseModel):
    items: list[WaRecipientOut]
    total: int


class WaOptoutIn(BaseModel):
    phone: str = Field(min_length=3, max_length=32)
    client_id: str | None = Field(default=None, description="Solo admin")


class WaOptoutOut(BaseModel):
    client_id: str
    wa_id: str
    source: Literal["keyword", "manual"]
    created_at: UTCDateTime


# ---------- agentes ----------

class AgentCreate(BaseModel):
    client_id: str | None = Field(
        default=None, description="Obligatorio para un admin; un usuario o API key de cliente crea en el suyo")
    name: str = Field(min_length=1, max_length=128)
    slug: str | None = Field(default=None, pattern=SLUG, description="Sin slug, se arma del nombre")
    description: str = ""
    # La definicion (workflow JSON), la plantilla de partida (GET /agent-templates) o ninguna: en blanco.
    definition: dict[str, Any] | None = None
    template_id: str | None = None
    engine: Literal["classic", "structured"] | None = Field(
        default=None, description="Motor; pisa el de la definicion o la plantilla (la definicion es la misma)")


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    archived: bool | None = None


class DefinitionIn(BaseModel):
    definition: dict[str, Any]


class ValidationOut(BaseModel):
    valid: bool
    errors: list[dict] = []


class PromptIn(BaseModel):
    definition: dict[str, Any]
    channel: Literal["voice", "whatsapp"] = "voice"


class PromptOut(BaseModel):
    engine: str
    system: str = Field(description="Prompt de sistema")
    workflow: str | None = Field(default=None, description="structured: la definicion que va en cada turno")


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


ApiScope = Literal["calls", "llm", "stt", "tts"]


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    scopes: list[ApiScope] = Field(
        default=["calls"], min_length=1,
        description="calls: API de llamadas, agentes y reportes. llm, stt, tts: motores de la API de inferencia")


class ApiKeyOut(ORM):
    id: str
    client_id: str
    name: str
    prefix: str
    scopes: list[ApiScope]
    created_at: UTCDateTime
    last_used_at: UTCDateTime | None
    revoked_at: UTCDateTime | None

    @field_validator("scopes", mode="before")
    @classmethod
    def _split_scopes(cls, v):
        return [p for p in v.split(",") if p] if isinstance(v, str) else v


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
    closed_at: str | None = Field(default=None, description="Cerrada: el proximo mensaje empieza otra conversacion")
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
    format: Literal["wav", "pcm"] = Field(
        default="wav", description="wav: archivo completo. pcm: crudo (16 bits, mono, 24 kHz) mientras se sintetiza")


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
    format: Literal["wav", "pcm"] = Field(
        default="wav", description="wav: archivo completo. pcm: crudo (16 bits, mono, 24 kHz) mientras se sintetiza")


class DemoContactIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    company: str = Field(default="", max_length=120)
    email: EmailStr | None = None
    phone: str = Field(default="", max_length=40, pattern=r"^$|^[0-9+()\- ]{6,40}$")
    message: str = Field(default="", max_length=2000)
    page: str = Field(default="", max_length=64, pattern=r"^$|^/[a-z0-9/_-]*$")
    # Trampa para bots: el campo esta oculto en el formulario. Con valor, se responde 204 sin guardar.
    website: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def email_or_phone(self):
        if not self.email and not self.phone:
            raise ValueError("Dejanos un email o un teléfono para contactarte")
        return self


# ---------- API de inferencia (LLM, STT, TTS) ----------

class ChatCompletionIn(BaseModel):
    """Compatible con OpenAI. `model` se acepta (los SDK lo piden) pero lo fija la plataforma."""
    model: str | None = None
    messages: list[dict[str, Any]] = Field(min_length=1)
    stream: bool = False
    max_tokens: int | None = Field(default=None, ge=1)
    max_completion_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    stop: str | list[str] | None = None
    seed: int | None = None
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    response_format: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    n: int | None = Field(default=None, description="Solo 1")


class SpeechIn(BaseModel):
    model: str | None = None
    input: str = Field(min_length=1, description="Texto a sintetizar (hasta INFERENCE_TTS_MAX_CHARS)")
    voice: str = Field(description="Una de GET /inference/voices")
    response_format: Literal["wav", "pcm"] | None = Field(
        default=None,
        description="wav (default): archivo completo. pcm: 24 kHz, mono, 16 bits, a medida que se sintetiza")
    stream_format: Literal["audio", "sse"] = Field(
        default="audio", description="audio: los bytes. sse: eventos speech.audio.delta/done (solo con pcm)")


class InferenceModelOut(BaseModel):
    id: str
    object: str = "model"
    owned_by: str
    engine: Literal["llm", "stt", "tts"]


class InferenceModelsOut(BaseModel):
    object: str = "list"
    data: list[InferenceModelOut]


class MeterOut(BaseModel):
    used: float
    limit: int | None = Field(description="None: ilimitado; 0: no incluido en el plan")
    remaining: float | None


class InferenceRequestsOut(BaseModel):
    llm: int
    stt: int
    tts: int


class InferenceKeyUsageOut(BaseModel):
    key_id: str
    name: str
    prefix: str
    revoked: bool
    scopes: list[str]
    requests: InferenceRequestsOut
    llm_input_tokens: int
    llm_output_tokens: int
    tts_minutes: float
    stt_minutes: float


class InferenceUsageOut(BaseModel):
    """Consumo del mes de la API de inferencia contra los limites del tier."""
    month: str
    period_start: datetime.date
    period_end: datetime.date = Field(description="Exclusivo")
    rate_limit: int | None = Field(description="Pedidos por minuto; None: ilimitado")
    llm_input_tokens: MeterOut
    llm_output_tokens: MeterOut
    tts_minutes: MeterOut
    stt_minutes: MeterOut
    requests: InferenceRequestsOut
    keys: list[InferenceKeyUsageOut]
