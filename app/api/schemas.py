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
CampaignChannel = Literal["whatsapp", "voice"]
CampaignStatus = Literal["draft", "scheduled", "running", "paused", "done", "cancelled"]


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


class PasswordResetIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class MeOut(BaseModel):
    id: str
    email: str
    name: str
    role: Literal["admin", "client"]
    client_id: str | None
    client_name: str | None
    # Usuario de cliente que todavia no cerro el pop-up de bienvenida.
    welcome_pending: bool = False


class ProfileIn(BaseModel):
    name: str = Field(max_length=128)


class AccountCodeOut(BaseModel):
    """Desafio del codigo por mail: se manda de vuelta con el codigo."""
    challenge: str
    sent_to: str
    expires_at: datetime.datetime


class EmailCodeIn(BaseModel):
    email: EmailStr = Field(max_length=254, description="Email nuevo")


class AccountCodeIn(BaseModel):
    challenge: str = Field(min_length=10, max_length=4096)
    code: str = Field(pattern=r"^\d{6}$")


class PasswordChangeIn(AccountCodeIn):
    password: str = Field(min_length=10, max_length=256)


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
    # Campañas y agenda de contactos (docs/LLAMADAS_SALIENTES_PLAN.md). None: ilimitado; 0: no incluido.
    campaign_channels: list[CampaignChannel] = Field(default=[], description="Canales de campañas del plan: whatsapp, voice")
    max_campaigns_per_month: int | None = Field(default=None, ge=0, description="Campañas iniciadas por mes calendario")
    max_campaign_contacts: int | None = Field(default=None, ge=0, description="Contactos por campaña")
    max_campaign_concurrency: int | None = Field(default=None, ge=0, description="Llamadas simultaneas de una campaña de voz")
    max_contacts: int | None = Field(default=None, ge=0, description="Contactos activos en la agenda (los archivados no cuentan)")
    max_call_links: int | None = Field(default=None, ge=0, description="Links publicos para llamar a un agente (uno por agente)")
    max_team_members: int | None = Field(default=None, ge=0, description="Personas del equipo para derivar llamadas y WhatsApp")
    campaign_followup: bool = Field(default=False, description="Puede activar el seguimiento por WhatsApp de las campañas de voz")
    whatsapp: bool = Field(default=True, description="Incluye WhatsApp: cuentas, mensajes y llamadas")
    # Autoservicio (docs/SUSCRIPCIONES_PLAN.md).
    price_ars: int | None = Field(default=None, ge=0,
                                  description="Precio mensual en pesos, lo que se cobra. null: no se vende por el dashboard; 0: gratis")
    public: bool = Field(default=False, description="Se ofrece en el registro y en la pantalla Plan")
    sort: int = Field(default=0, description="Orden en la pantalla Plan (menor primero)")


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
    campaign_channels: list[CampaignChannel] | None = None
    max_campaigns_per_month: int | None = Field(default=None, ge=0)
    max_campaign_contacts: int | None = Field(default=None, ge=0)
    max_campaign_concurrency: int | None = Field(default=None, ge=0)
    max_contacts: int | None = Field(default=None, ge=0)
    max_call_links: int | None = Field(default=None, ge=0)
    max_team_members: int | None = Field(default=None, ge=0)
    campaign_followup: bool | None = None
    whatsapp: bool | None = None
    price_ars: int | None = Field(default=None, ge=0)
    public: bool | None = None
    sort: int | None = None


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
    campaign_channels: list[CampaignChannel]
    max_campaigns_per_month: int | None
    max_campaign_contacts: int | None
    max_campaign_concurrency: int | None
    max_contacts: int | None
    max_call_links: int | None
    max_team_members: int | None
    campaign_followup: bool
    whatsapp: bool
    price_ars: int | None
    public: bool
    sort: int
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
    created_via: Literal["admin", "signup"] = "admin"
    tier: TierBrief
    created_at: UTCDateTime
    agents_count: int = 0
    numbers_count: int = 0
    adjustments_count: int = Field(default=0, description="Ajustes de limites vigentes hoy")


class CallEmailsIn(BaseModel):
    """Resumen por email de cada llamada (app/mail/call_summary.py). Cada agente lo prende en su
    definicion (`call_summary_email`); `enabled` en false lo apaga para todos los agentes del cliente."""
    enabled: bool
    recipients: list[EmailStr] = Field(default_factory=list, max_length=10,
                                       description="Destinos; vacio = los usuarios activos del cliente")


class CallEmailsOut(CallEmailsIn):
    default_recipients: list[str] = Field(description="Usuarios activos del cliente (los destinos si recipients va vacio)")
    agents: list[str] = Field(description="Agentes del cliente (no archivados) con el resumen prendido")


# ---------- ajustes de limites por cliente ----------

# Los campos de Tier que se pueden ajustar (igual a services/limits.LIMIT_FIELDS; un test lo verifica).
LimitField = Literal[
    "max_concurrent_calls", "max_calls_per_hour", "max_calls_per_day", "max_calls_per_month",
    "inbound_minutes", "outbound_minutes", "max_phone_numbers",
    "api_llm_input_tokens", "api_llm_output_tokens", "api_tts_minutes", "api_stt_minutes", "api_rate_limit",
    "max_campaigns_per_month", "max_campaign_contacts", "max_campaign_concurrency", "max_contacts",
    "max_call_links", "max_team_members",
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


class WaRouteIn(BaseModel):
    """Una regla de ruteo por contacto: estos contactos los atiende este agente."""
    agent_id: str
    contacts: list[str] = Field(default_factory=list, max_length=500,
                                examples=[["5491155551234"]],
                                description="WhatsApp de cada contacto, con código de país")


class WaRouteOut(BaseModel):
    agent_id: str
    agent_name: str | None = None
    contacts: list[str]


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
    routes: list[WaRouteOut] = Field(description="Ruteo por contacto: pisa al agente por defecto en mensajes y "
                                                  "llamadas de WhatsApp")
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
    param_names: list[Annotated[str, Field(min_length=1, max_length=64)]] | None = Field(
        default=None, max_length=20,
        description="Atributo del contacto que completa cada variable ({{1}} = el primero); un contacto "
                    "sin `params` los toma de ahi")


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
    status: CampaignStatus
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
    engine: Literal["classic", "structured", "assistant"] | None = Field(
        default=None, description="Motor; pisa el de la definicion o la plantilla (la definicion es la misma). "
                                  "assistant: herramientas de las apps del cliente (docs/APPS_PLAN.md)")


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
    # Objetivo de la definicion (`objective.description`), para elegir el agente en "Probar agentes".
    objective: str = ""
    # URL del link para llamar activo; solo en la lista (GET /agents).
    call_link_url: str | None = None
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


ApiScope = Literal["calls", "mcp", "mcp_read", "llm", "stt", "tts"]


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    scopes: list[ApiScope] = Field(
        default=["calls"], min_length=1,
        description="calls: API de llamadas, agentes y reportes. mcp: servidor MCP (/mcp) para agentes de IA. "
                    "mcp_read: el mismo MCP, solo con las herramientas de lectura. "
                                  "llm, stt, tts: motores de la API de inferencia")


LlmConnectionKind = Literal["openai_compatible", "openrouter", "anthropic"]


class LlmConnectionIn(BaseModel):
    """Conexion a un proveedor de LLM con la clave del cliente (BYOK). La clave no se devuelve nunca."""
    name: str = Field(min_length=1, max_length=64)
    kind: LlmConnectionKind
    base_url: str | None = Field(
        default=None, max_length=255, description="Solo openai_compatible; openrouter y anthropic tienen la suya fija")
    api_key: str = Field(min_length=1, max_length=512)
    default_model: str = Field(default="", max_length=128)


class LlmConnectionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(default=None, max_length=512, description="Para rotar la clave")
    default_model: str | None = Field(default=None, max_length=128)


class LlmConnectionTestIn(BaseModel):
    model: str | None = Field(default=None, max_length=128, description="Sin modelo, el de la conexion")


class LlmConnectionOut(ORM):
    id: str
    client_id: str
    name: str
    kind: LlmConnectionKind
    base_url: str
    last4: str
    default_model: str
    json_mode: Literal["json_schema", "json_object", "prompt"]
    created_by: str | None
    created_at: UTCDateTime
    last_test_at: UTCDateTime | None
    last_test_ok: bool | None
    last_test_detail: str
    used_by: int = Field(default=0, description="Agentes vigentes que la usan")


class LlmParamSpec(BaseModel):
    """Un parametro de generacion que ofrece un proveedor (app/llm/params.py)."""
    name: str
    label: str
    type: Literal["number", "int", "bool", "choice"]
    minimum: float | None = None
    maximum: float | None = None
    choices: list[str] = []
    hint: str = ""


class LlmProviderSpec(BaseModel):
    kind: str
    label: str
    params: list[LlmParamSpec]


class LlmParamsOut(BaseModel):
    """Catalogo de parametros para el editor del agente: el de cada proveedor y los del LLM local
    (que dependen de la familia del modelo y del motor)."""
    local_model: str
    local_family: str
    local_defaults: dict[str, dict[str, Any]]
    providers: list[LlmProviderSpec]


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
    contact_id: str | None = Field(default=None, description="Contacto de la agenda: sin `phone`, marca el suyo, y "
                                                              "sus datos van a la conversacion como en una campaña")
    context: str | None = Field(default=None, max_length=2000,
                                description="Motivo del llamado en texto libre (lo que el contacto dejo en la web): "
                                            "el agente llama con ese contexto")


class CallStartedOut(BaseModel):
    conversation_id: str
    room: str
    mode: str
    join_url: str | None = None


class CallJoinOut(BaseModel):
    """Para conectarse a una llamada de prueba con el SDK de LiveKit (la pagina del panel)."""
    livekit_url: str
    token: str


class CallHangupOut(BaseModel):
    status: str
    ended_reason: str


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


class CallBulkDeleteIn(BaseModel):
    ids: list[Annotated[str, Field(max_length=36)]] = Field(min_length=1, max_length=500)


class CallBulkDeleteOut(BaseModel):
    deleted: int = Field(description="Cuantas habia de las pedidas; los ids inexistentes se ignoran")


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
    # LLM externo (conexion BYOK) o el respaldo que contesto: docs/BYOK_LLM_PLAN.md.
    provider: str | None = None
    model: str | None = None
    fallback_from: str | None = None
    fallback_reason: str | None = None


class MessageOut(BaseModel):
    role: Literal["assistant", "user"]
    text: str
    llm: list[LlmCall] | None = None
    # WhatsApp: del usuario, transcripcion de una nota de voz; del agente, enviada como nota de voz.
    voice_note: bool = False
    # Llamada con agent.record_audio: numero de su WAV (/calls/{id}/recordings/{n}), uno por mensaje.
    recording: int | None = None
    at: UTCDateTime | None = None
    # Llamada derivada: lo hablado con la persona del equipo lleva el tramo; lo que dijo ella, su nombre.
    handoff_leg: str | None = None
    person: str | None = None


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
    # Llamada suelta (pantalla Llamadas): el motivo con que se llamo.
    context: str | None = None
    # Numero de cada WAV grabado (agent.record_audio), uno por mensaje, si los hay.
    recordings: list[int] = []
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


# ---------- link para llamar a un agente (docs/LINK_LLAMADA_PLAN.md) ----------

class CallLinkIn(BaseModel):
    """Textos vacios: el nombre del agente y el del cliente. Topes en null: sin tope propio."""
    display_name: str = Field(default="", max_length=64, description="Nombre que ve quien llama")
    company_name: str = Field(default="", max_length=128, description="Empresa que ve quien llama")
    subtitle: str = Field(default="", max_length=120, description="Debajo de la empresa, ej. 'Turnos y consultas'")
    max_call_seconds: int | None = Field(default=None, ge=30, description="Duracion maxima de cada llamada")
    max_concurrent: int | None = Field(default=None, ge=0, description="Llamadas a la vez por este link")
    daily_minutes: int | None = Field(default=None, ge=0, description="Minutos por dia por este link")
    paused: bool = False


class CallLinkPatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    company_name: str | None = Field(default=None, max_length=128)
    subtitle: str | None = Field(default=None, max_length=120)
    max_call_seconds: int | None = Field(default=None, ge=30)
    max_concurrent: int | None = Field(default=None, ge=0)
    daily_minutes: int | None = Field(default=None, ge=0)
    paused: bool | None = None


class CallLinkUsageOut(BaseModel):
    calls_today: int
    seconds_today: int
    seconds_month: int


class CallLinkOut(ORM):
    id: str
    agent_id: str
    token: str
    url: str
    display_name: str
    company_name: str
    subtitle: str
    image_url: str | None = Field(description="Imagen de arriba de la pagina (null: la inicial de la empresa)")
    max_call_seconds: int
    max_concurrent: int | None
    daily_minutes: int | None
    paused: bool
    created_at: UTCDateTime
    usage: CallLinkUsageOut


class CallLinkStateOut(BaseModel):
    """El link del agente (null si no tiene) y lo que permite el plan del cliente."""
    link: CallLinkOut | None
    plan_max: int | None = Field(description="Links que incluye el plan (null: sin tope; 0: no incluido)")
    plan_used: int = Field(description="Links activos del cliente")
    enabled: bool = Field(description="El servidor tiene configurada la pagina publica (Turnstile y LiveKit)")
    default_display_name: str
    default_company_name: str


class PublicLinkOut(BaseModel):
    display_name: str
    company_name: str
    subtitle: str
    image_url: str | None
    max_call_seconds: int
    records_audio: bool
    available: bool


class PublicLinkCallIn(BaseModel):
    turnstile_token: str = Field(min_length=1, max_length=2048)


class PublicLinkCallOut(BaseModel):
    livekit_url: str
    token: str
    max_call_seconds: int


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


class SignupIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=120, description="Nombre de la empresa (el del cliente)")
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)
    turnstile_token: str = Field(min_length=1, max_length=2048)
    # Plan elegido en la landing (nombre del tier). Pago y con Mercado Pago: `card_token_id` (Card Payment
    # Brick, paso 2 del formulario) y la cuenta se crea solo si MP aprueba la tarjeta.
    plan: str = Field(default="", max_length=64, pattern=r"^[\w .-]*$")
    card_token_id: str | None = Field(default=None, max_length=128)
    # Trampa para bots, como en /contact.
    website: str = Field(default="", max_length=200)


class SignupCheckIn(BaseModel):
    email: EmailStr


class PublicPlanOut(BaseModel):
    id: str
    name: str
    price_ars: int


class PublicPlansOut(BaseModel):
    """Planes con precio que se contratan en el registro. `mp_public_key`: si viene, los pagos se pagan con
    tarjeta en el registro (Card Payment Brick)."""
    mp_public_key: str | None
    plans: list[PublicPlanOut]


class SignupOut(BaseModel):
    continue_url: str = Field(description="Link de un solo uso (10 min) que abre la sesion en el dashboard")


class HandoffIn(BaseModel):
    token: str = Field(min_length=10, max_length=2048)


# ---------- cobro de los planes (docs/SUSCRIPCIONES_PLAN.md) ----------

TaxCondition = Literal["ri", "monotributo", "exento", "cf"]
SubscriptionStatus = Literal["pending", "active", "past_due", "canceled"]
PaymentMethod = Literal["transfer", "mercadopago"]


class PlanOut(ORM):
    """Un tier publico, como se ofrece en la pantalla Plan."""
    id: str
    name: str
    description: str
    price_ars: int
    max_concurrent_calls: int | None
    inbound_minutes: int | None
    outbound_minutes: int | None
    max_phone_numbers: int | None
    api_rate_limit: int | None
    # Campañas y agenda (None = sin tope, 0 = no incluido).
    campaign_channels: list[CampaignChannel] = []
    max_campaigns_per_month: int | None = None
    max_campaign_contacts: int | None = None
    max_campaign_concurrency: int | None = None
    max_contacts: int | None = None
    max_call_links: int | None = None
    max_team_members: int | None = None
    campaign_followup: bool = False


class SubscriptionOut(BaseModel):
    id: str
    tier: TierBrief
    pending_tier: TierBrief | None
    method: PaymentMethod
    status: SubscriptionStatus
    current_period_end: datetime.date | None
    grace_until: datetime.date | None
    cancel_at_period_end: bool
    amount_due: int = Field(description="Lo que se cobra en el proximo periodo, en pesos")
    created_at: UTCDateTime


class FiscalIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    legal_name: str = Field(min_length=1, max_length=128, description="Razon social o nombre y apellido")
    tax_id: str = Field(pattern=r"^\d{11}$", description="CUIT o CUIL, 11 digitos sin guiones")
    tax_condition: TaxCondition

    @field_validator("tax_id", mode="before")
    @classmethod
    def _digits(cls, v):
        return "".join(ch for ch in v if ch.isdigit()) if isinstance(v, str) else v


class FiscalOut(BaseModel):
    legal_name: str
    tax_id: str
    tax_condition: TaxCondition | Literal[""]


class BankRow(BaseModel):
    label: str
    value: str


class PaymentOut(BaseModel):
    id: str
    client_id: str
    client_name: str = ""
    tier_name: str | None
    method: PaymentMethod
    status: Literal["approved", "rejected", "refunded"]
    amount_ars: int
    paid_on: datetime.date
    period_end: datetime.date | None
    note: str
    invoiced_at: UTCDateTime | None
    recorded_by_email: str | None = None
    # Para facturar (vista de admin).
    legal_name: str = ""
    tax_id: str = ""
    tax_condition: str = ""


class BillingOut(BaseModel):
    """Plan y cobro de un cliente: lo que muestra la pantalla Plan."""
    tier: TierBrief
    tier_price_ars: int | None
    subscription: SubscriptionOut | None
    plans: list[PlanOut]
    methods: list[PaymentMethod] = Field(description="Medios de pago disponibles")
    mp_public_key: str | None = Field(default=None, description="Public key de Mercado Pago para el formulario de tarjeta")
    fiscal: FiscalOut
    bank: list[BankRow] = Field(description="Datos para la transferencia")
    support_email: str
    payments: list[PaymentOut]
    suspended_numbers: list[str]


class SubscribeIn(BaseModel):
    """transfer: queda pedido hasta el pago. mercadopago: sin plan pago, `card_token_id` (Card Payment Brick)
    crea el debito automatico y cobra el primer mes; con uno activo, cambia el plan (sin tarjeta)."""
    tier_id: str
    method: PaymentMethod = "transfer"
    card_token_id: str | None = Field(default=None, max_length=128)


class PaymentIn(BaseModel):
    """Pago por transferencia confirmado por un admin."""
    tier_id: str
    amount_ars: int = Field(ge=0)
    paid_on: datetime.date
    note: str = Field(default="", max_length=255)


class PaymentPatch(BaseModel):
    invoiced: bool


class SubscriptionRowOut(SubscriptionOut):
    """Una suscripcion en la vista Cobros (admin)."""
    client_id: str
    client_name: str


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


# --- Apps por cliente (docs/APPS_PLAN.md) ---

class AppRegisterIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    base_url: str = Field(max_length=255, description="http://app-<slug>:8000 (red interna atentina-apps)")
    token: str = Field(min_length=16, max_length=256, description="APP_TOKEN de la app; se guarda cifrado")


class AppViewOut(BaseModel):
    name: str
    title: str
    description: str = ""


class AppToolOut(BaseModel):
    name: str
    kind: str
    description: str


class AppJobOut(BaseModel):
    name: str
    title: str = ""
    hora: str
    dias: list[int] = []


class AppJobRunOut(BaseModel):
    message: str | None
    url: str | None
    entregas: list[dict[str, str]]


class AppOut(ORM):
    id: str
    slug: str
    name: str
    client_id: str | None
    client_name: str | None = None
    base_url: str
    version: str
    status: str
    last_error: str | None
    last_health_at: UTCDateTime | None
    created_at: UTCDateTime
    views: list[AppViewOut] = []
    tools: list[AppToolOut] = []
    jobs: list[AppJobOut] = []


class AppLinkIn(BaseModel):
    view: str
    params: dict[str, str | int] = {}


class AppLinkOut(ORM):
    id: str
    view: str
    params: dict[str, Any]
    created_by: str
    created_at: UTCDateTime
    expires_at: UTCDateTime
    revoked_at: UTCDateTime | None
    opens: int
    last_opened_at: UTCDateTime | None
    url: str | None = Field(default=None, description="Solo al crearlo: el token no se guarda")


class WaOperatorIn(BaseModel):
    account_id: str
    wa_id: str = Field(pattern=r"^\d{8,15}$", description="Como lo manda Meta, sin + (549351...)")
    client_id: str
    agent_id: str
    name: str = Field(default="", max_length=128)


class WaOperatorUpdate(BaseModel):
    agent_id: str | None = None
    name: str | None = Field(default=None, max_length=128)
    active: bool | None = None


class WaOperatorOut(ORM):
    id: str
    account_id: str
    account_number: str | None = None
    wa_id: str
    client_id: str
    client_name: str | None = None
    agent_id: str
    agent_name: str | None = None
    name: str
    active: bool
    created_at: UTCDateTime


# ---------- contactos (agenda del cliente, docs/LLAMADAS_SALIENTES_PLAN.md) ----------

OptoutChannel = Literal["whatsapp", "voice", "all"]
ContactSource = Literal["manual", "csv", "api", "campaign", "inbound"]
ContactScalar = str | int | float | bool | None


class ContactIn(BaseModel):
    """El telefono es lo unico obligatorio: E.164 o como se escribe (351 555-1234, +54 9 351 555-1234)."""
    phone: str = Field(min_length=3, max_length=32, examples=["+54 9 351 555-1234", "3515551234"])
    name: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    external_id: str | None = Field(default=None, max_length=128, description="Id en el sistema del cliente")
    attributes: dict[str, ContactScalar] = Field(default={}, description='Datos libres: {"deuda": 15000}')
    tags: list[str] = Field(default=[], max_length=20, description="Etiquetas: letras, numeros y _ . : -")


class ContactImportIn(BaseModel):
    """CSV con encabezado: columna telefono (o celular, phone, whatsapp); nombre, email, external_id
    y etiquetas (separadas por | o ;) opcionales; las demas columnas son atributos."""
    csv: str = Field(min_length=1, max_length=900_000)
    tags: list[str] = Field(default=[], max_length=20, description="Etiquetas que se suman a todos")


class ContactPatch(BaseModel):
    """Solo los campos enviados. attributes y tags reemplazan a los anteriores; el telefono no se cambia."""
    name: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    external_id: str | None = Field(default=None, max_length=128)
    attributes: dict[str, ContactScalar] | None = None
    tags: list[str] | None = Field(default=None, max_length=20)


class ContactOut(ORM):
    id: str
    client_id: str
    phone: str
    name: str | None
    email: str | None
    external_id: str | None
    attributes: dict[str, Any]
    tags: list[str]
    source: ContactSource
    archived_at: UTCDateTime | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ContactPage(BaseModel):
    items: list[ContactOut]
    total: int


class ContactRejected(BaseModel):
    phone: str
    reason: str
    line: int | None = Field(default=None, description="Fila del CSV (la 1 es el encabezado)")


class ContactsUpsertOut(BaseModel):
    created: int
    updated: int
    archived: int = Field(description="De los actualizados, cuantos estan archivados (no se desarchivan solos)")
    invalid: list[ContactRejected]
    contacts: list[ContactOut] = Field(description="Los creados y actualizados")


class ContactsArchiveIn(BaseModel):
    contact_ids: list[str] = Field(default=[], max_length=10_000)
    tags: list[str] = Field(default=[], max_length=20, description="Archiva los que tengan alguna de estas etiquetas")


class ContactsArchiveOut(BaseModel):
    archived: int


class ContactOptoutIn(BaseModel):
    phone: str = Field(min_length=3, max_length=32)
    channel: OptoutChannel = Field(default="all", description="Canal que no se contacta; all: todos")


class ContactOptoutOut(BaseModel):
    client_id: str
    phone: str
    channel: OptoutChannel
    source: Literal["keyword", "outcome", "manual"]
    created_at: UTCDateTime


class BlockedNumberIn(BaseModel):
    phone: str = Field(min_length=3, max_length=32)
    note: str = Field(default="", max_length=500, description="Por qué se bloqueó (para el equipo)")


class BlockedNumberOut(BaseModel):
    client_id: str
    phone: str
    note: str
    created_at: UTCDateTime


# ---------- campañas (WhatsApp y voz, docs/LLAMADAS_SALIENTES_PLAN.md) ----------

CampaignContactStatus = Literal["pending", "in_progress", "retry", "done", "failed", "skipped"]
VoiceResult = Literal["answered", "no_answer", "busy", "voicemail", "invalid", "rejected", "failed"]


CampaignPurpose = Literal["comercial", "cobranza", "turnos", "aviso"]
FollowupResult = Literal["no_answer", "busy", "voicemail", "invalid", "rejected", "failed"]


class FollowupIn(BaseModel):
    """Seguimiento por WhatsApp de una campaña de voz: a quien termino sin atender (`after`) se le manda esta
    plantilla despues del ultimo intento. Su respuesta abre la conversacion con `agent_id` o, sin el, el agente
    de la campaña. Lo incluye el plan (`campaign_followup`)."""
    after: list[FollowupResult] = Field(default=["no_answer", "busy", "voicemail"], min_length=1, max_length=6,
                                        description="Resultados finales de la llamada que disparan el seguimiento")
    account_id: str = Field(description="Numero de WhatsApp del cliente que manda la plantilla")
    template_name: str = Field(pattern=r"^[a-z0-9_]{1,512}$", description="Plantilla aprobada de ese numero")
    template_language: str = Field(default="es_AR", pattern=r"^[a-z]{2,3}(_[A-Z]{2})?$")
    params: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(
        default=[], max_length=20, description="Dato del contacto que completa cada variable ({{1}}, {{2}}...)")
    agent_id: str | None = Field(default=None, description="Quien atiende las respuestas; sin el, el agente de la campaña")


class CampaignStartIn(BaseModel):
    """Cuerpo opcional de start y resume."""
    no_call_registry_checked: bool = Field(
        default=False, description="Una campaña comercial se inicia confirmando que la lista se filtro contra el Registro No Llame")


class CampaignContactsIn(BaseModel):
    """Los contactos de la campaña, de una o varias fuentes a la vez. Los de `contacts` y `csv` tambien
    se cargan en la agenda (upsert por telefono). Los archivados, repetidos y dados de baja no entran:
    vuelven en `skipped`."""
    contact_ids: list[str] = Field(default=[], max_length=10_000, description="Contactos de la agenda")
    tags: list[str] = Field(default=[], max_length=20, description="Los contactos activos con alguna de estas etiquetas")
    contacts: list[ContactIn] = Field(default=[], max_length=10_000, description="Contactos nuevos o a actualizar")
    csv: str | None = Field(default=None, max_length=900_000, description="CSV de contactos: como /contacts/import")
    recipients: list[WaRecipientIn] = Field(
        default=[], max_length=10_000,
        description="Solo WhatsApp: contactos con los valores de {{1}}, {{2}}... de la plantilla en orden")


class CampaignIn(CampaignContactsIn):
    """channel whatsapp: account_id y template_name (la plantilla aprobada); `param_names` dice que
    dato de cada contacto completa {{1}}, {{2}}... (["nombre", "deuda"]). channel voice: agent_id y,
    opcional, from_number_id, voice, concurrency (1: de a uno) y reintentos."""
    channel: CampaignChannel
    name: str = Field(min_length=1, max_length=128)
    client_id: str | None = Field(default=None, description="Solo admin, en voz (en WhatsApp sale del numero)")
    agent_id: str | None = Field(default=None, description="Voz: obligatorio. WhatsApp: quien atiende las respuestas; sin el, el del numero")
    rate_per_minute: int = Field(default=20, ge=1, le=600, description="Envios o arranques de llamada por minuto")
    window_start: int = Field(default=9, ge=0, le=23, description="Hora local de inicio (BILLING_TIMEZONE)")
    window_end: int = Field(default=20, ge=1, le=24, description="Hora local de fin, sin incluir")
    weekdays: list[int] | None = Field(default=None, max_length=7, description="Dias permitidos, 0 lunes a 6 domingo; null: todos")
    starts_at: datetime.datetime | None = Field(default=None, description="No arranca antes de esta fecha")
    ends_at: datetime.datetime | None = Field(default=None, description="Termina pasada esta fecha")
    start: bool = Field(default=False, description="Iniciarla de una vez, con los contactos del mismo pedido")
    purpose: CampaignPurpose | None = Field(
        default=None, description="comercial, cobranza, turnos o aviso. La comercial se inicia confirmando el Registro No Llame")
    no_call_registry_checked: bool = Field(default=False, description="Con `start`: la confirmacion del Registro No Llame")
    callback_url: str | None = Field(
        default=None, max_length=512, description="Webhook: un POST firmado por cada contacto que termina y otro al terminar la campaña")
    callback_secret: str | None = Field(
        default=None, min_length=16, max_length=128, description="Firma del webhook (HMAC-SHA256). Sin el, se genera uno y se muestra una sola vez")
    # WhatsApp.
    account_id: str | None = Field(default=None, description="WhatsApp: numero que manda la campaña")
    template_name: str | None = Field(default=None, pattern=r"^[a-z0-9_]{1,512}$", description="WhatsApp: plantilla aprobada de la WABA del numero")
    template_language: str = Field(default="es_AR", pattern=r"^[a-z]{2,3}(_[A-Z]{2})?$")
    param_names: list[Annotated[str, Field(min_length=1, max_length=64)]] | None = Field(
        default=None, max_length=20, description="WhatsApp: atributo del contacto de cada variable de la plantilla")
    # Voz.
    from_number_id: str | None = Field(default=None, description="Voz: numero del cliente que se muestra al llamar")
    voice: str | None = Field(default=None, max_length=64, description="Voz: voz del TTS; sin ella, la del agente")
    concurrency: int = Field(default=1, ge=1, le=100, description="Voz: llamadas simultaneas. 1: secuencial")
    max_attempts: int | None = Field(default=None, ge=1, le=10, description="Voz: intentos por contacto (default 3)")
    retry_minutes: int | None = Field(default=None, ge=1, le=10_080, description="Voz: minutos entre intentos (default 60)")
    retry_on: list[VoiceResult] | None = Field(default=None, description="Voz: resultados que se reintentan (default no_answer, busy, voicemail, failed)")
    followup: FollowupIn | None = Field(default=None, description="Voz: seguimiento por WhatsApp a quien no atendio; sin el, apagado")


class CampaignPatch(BaseModel):
    """Solo los campos enviados, en una campaña que no termino. agent_id null en WhatsApp: el agente del numero."""
    name: str | None = Field(default=None, min_length=1, max_length=128)
    agent_id: str | None = None
    rate_per_minute: int | None = Field(default=None, ge=1, le=600)
    window_start: int | None = Field(default=None, ge=0, le=23)
    window_end: int | None = Field(default=None, ge=1, le=24)
    weekdays: list[int] | None = Field(default=None, max_length=7)
    starts_at: datetime.datetime | None = None
    ends_at: datetime.datetime | None = None
    from_number_id: str | None = None
    voice: str | None = Field(default=None, max_length=64)
    concurrency: int | None = Field(default=None, ge=1, le=100)
    max_attempts: int | None = Field(default=None, ge=1, le=10)
    retry_minutes: int | None = Field(default=None, ge=1, le=10_080)
    retry_on: list[VoiceResult] | None = None
    purpose: CampaignPurpose | None = Field(default=None, description="null: sin finalidad. Cambiarla pide la campaña pausada")
    followup: FollowupIn | None = Field(default=None, description="Voz. null: apaga el seguimiento")
    callback_url: str | None = Field(default=None, max_length=512, description="null: apaga el webhook")
    callback_secret: str | None = Field(default=None, min_length=16, max_length=128, description="Rota la firma del webhook")


class CampaignProgress(BaseModel):
    pending: int
    in_progress: int
    retry: int
    done: int
    failed: int
    skipped: int


class CampaignOut(BaseModel):
    """La campaña y su avance (el polling: GET /campaigns/{id}). `results`: en voz, contactos por
    resultado de la llamada; en WhatsApp, sent, delivered, read y replied (acumulativos: uno leido
    tambien fue entregado y enviado)."""
    id: str
    client_id: str
    client_name: str | None = None
    channel: CampaignChannel
    name: str
    agent_id: str | None = None
    agent_name: str | None = Field(default=None, description="El de la campaña o, sin uno en WhatsApp, el del numero")
    status: CampaignStatus
    status_reason: str | None = None
    in_window: bool = Field(description="Si ahora cae en el horario y los dias permitidos")
    rate_per_minute: int
    window_start: int
    window_end: int
    weekdays: list[int] | None = None
    timezone: str
    starts_at: UTCDateTime | None = None
    ends_at: UTCDateTime | None = None
    # WhatsApp.
    account_id: str | None = None
    display_phone_number: str | None = None
    template_name: str | None = None
    template_language: str | None = None
    template_category: str | None = None
    template_body: str | None = None
    template_params: int | None = None
    param_names: list[str] | None = None
    # Voz.
    from_number_id: str | None = None
    voice: str | None = None
    concurrency: int | None = None
    max_attempts: int | None = None
    retry_minutes: int | None = None
    retry_on: list[str] | None = None
    followup_config: dict[str, Any] | None = Field(default=None, description="Voz: el seguimiento por WhatsApp configurado")
    # Finalidad y webhook.
    purpose: CampaignPurpose | None = None
    registry_confirmed: bool = Field(default=False, description="Se confirmo el Registro No Llame (campañas comerciales)")
    callback_url: str | None = None
    callback_secret: str | None = Field(
        default=None, description="Solo en la respuesta que genera el secreto del webhook: no se vuelve a mostrar")
    # Avance.
    total: int
    percent: float = Field(description="Contactos que ya no esperan nada (terminados, fallidos o salteados)")
    eta_minutes: int | None = Field(default=None, description="Al ritmo de los ultimos 15 minutos; null sin ritmo o fuera de curso")
    progress: CampaignProgress
    results: dict[str, int]
    goal: int | None = Field(default=None, description="Voz: atendidas cuya conversacion llego al objetivo del agente (solo en GET /campaigns/{id}, no en la lista)")
    minutes_used: float | None = Field(default=None, description="Voz: minutos de llamada")
    followup: dict[str, int] | None = Field(
        default=None, description="Voz con seguimiento: contactos pending, sent, replied (de los enviados), failed y skipped")
    started_at: UTCDateTime | None = None
    finished_at: UTCDateTime | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class CampaignContactsAdded(BaseModel):
    added: int
    skipped: list[ContactRejected]


class CampaignCreated(CampaignContactsAdded):
    campaign: CampaignOut


class CampaignContactOut(BaseModel):
    id: str
    contact_id: str
    phone: str
    name: str | None = None
    vars: dict[str, Any]
    status: CampaignContactStatus
    result: str | None = Field(default=None, description="Voz: el resultado de la llamada. WhatsApp: sent, delivered, read, replied o failed")
    error: dict[str, Any] | None = None
    conversation_id: str | None = None
    attempts: int
    next_attempt_at: UTCDateTime | None = None
    last_attempt_at: UTCDateTime | None = None
    sent_at: UTCDateTime | None = None
    replied_at: UTCDateTime | None = None


class CampaignContactPage(BaseModel):
    items: list[CampaignContactOut]
    total: int


class CampaignHour(BaseModel):
    hour: int = Field(ge=0, le=23, description="Hora local (zona del campo timezone)")
    attempts: int = Field(description="Llamadas marcadas (voz) o mensajes enviados (WhatsApp) en esa hora")
    reached: int = Field(description="De esas, las atendidas (voz) o las que respondieron (WhatsApp)")


class CampaignStatsOut(BaseModel):
    """Indicadores de una campaña (GET /campaigns/{id}/stats). En voz, `attempts` son las llamadas
    marcadas (con los reintentos) y `reached` las atendidas; en WhatsApp, los mensajes enviados y los
    contactos que respondieron."""
    campaign_id: str
    channel: CampaignChannel
    contacts: int
    attempts: int
    reached: int
    contact_rate: float = Field(description="reached / attempts, en %")
    goal: int = Field(description="Conversaciones que llegaron al objetivo del agente")
    goal_rate: float = Field(description="goal / reached, en %")
    avg_duration_seconds: int | None = Field(default=None, description="Voz: duracion media de las atendidas")
    minutes: float | None = Field(default=None, description="Voz: minutos de llamada, con los intentos que no se atendieron")
    results: dict[str, int] = Field(description="Voz: contactos por resultado. WhatsApp: sent, delivered, read y replied")
    by_hour: list[CampaignHour] = Field(description="Las 24 horas del dia, para elegir el horario")
    timezone: str


PlanFeatureKey = Literal["outbound_calls", "campaigns_voice", "campaigns_whatsapp", "whatsapp", "contacts",
                         "team", "call_links"]


class PlanFeatureOut(BaseModel):
    enabled: bool
    reason: str | None = Field(default=None, description="Lo que hace falta para usarla (null si esta incluida)")


class PlanFeaturesOut(BaseModel):
    """Que funciones incluye el plan del cliente (GET /plan/features)."""
    client_id: str
    tier_name: str
    free: bool = Field(description="El plan es gratis (precio 0)")
    features: dict[PlanFeatureKey, PlanFeatureOut]


class CampaignPlanOut(BaseModel):
    """Lo que el plan del cliente permite en campañas y agenda (GET /campaigns/plan), para que la UI
    deshabilite lo que no entra. None = sin tope; 0 = no incluido."""
    client_id: str
    tier_name: str
    channels: list[CampaignChannel]
    followup: bool
    max_campaigns_per_month: int | None
    campaigns_started: int = Field(description="Campañas iniciadas en el mes en curso")
    max_campaign_contacts: int | None
    max_campaign_concurrency: int | None
    max_contacts: int | None
    contacts_active: int = Field(description="Contactos activos de la agenda (los archivados no cuentan)")


class ContactCampaignOut(BaseModel):
    """Un contacto en una campaña, para su ficha (GET /contacts/{id}/campaigns)."""
    campaign_id: str
    campaign_name: str
    channel: CampaignChannel
    campaign_status: CampaignStatus
    status: Literal["pending", "in_progress", "retry", "done", "failed", "skipped"]
    result: str | None
    attempts: int
    last_attempt_at: UTCDateTime | None
    sent_at: UTCDateTime | None
    conversation_id: str | None


# ---------- pedidos a la API de inferencia ----------

class ApiRequestOut(BaseModel):
    id: str
    created_at: UTCDateTime
    client_id: str
    client_name: str
    api_key_id: str | None
    api_key_name: str | None = Field(description="None si la key se borró")
    api_key_prefix: str | None
    kind: Literal["llm", "stt", "tts"]
    stream: bool
    status: Literal["ok", "cut", "error", "rejected"] = Field(
        description="ok; cut: stream cortado (se cobra lo entregado); error: del motor o del pedido; "
                    "rejected: cupo del mes agotado o motor fuera del plan")
    http_status: int
    error_code: str | None
    duration_ms: int = Field(description="Hasta el último byte (en un stream, hasta que terminó o se cortó)")
    ttfb_ms: int | None = Field(description="Hasta el primer byte o token (stream y TTS)")
    input_tokens: int | None
    output_tokens: int | None
    audio_seconds: float | None = Field(description="Transcripto (STT) o sintetizado (TTS)")
    characters: int | None = Field(description="Largo del texto del TTS")
    voice: str | None
    response_format: str | None


class ApiRequestsSummaryOut(BaseModel):
    requests: int
    by_status: dict[str, int]
    by_kind: dict[str, int]
    input_tokens: int
    output_tokens: int
    stt_seconds: float
    tts_seconds: float
    avg_duration_ms: int | None = Field(description="De los pedidos ok")


class ApiRequestPage(BaseModel):
    items: list[ApiRequestOut]
    total: int
    summary: ApiRequestsSummaryOut = Field(description="Totales de todo el filtro, no solo de la página")


# ---------- equipo, areas de derivacion y eventos (docs/DERIVACIONES_PLAN.md) ----------

class TeamMemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32, description="Para transferir llamadas (Argentina)")
    whatsapp: str | None = Field(default=None, max_length=32, description="Para el puente de WhatsApp; único por cliente")
    user_id: str | None = Field(default=None, description="Usuario del panel (softphone web)")
    active: bool = True


class TeamMemberPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    whatsapp: str | None = Field(default=None, max_length=32)
    user_id: str | None = None
    active: bool | None = None


class TeamMemberOut(ORM):
    id: str
    client_id: str
    name: str
    phone: str | None
    whatsapp: str | None
    user_id: str | None
    active: bool
    created_at: UTCDateTime


class HandoffSchedule(BaseModel):
    """Horario semanal en la zona `tz`; `closed`: días sin atención (feriados). Sin horario = siempre."""
    tz: str = "America/Argentina/Buenos_Aires"
    week: dict[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"], list[tuple[str, str]]] = Field(
        default_factory=dict, description='Por día, franjas "HH:MM" (ej. {"mon": [["09:00", "13:00"], ["16:00", "20:00"]]})')
    closed: list[datetime.date] = Field(default_factory=list)


class HandoffAreaIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000, description="Qué atiende: lo lee el agente para elegir el área")
    active: bool = True
    member_ids: list[str] = Field(default_factory=list, description="Personas del equipo, en el orden en que se las llama")
    strategy: Literal["sequential", "round_robin"] = "sequential"
    ring_seconds: int = Field(default=20, ge=5, le=60, description="Timbre por persona (el buzón de Claro atiende a los ~33 s)")
    schedule: HandoffSchedule | None = None
    fallback: Literal["take_message"] = "take_message"
    on_person_hangup: Literal["resume", "end"] = Field(
        default="resume", description="Si la persona corta: resume (el agente vuelve) o end (se despide y corta)")
    return_digits: str = Field(default="2", max_length=4, description="Tecla de la persona para volver a la IA (sin *)")
    wa_reply_minutes: int = Field(default=10, ge=1, le=1440)
    messages: dict[str, str] = Field(default_factory=dict, description="Textos que cambian los de /handoff-areas/defaults")


class HandoffAreaPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    active: bool | None = None
    member_ids: list[str] | None = None
    strategy: Literal["sequential", "round_robin"] | None = None
    ring_seconds: int | None = Field(default=None, ge=5, le=60)
    schedule: HandoffSchedule | None = None
    fallback: Literal["take_message"] | None = None
    on_person_hangup: Literal["resume", "end"] | None = None
    return_digits: str | None = Field(default=None, max_length=4)
    wa_reply_minutes: int | None = Field(default=None, ge=1, le=1440)
    messages: dict[str, str] | None = None


class HandoffAreaOut(ORM):
    id: str
    client_id: str
    name: str
    description: str
    active: bool
    member_ids: list[str]
    strategy: str
    ring_seconds: int
    schedule: HandoffSchedule | None
    schedule_text: str = Field(description="El horario como lo dice el agente")
    open_now: bool
    fallback: str
    on_person_hangup: str
    return_digits: str
    wa_reply_minutes: int
    messages: dict[str, str] = Field(description="Solo los que cambian el default")
    created_at: UTCDateTime


class HoldMusicOut(BaseModel):
    """Temas de musica de espera para workflow.handoff.hold_music.track."""
    tracks: list[str]


class HandoffDefaultsOut(BaseModel):
    messages: dict[str, str]
    variables: list[str]


class EventOut(ORM):
    id: int
    client_id: str
    at: UTCDateTime
    type: str
    actor: str
    conversation_id: str | None
    area_id: str | None
    team_member_id: str | None
    data: dict


# ---------- OAuth del servidor MCP (app/api/oauth.py) ----------

class OAuthAuthorizeOut(BaseModel):
    """El pedido de un agente de IA para la pantalla de consentimiento. Con `valid` false, `redirect_to`
    (si viene) devuelve el error al agente; sin él, el pedido no se puede devolver."""
    valid: bool
    error: str | None = None
    error_description: str | None = None
    redirect_to: str | None = None
    client_name: str | None = None
    client_uri: str | None = None
    verified: bool = False          # el client_id es la URL de su documento (no un registro anónimo)
    redirect_host: str | None = None
    scope: str | None = None
    resource: str | None = None
    needs_client: bool = False      # admin: elegir el cliente con el que actúa el agente
    client_id: str | None = None
    client_name_tenant: str | None = None


class OAuthApproveIn(BaseModel):
    params: dict[str, Any] = Field(description="La query de /oauth/authorize, tal cual")
    approve: bool
    client_id: str | None = Field(None, description="Admin: el cliente con el que va a actuar el agente")
    platform: bool = Field(False, description="Admin: el agente actúa como admin en toda la plataforma "
                                              "(toolset `admin`), sin cliente")


class OAuthRedirectOut(BaseModel):
    redirect_to: str


class OAuthGrantOut(BaseModel):
    id: str
    client_id: str | None = Field(description="None: un admin que autorizó toda la plataforma")
    app_name: str
    app_uri: str | None
    verified: bool
    user_email: str
    created_at: UTCDateTime
    last_used_at: UTCDateTime | None


class McpToolUsageOut(BaseModel):
    tool: str
    calls: int
    errors: int
    avg_ms: int
    last_day: datetime.date


class McpUsageOut(BaseModel):
    since: datetime.date
    days: int
    calls: int
    errors: int
    tools: list[McpToolUsageOut]
