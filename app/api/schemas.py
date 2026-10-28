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


class LegalVersionOut(BaseModel):
    document: Literal["terms", "privacy"]
    title: str
    version: str = Field(description="Fecha de publicacion, AAAA-MM-DD")
    sha256: str = Field(description="Huella del texto exacto de esa version")
    url: str = Field(description="Link permanente a esa version")


HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class BrandingPublicOut(BaseModel):
    """La marca con la que los usuarios de un cliente ven el panel (docs/ARQUITECTURA.md)."""
    slug: str = Field(description="El `c=` del login: el panel recuerda la ultima marca que mostro")
    name: str = Field(description="Nombre del cliente: titulo de las pestañas y texto si no hay logo")
    logo_url: str | None = Field(description="Ruta del logo (publica, cacheable); null = el nombre en texto")
    logo_ratio: float | None = Field(description="Ancho / alto del logo, para reservar el lugar")
    color_primary: str = Field(description="La accion: botones, links, seleccion, primera serie de los graficos")
    color_header: str = Field(description="Fondo de la barra superior")
    color_accent: str = Field(description="Segunda serie de los graficos y detalles")
    header_fg: str = Field(description="Texto e iconos de la barra: #ffffff o la tinta, segun el contraste")
    powered_by: bool = Field(description='Mostrar "Con tecnologia de Atentina" al pie del menu')


class BrandingIn(BaseModel):
    enabled: bool = Field(description="Mostrar el panel con esta marca (si el plan la incluye)")
    color_primary: str = Field(pattern=HEX_COLOR, description="#rrggbb; tiene que dar 4,5:1 con blanco")
    color_header: str = Field(pattern=HEX_COLOR)
    color_accent: str = Field(pattern=HEX_COLOR)
    powered_by: bool = True


class BrandingOut(BrandingIn):
    logo_url: str | None
    logo_ratio: float | None
    header_fg: str
    available: bool = Field(description="El plan del cliente incluye la marca blanca")
    active: bool = Field(description="Se esta mostrando: enabled y el plan la incluye")


class MeOut(BaseModel):
    id: str
    email: str
    name: str
    role: Literal["admin", "client"]
    client_id: str | None
    client_name: str | None
    # Marca blanca resuelta del cliente del usuario (null: el panel de Atentina).
    branding: BrandingPublicOut | None = None
    # Usuario de cliente que todavia no cerro el pop-up de bienvenida.
    welcome_pending: bool = False
    # Versiones vigentes de las condiciones y la politica que el usuario no acepto: el panel pide aceptarlas.
    legal_pending: list[LegalVersionOut] = []
    # Un admin que entró como este cliente (header X-Atentina-Client): id, email y name son los del admin.
    support: bool = False


class LegalAcceptIn(BaseModel):
    """Las versiones de `legal_pending`; la de un documento ya aceptado puede ir vacia."""
    terms_version: str = Field(default="", max_length=16)
    privacy_version: str = Field(default="", max_length=16)


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
    # Campañas y agenda de contactos (docs/features/CAMPANAS.md). None: ilimitado; 0: no incluido.
    campaign_channels: list[CampaignChannel] = Field(default=[], description="Canales de campañas del plan: whatsapp, voice")
    max_campaigns_per_month: int | None = Field(default=None, ge=0, description="Campañas iniciadas por mes calendario")
    max_campaign_contacts: int | None = Field(default=None, ge=0, description="Contactos por campaña")
    max_campaign_concurrency: int | None = Field(default=None, ge=0, description="Llamadas simultaneas de una campaña de voz")
    max_contacts: int | None = Field(default=None, ge=0, description="Contactos activos en la agenda (los archivados no cuentan)")
    max_call_links: int | None = Field(default=None, ge=0, description="Links publicos para llamar a un agente (uno por agente)")
    max_team_members: int | None = Field(default=None, ge=0, description="Personas del equipo para derivar llamadas y WhatsApp")
    campaign_followup: bool = Field(default=False, description="Puede activar el seguimiento por WhatsApp de las campañas de voz")
    whatsapp: bool = Field(default=True, description="Incluye WhatsApp: cuentas, mensajes y llamadas")
    external_agent: bool = Field(default=False, description="Incluye tu propio agente: el agente del cliente "
                                                            "detras de su endpoint, con la voz de la plataforma")
    max_tools: int | None = Field(default=0, ge=0, description="Herramientas del cliente (APIs y codigo). "
                                                               "null: sin tope; 0: no incluido")
    code_tools: bool = Field(default=False, description="Las herramientas pueden ser codigo (JavaScript)")
    white_label: bool = Field(default=False, description="Marca blanca: el panel con el logo y los colores del cliente")
    advanced_reports: bool = Field(default=False, description="Reportes completos: Resultados, Mensajes, "
                                                              "Transferencias y Campañas (sin esto, Resumen y Llamadas)")
    internal: bool = Field(default=False, description="Tier de Atentina: no se ofrece como plan ni cuenta en "
                                                      "las estadisticas de la plataforma")
    direct_calls: bool = Field(default=False, description="Llamadas directas: el equipo llama y atiende desde el "
                                                          "panel, sin el agente (la saliente pide ademas salientes)")
    # Autoservicio (docs/features/COBROS.md).
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
    external_agent: bool | None = None
    max_tools: int | None = Field(default=None, ge=0)
    code_tools: bool | None = None
    white_label: bool | None = None
    advanced_reports: bool | None = None
    internal: bool | None = None
    direct_calls: bool | None = None
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
    external_agent: bool
    max_tools: int | None
    code_tools: bool
    white_label: bool
    advanced_reports: bool
    internal: bool
    direct_calls: bool
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
    "max_call_links", "max_team_members", "max_tools",
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
    projected_minutes: float | None = Field(default=None, description="A fin de mes, al ritmo del mes en curso; "
                                                                      "None en un mes pasado")


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
    # Quien atiende las entrantes (docs/features/EQUIPO_TELEFONIA.md).
    answer_mode: Literal["team", "agent"] | None = Field(
        default=None, description="team: las personas del número; agent: el agente (puede derivar con sus áreas)")
    member_ids: list[str] | None = Field(default=None, description="Personas del equipo, en el orden en que suenan; "
                                                                    "cada una con celular o usuario del panel")
    ring_first: Literal["phone", "panel"] | None = Field(
        default=None, description="Dónde suena primero: phone (el celular de cada uno, en orden) o panel (los "
                                  "Disponibles, a la vez); si nadie atiende, en el otro")
    ring_seconds: int | None = Field(default=None, ge=5, le=60, description="Timbre por persona")
    schedule: "HandoffSchedule | None" = Field(default=None, description="Horario; null = siempre")
    team_fallback: Literal["agent", "voicemail", "hangup"] | None = Field(
        default=None, description="Si nadie atiende o fuera de horario: el agente del número, mensaje y graba, o "
                                  "mensaje y corta")
    team_fallback_message: str | None = Field(default=None, max_length=500)


class AssignIn(BaseModel):
    client_id: str


class PhoneNumberMemberOut(BaseModel):
    id: str
    name: str
    phone: str | None
    user_id: str | None


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
    answer_mode: Literal["team", "agent"]
    ring_first: Literal["phone", "panel"]
    ring_seconds: int
    schedule: "HandoffSchedule | None" = None
    team_fallback: Literal["agent", "voicemail", "hangup"]
    team_fallback_message: str
    members: list[PhoneNumberMemberOut] = Field(default_factory=list, description="Las personas del número, en orden")


class SkippedNumber(BaseModel):
    number: str
    reason: str


class PhoneNumberBulkOut(BaseModel):
    created: list[PhoneNumberOut]
    skipped: list[SkippedNumber]


# ---------- whatsapp ----------

class WaAccountIn(BaseModel):
    client_id: str = Field(default="", description="Admin: el cliente. Un admin que entró como el cliente: se ignora")
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
    source: Literal["manual", "embedded_signup", "coexistence", "own_app"] = "manual"
    # own_app (la app de Meta del cliente): lo que pega en su app (Webhooks -> WhatsApp Business Account).
    webhook_url: str | None = None
    verify_token: str | None = None
    has_app_secret: bool = False
    routes: list[WaRouteOut] = Field(description="Ruteo por contacto: pisa al agente por defecto en mensajes y "
                                                  "llamadas de WhatsApp")
    created_at: UTCDateTime
    updated_at: UTCDateTime


class WaOwnAppIn(BaseModel):
    """Alta con la app de Meta propia del cliente. Con el mismo phone_number_id de una cuenta own_app del
    cliente, cambia el token y el secret (la URL de webhook y el verify token siguen iguales)."""
    agent_id: str = Field(description="Agente del cliente que atiende los mensajes")
    phone_number_id: str = Field(pattern=r"^\d{1,32}$", description="Identificador del número de teléfono (Meta)")
    waba_id: str = Field(pattern=r"^\d{1,32}$", description="Identificador de la cuenta de WhatsApp Business")
    access_token: str = Field(min_length=20, max_length=1024,
                              description="Token permanente de un usuario de sistema con whatsapp_business_messaging "
                                          "y whatsapp_business_management sobre la WABA")
    app_secret: str = Field(min_length=16, max_length=128, description="Clave secreta de la app (firma de los webhooks)")
    client_id: str | None = Field(default=None, description="Solo admin; a un usuario de cliente se le fuerza el suyo")


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
    system: str = Field(description="Prompt de sistema")


class AgentOut(ORM):
    id: str
    client_id: str
    name: str
    slug: str
    description: str
    version: int
    archived: bool
    own_agent: bool = Field(default=False, description="Tu propio agente: contesta el endpoint del cliente "
                                                       "(definition.external)")
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
    mode: Literal["llm", "external"] = Field(
        default="llm", description="llm: salida JSON (BYOK). external: el endpoint de un agente propio "
                                   "(un turno en streaming con end_call; docs/features/LLM_CONEXIONES.md)")


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


# ---------- herramientas del cliente y secretos de los agentes (docs/features/HERRAMIENTAS.md) ----------

ToolType = Literal["http", "code"]


class ToolIn(BaseModel):
    """Una herramienta del cliente. El formato de `definition` segun `type` esta en GET /tools/schema y en
    docs/features/HERRAMIENTAS.md."""
    slug: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$",
                      description="Nombre con el que la ve el agente y la referencia la definicion (tools[].tool)")
    type: ToolType
    definition: dict[str, Any] = Field(description="description, confirm, messages, response, assign y, segun el "
                                                   "tipo, http {method, url, path, query, headers, body, auth, ...} o "
                                                   "parameters, code, secrets, allowed_hosts, timeout_ms")


class ToolUpdate(BaseModel):
    type: ToolType
    definition: dict[str, Any]


class ToolAgentRef(BaseModel):
    id: str
    slug: str
    name: str


class ToolOut(BaseModel):
    id: str
    slug: str
    type: ToolType
    definition: dict[str, Any]
    revision: int
    secrets: list[str] = Field(description="Secretos que usa (con su credencial): del cliente o de cada agente que "
                                           "la use")
    llm_tool: dict[str, Any] | None = Field(description="Lo que ve el modelo (formato de function calling de OpenAI)")
    used_by: list[ToolAgentRef]
    last_test_at: UTCDateTime | None
    last_test_ok: bool | None
    last_test_detail: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ToolVersionOut(ORM):
    revision: int
    type: ToolType
    definition: dict[str, Any]
    created_by: str | None
    created_at: UTCDateTime


class ToolTestIn(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict, description="Los argumentos, como los mandaria el agente")
    agent_id: str | None = Field(default=None, description="Usa los secretos propios de ese agente (sin agente, los "
                                                           "del cliente)")
    secrets: dict[str, str] | None = Field(default=None, description="Secretos para esta prueba (no se guardan; "
                                                                     "pisan los del cliente y los del agente)")
    call: dict[str, Any] | None = Field(default=None, description="Datos de llamada de ejemplo: id, channel, mode, "
                                                                  "from, to")


class ToolDraftTestIn(ToolTestIn):
    type: ToolType
    definition: dict[str, Any]


class ToolTestOut(BaseModel):
    ok: bool
    status: int | None = Field(description="HTTP de la API (herramientas http)")
    ms: int
    data: Any = Field(description="El resultado, con los secretos tachados")
    error: str | None
    llm: str = Field(description="Lo que recibe el agente")
    request: dict[str, Any] | None = Field(description="El pedido enviado, con los secretos tachados")
    logs: list[str] = Field(description="console.log del codigo")
    assigned: dict[str, Any]


class ToolTemplateOut(BaseModel):
    code: str
    parameters: dict[str, Any]


class AgentSecretIn(BaseModel):
    name: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$", description="Mayusculas, numeros y _ (ej. CRM_TOKEN)")
    value: str = Field(min_length=1, max_length=10000, description="No se devuelve nunca")
    description: str = Field(default="", max_length=255)


class AgentSecretPatch(BaseModel):
    value: str | None = Field(default=None, min_length=1, max_length=10000, description="Para reemplazarlo")
    description: str | None = Field(default=None, max_length=255)


class AgentSecretOut(BaseModel):
    name: str
    description: str
    last4: str = Field(description="Ultimos 4 caracteres (vacio si el valor es corto)")
    used_by: list[str] = Field(description="Herramientas del agente que lo piden")
    missing: bool = Field(description="Lo pide una herramienta del agente y no esta ni en el agente ni en el cliente")
    source: Literal["agent", "client"] | None = Field(
        description="agent: propio del agente; client: lo usa del cliente; null: falta")
    overrides: bool = Field(description="Es propio del agente y pisa uno del cliente con el mismo nombre")
    created_at: UTCDateTime | None
    updated_at: UTCDateTime | None


class SecretPromoteOut(BaseModel):
    moved: int = Field(description="Agentes que dejaron de tener su propio valor (tenian el mismo)")


class SecretAgentRef(BaseModel):
    id: str
    name: str


class ClientSecretOut(BaseModel):
    name: str
    description: str
    last4: str = Field(description="Ultimos 4 caracteres (vacio si el valor es corto)")
    missing: bool = Field(description="Lo pide una herramienta o una credencial y no esta cargado")
    used_by: list[str] = Field(description="Herramientas que lo piden")
    credentials: list[str] = Field(description="Credenciales que guardan su valor en este secreto")
    agents: list[SecretAgentRef] = Field(description="Agentes con su propio valor (pisa al del cliente)")
    created_at: UTCDateTime | None
    updated_at: UTCDateTime | None


class CredentialIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$", description="Con el que la usa una herramienta "
                                                                       "(auth.credential)")
    name: str = Field(min_length=1, max_length=120, description="Para reconocerla (ej. API del CRM)")
    description: str = Field(default="", max_length=255)
    auth: dict[str, Any] = Field(description="Tipo (bearer, api_key, basic, oauth2_client_credentials) y sus datos, "
                                             "como `auth` de una herramienta (get_tool_schema); `secret` es el nombre "
                                             "del secreto del cliente con el valor")
    value: str | None = Field(default=None, min_length=1, max_length=10000,
                              description="El token, la key, la clave o el client secret: se guarda en el secreto "
                                          "`auth.secret` del cliente (lo crea o lo reemplaza). Sin value, el secreto "
                                          "ya tiene que existir. No se devuelve nunca")


class CredentialUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)
    auth: dict[str, Any]
    value: str | None = Field(default=None, min_length=1, max_length=10000,
                              description="Para reemplazar el valor; sin value queda el que esta")


class CredentialOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    type: str
    auth: dict[str, Any] = Field(description="Sin valores: `secret` es el nombre del secreto")
    secret: str
    secret_set: bool = Field(description="El cliente tiene cargado el secreto")
    used_by: list[str] = Field(description="Herramientas que la usan")
    created_at: UTCDateTime
    updated_at: UTCDateTime


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
    """Catalogo de parametros para el editor del agente: el de cada proveedor y los del LLM local (su
    configuracion; lo que no aparece lo decide el servidor)."""
    local_model: str
    local_defaults: dict[str, Any]
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


# ---------- llamadas directas (docs/features/EQUIPO_TELEFONIA.md) ----------

class DirectCallIn(BaseModel):
    contact_id: str | None = Field(default=None, description="Contacto de la agenda (marca su teléfono)")
    phone: str | None = Field(default=None, description="E.164, sin contacto")
    from_number_id: str | None = Field(default=None, description="Número del cliente para el caller ID; sin él, "
                                                                  "el primero")
    confirm_opted_out: bool = Field(default=False, description="El contacto pidió no recibir llamadas y se llama "
                                                               "igual (queda registrado); sin esto, 409 opted_out")
    user_id: str | None = Field(default=None, description="Por API key o MCP: el usuario del cliente que va a "
                                                          "hablar (abre join_url con su sesión). Desde el panel, "
                                                          "el de la sesión")

    @model_validator(mode="after")
    def _contact_or_phone(self):
        if not self.contact_id and not self.phone:
            raise ValueError("Indicá contact_id o phone")
        return self


class DirectCallOut(BaseModel):
    conversation_id: str
    room: str
    status: str
    livekit_url: str
    token: str | None = Field(default=None, description="Con sesión: el token del usuario para entrar a la room")
    join_url: str | None = Field(default=None, description="Por API key o MCP: la página del panel que entra a "
                                                           "la llamada con la sesión del usuario")


class DirectJoinOut(BaseModel):
    livekit_url: str
    token: str


class PresenceIn(BaseModel):
    available: bool


class PresenceOut(BaseModel):
    available: bool
    last_seen: UTCDateTime | None


class RingingOut(BaseModel):
    conversation_id: str
    phone: str | None
    contact_id: str | None = None
    contact_name: str | None = None
    number_e164: str | None
    number_label: str | None
    started_at: UTCDateTime


class TeamPresenceOut(BaseModel):
    user_id: str
    team_member_id: str | None = None
    name: str
    available: bool = Field(description="Disponible en el panel para atender")
    busy: bool = Field(description="En una llamada")


class DirectCallSettings(BaseModel):
    recording_notice: bool = Field(description="Avisar \"Esta llamada está siendo grabada\" al empezar las "
                                               "llamadas directas (siempre se graban)")


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
    # Llamadas directas (docs/features/EQUIPO_TELEFONIA.md): quien llamo o atendio, quien atiende la entrante y si se
    # llamo a un contacto dado de baja con confirmacion.
    user_id: str | None = None
    user_name: str | None = None
    answered_by: Literal["agent", "team"] | None = None
    opted_out_confirmed: bool = False
    contact_id: str | None = Field(default=None, description="El contacto de la agenda con ese teléfono, si hay "
                                                             "(contact_name, si el agente no lo tomó, es el suyo)")


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


class TeamOutcome(BaseModel):
    answered: bool | None = Field(description="Si atendió alguien del equipo; null mientras suena")
    person: str | None = Field(default=None, description="Quien atendió en su celular (en el panel, user_name)")
    fallback: Literal["agent", "voicemail", "hangup"] | None = Field(
        default=None, description="Nadie atendió: el respaldo (pasó al agente, tomó un mensaje o cortó con un "
                                  "aviso); null si no se sabe (llamadas de antes)")


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
    # Llamadas directas (docs/features/EQUIPO_TELEFONIA.md): como en CallSummary.
    user_id: str | None = None
    user_name: str | None = None
    answered_by: Literal["agent", "team"] | None = None
    opted_out_confirmed: bool = False
    # El contacto de la agenda con ese telefono, si hay.
    contact_id: str | None = None
    contact_name: str | None = None
    team: TeamOutcome | None = Field(default=None, description="Entrante al equipo: si atendió alguien y, si "
                                                                 "nadie, el respaldo usado")


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
    # LLM externo (conexion BYOK) o el respaldo que contesto: docs/features/LLM_CONEXIONES.md.
    provider: str | None = None
    model: str | None = None
    fallback_from: str | None = None
    fallback_reason: str | None = None
    # Tu propio agente (definition.external, docs/features/LLM_CONEXIONES.md): ms hasta el primer texto y el error del endpoint.
    first_token_ms: int | None = None
    error: str | None = None
    # Herramienta del cliente (docs/features/HERRAMIENTAS.md): slug, type, revision, ok, status, ms y, si hubo, el pedido
    # (con los secretos tachados) y los logs del codigo.
    tool: dict[str, Any] | None = None


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


# ---------- link para llamar a un agente (docs/features/LINK_LLAMADA.md) ----------

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
    # Casilla de las condiciones y las versiones que mostro el formulario (409 terms_outdated si ya no son las
    # vigentes: GET /legal).
    accept_terms: bool = False
    terms_version: str = Field(default="", max_length=16)
    privacy_version: str = Field(default="", max_length=16)
    # Trampa para bots, como en /contact.
    website: str = Field(default="", max_length=200)


ConsumerRequestKind = Literal["revocation", "cancellation"]
ConsumerRequestStatus = Literal["open", "done", "rejected"]


class ConsumerRequestIn(BaseModel):
    """Boton de arrepentimiento (`revocation`) o de baja (`cancellation`) de la landing, sin cuenta."""
    model_config = ConfigDict(str_strip_whitespace=True)

    kind: ConsumerRequestKind
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    company: str = Field(default="", max_length=120)
    message: str = Field(default="", max_length=2000)
    turnstile_token: str = Field(min_length=1, max_length=2048)
    website: str = Field(default="", max_length=200)   # trampa para bots


class ConsumerRequestCreated(BaseModel):
    code: str = Field(description="Codigo de tramite, que tambien sale por mail")


class ConsumerRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime.datetime
    kind: ConsumerRequestKind
    code: str
    name: str
    email: str
    company: str
    message: str
    client_id: str | None
    status: ConsumerRequestStatus
    resolution: str
    resolved_at: datetime.datetime | None
    email_status: str


class ConsumerRequestPatch(BaseModel):
    status: ConsumerRequestStatus
    resolution: str = Field(default="", max_length=2000, description="Que se hizo (baja, devolucion, motivo)")


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


class SessionSwitchIn(BaseModel):
    target: Literal["phone", "panel"] = Field(description="phone: la app del teléfono; panel: el Teléfono del equipo")


class SessionSwitchOut(BaseModel):
    url: str = Field(description="A dónde ir: con el pase de sesión de un solo uso (#sesion=) si es otro host")


class SessionRedeemIn(BaseModel):
    token: str = Field(min_length=10, max_length=2048)


# ---------- cobro de los planes (docs/features/COBROS.md) ----------

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
    max_tools: int | None = None
    code_tools: bool = False
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


# ---------- contactos (agenda del cliente, docs/features/CAMPANAS.md) ----------

OptoutChannel = Literal["whatsapp", "voice", "all"]
ContactSource = Literal["manual", "csv", "api", "campaign", "inbound"]


class ContactIn(BaseModel):
    """El telefono es lo unico obligatorio: E.164 o como se escribe (351 555-1234, +54 9 351 555-1234)."""
    phone: str = Field(min_length=3, max_length=32, examples=["+54 9 351 555-1234", "3515551234"])
    name: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    notes: str | None = Field(default=None, max_length=2000, description="Nota libre sobre el contacto")


class ContactImportIn(BaseModel):
    """CSV con encabezado: columna telefono (o celular, phone, whatsapp); nombre, email
    y notas opcionales; las demas columnas se ignoran."""
    csv: str = Field(min_length=1, max_length=900_000)


class ContactPatch(BaseModel):
    """Solo los campos enviados, que reemplazan a los anteriores; el telefono no se cambia."""
    name: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    notes: str | None = Field(default=None, max_length=2000)


class ContactOut(ORM):
    id: str
    client_id: str
    phone: str
    name: str | None
    email: str | None
    notes: str | None
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
    contact_ids: list[str] = Field(min_length=1, max_length=10_000)


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


# ---------- campañas (WhatsApp y voz, docs/features/CAMPANAS.md) ----------

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
        default=None, max_length=20, description="WhatsApp: dato del contacto (nombre, telefono o email) de cada variable de la plantilla")
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
                         "team", "call_links", "external_agent", "custom_tools", "code_tools", "white_label",
                         "advanced_reports", "direct_calls"]


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


# ---------- equipo, areas de derivacion y eventos (docs/features/EQUIPO_TELEFONIA.md) ----------

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


# ---------- reportes (docs/features/REPORTES.md) ----------

class ReportPeriodOut(BaseModel):
    date_from: datetime.date
    date_to: datetime.date


class ReportByChannelOut(BaseModel):
    voice_in: int = Field(description="Teléfono entrante (también las pruebas y las conversaciones por API)")
    voice_out: int = Field(description="Teléfono saliente: del agente, de una campaña o directa de una persona")
    whatsapp: int
    web: int


class ReportKpisOut(BaseModel):
    conversations: int = Field(description="Consultas: llamadas (atendidas o no) y conversaciones de WhatsApp")
    by_channel: ReportByChannelOut
    with_agent: int = Field(description="Consultas atendidas por un agente: la base de los porcentajes (no cuenta las "
                                        "llamadas directas del equipo)")
    conversions: int = Field(description="Las que tienen todos los datos requeridos (conversion complete)")
    conversion_pct: float | None = Field(description="conversions / with_agent, en %")
    goals: int = Field(description="Las que tienen un resultado que cumple el objetivo")
    goal_pct: float | None = Field(description="goals / with_agent, en %")
    transfers: int = Field(description="Conversaciones con un pedido de derivación a una persona")
    transfers_answered: int = Field(description="Derivaciones atendidas por una persona")
    transfer_pct: float | None
    minutes: float
    finished: int = Field(description="Llamadas finalizadas")
    failed: int = Field(description="Llamadas que fallaron (estado fallida)")
    avg_duration: int | None = Field(description="Segundos, de las llamadas finalizadas")
    rejected_by_limit: int = Field(description="Llamadas rechazadas por el plan (concurrencia, cantidad o minutos)")
    wa_messages: int


class ReportSummaryDayOut(BaseModel):
    date: datetime.date
    voice_in: int
    voice_out: int
    whatsapp: int
    web: int
    transfers: int
    transfers_answered: int


class ReportSummaryOut(BaseModel):
    period: ReportPeriodOut
    kpis: ReportKpisOut
    previous: ReportKpisOut = Field(description="El mismo largo, inmediatamente antes")
    daily: list[ReportSummaryDayOut]


class ReportHeatCellOut(BaseModel):
    weekday: int = Field(description="0 = lunes")
    hour: int
    count: int


class ReportCallsDayOut(BaseModel):
    date: datetime.date
    entrante: int
    saliente: int
    directa: int
    web: int
    prueba: int


class ReportLineOut(BaseModel):
    phone_number_id: str
    number: str
    calls: int
    minutes: float
    conversion_pct: float | None


class ReportCallsAgentOut(BaseModel):
    agent_id: str
    agent_name: str
    calls: int
    minutes: float
    avg_duration: int | None
    conversion_pct: float | None
    goal_pct: float | None


class ReportCallTypeOut(BaseModel):
    type: Literal["agent", "direct", "team"] = Field(
        description="agent: la atiende o la hace el agente; direct: la hace una persona del equipo; team: "
                    "entrante que atiende el equipo")
    calls: int
    minutes: float
    avg_duration: int | None = Field(description="Segundos, de las llamadas finalizadas")


class ReportCallUserOut(BaseModel):
    user_id: str
    user_name: str
    direct: int = Field(description="Directas que hizo")
    team: int = Field(description="Entrantes del equipo que atendió")
    calls: int
    minutes: float
    avg_duration: int | None = Field(description="Segundos, de las llamadas finalizadas")


class ReportCountOut(BaseModel):
    count: int


class ReportBucketOut(ReportCountOut):
    bucket: Literal["0-15s", "15-60s", "1-3m", "3-5m", "5-10m", "10m+"]


class ReportReasonOut(ReportCountOut):
    reason: str


class ReportCallerOut(ReportCountOut):
    phone: str = Field(description="Teléfono o wa_id, sin el +")
    last_at: UTCDateTime


class ReportCallersOut(BaseModel):
    new: int = Field(description="Su primer contacto es del período")
    returning: int = Field(description="Ya había llamado o escrito antes del período")
    top: list[ReportCallerOut] = Field(description="Los que más volvieron en el período")


class ReportCallsOut(BaseModel):
    daily: list[ReportCallsDayOut]
    heatmap: list[ReportHeatCellOut]
    by_line: list[ReportLineOut]
    by_agent: list[ReportCallsAgentOut]
    by_type: list[ReportCallTypeOut] = Field(description="Siempre los tres tipos, en el orden agent, direct, team")
    by_user: list[ReportCallUserOut] = Field(description="Usuarios del panel con directas hechas o entrantes "
                                                         "del equipo atendidas")
    durations: list[ReportBucketOut] = Field(description="Llamadas finalizadas por duración")
    total: int = Field(description="Llamadas del período, con cualquier estado: lo que suman by_type y ended")
    ended: list[ReportReasonOut] = Field(description=(
        "Siempre todos, en este orden: customer_hangup, agent_end, person_hangup (cortó la persona del equipo), "
        "off_topic, hangup_by_user, team_no_answer y after_hours (entrante al equipo que nadie atendió o fuera de "
        "horario), no_answer, busy, voicemail, user_not_joined (la persona no entró a su saliente), max_duration, "
        "quota_exhausted, blocked_number, rejected, worker_error, failed (otra falla) y other"))
    early_hangups: int = Field(description="Finalizadas en menos de 15 s")
    callers: ReportCallersOut


class ReportConversionDayOut(BaseModel):
    date: datetime.date
    complete: int
    partial: int
    empty: int


class ReportOutcomesAgentOut(BaseModel):
    agent_id: str
    agent_name: str
    total: int
    complete: int
    partial: int
    empty: int
    goal: int


class ReportOutcomeOut(BaseModel):
    agent_id: str
    agent_name: str
    outcome: str
    label: str
    goal: bool
    count: int


class ReportFunnelOut(BaseModel):
    conversations: int
    with_data: int
    complete: int
    goal: int


class ReportFieldOut(BaseModel):
    agent_id: str
    agent_name: str
    field: str
    label: str
    captured: int
    total: int
    pct: float | None


class ReportVersionOut(BaseModel):
    agent_id: str
    agent_name: str
    version: int
    total: int
    conversion_pct: float | None
    goal_pct: float | None


class ReportOutcomesOut(BaseModel):
    conversion_daily: list[ReportConversionDayOut]
    by_agent: list[ReportOutcomesAgentOut]
    outcomes: list[ReportOutcomeOut]
    funnel: ReportFunnelOut
    fields: list[ReportFieldOut] = Field(description="Datos obligatorios de la versión vigente de cada agente")
    by_version: list[ReportVersionOut]


class ReportMessagesDayOut(BaseModel):
    date: datetime.date
    inbound: int
    outbound: int
    inbound_audio: int
    outbound_audio: int
    conversations: int


class ReportDeliveryOut(BaseModel):
    sent: int = Field(description="Salientes aceptados por Meta (incluye entregados y leídos)")
    delivered: int = Field(description="Entregados (incluye leídos)")
    read: int
    failed: int


class ReportFailureOut(BaseModel):
    code: str | None
    message: str | None
    count: int


class ReportConversionOut(BaseModel):
    complete: int
    partial: int
    empty: int


class ReportAccountStatusOut(BaseModel):
    at: UTCDateTime
    status: str | None
    quality_rating: str | None
    messaging_limit: str | None


class ReportAccountOut(BaseModel):
    account_id: str
    display_phone_number: str | None
    status: str | None
    quality_rating: str | None
    messaging_limit: str | None
    history: list[ReportAccountStatusOut] = Field(description="Cambios dentro del período")


class ReportMessagesOut(BaseModel):
    daily: list[ReportMessagesDayOut]
    heatmap: list[ReportHeatCellOut] = Field(description="Mensajes entrantes")
    delivery: ReportDeliveryOut
    failures: list[ReportFailureOut]
    per_conversation_avg: float | None
    conversion: ReportConversionOut
    accounts: list[ReportAccountOut]


class ReportTransfersKpisOut(BaseModel):
    requested: int
    answered: int
    not_answered: int
    unavailable: int = Field(description="Fuera de horario, sin miembros, sin canal o sin minutos")
    answer_pct: float | None
    avg_answer_seconds: float | None = Field(description="Del timbre a que atiende la persona")
    minutes: float = Field(description="Minutos salientes de los tramos a personas")


class ReportTransfersDayOut(BaseModel):
    date: datetime.date
    requested: int
    answered: int


class ReportAreaOut(BaseModel):
    area_id: str | None
    name: str
    requested: int
    answered: int
    not_answered: int
    unavailable: int


class ReportMemberOut(BaseModel):
    team_member_id: str
    name: str
    attempts: int
    answered: int
    not_answered: int
    avg_answer_seconds: float | None
    minutes: float


class ReportWaHandoffOut(BaseModel):
    assigned: int
    first_reply: int
    avg_first_reply_seconds: float | None
    reassigned: int


class ReportTransfersOut(BaseModel):
    kpis: ReportTransfersKpisOut
    daily: list[ReportTransfersDayOut]
    by_area: list[ReportAreaOut]
    by_member: list[ReportMemberOut]
    whatsapp: ReportWaHandoffOut


class ReportCampaignOut(BaseModel):
    campaign_id: str
    name: str
    channel: CampaignChannel
    status: CampaignStatus
    contacts: int
    attempts: int = Field(description="Voz: llamadas; WhatsApp: plantillas enviadas")
    reached: int = Field(description="Voz: atendidas; WhatsApp: respondidas")
    complete: int
    goal: int
    optouts: int
    minutes: float


class ReportBestHourOut(BaseModel):
    weekday: int = Field(description="0 = lunes")
    hour: int
    attempts: int
    reached: int


class ReportCampaignsOut(BaseModel):
    campaigns: list[ReportCampaignOut]
    no_contact: list[ReportReasonOut] = Field(description="busy, no_answer, voicemail, invalid, failed, other")
    best_hours: list[ReportBestHourOut]


class ReportLatencyDayOut(BaseModel):
    date: datetime.date
    p50: float | None = Field(description="Segundos, del fin del habla del cliente al primer audio (total)")
    p95: float | None
    stt_p50: float | None
    eou_p50: float | None
    llm_p50: float | None
    tts_p50: float | None


class ReportProviderOut(BaseModel):
    provider: str
    model: str | None
    turns: int
    avg_ms: int | None
    errors: int


class ReportToolOut(BaseModel):
    tool_id: str | None
    slug: str
    type: str
    runs: int
    errors: int
    error_pct: float | None
    p50_ms: float | None
    p95_ms: float | None
    last_error: str | None
    last_error_at: UTCDateTime | None


class ReportTokensDayOut(BaseModel):
    date: datetime.date
    input: int
    output: int


class ReportTokensOut(BaseModel):
    input: int
    output: int
    by_day: list[ReportTokensDayOut]


class ReportTechnicalOut(BaseModel):
    latency_daily: list[ReportLatencyDayOut]
    by_provider: list[ReportProviderOut]
    tools: list[ReportToolOut]
    turns_avg: float | None = Field(description="Mensajes del cliente por conversación")
    errors: list[ReportReasonOut] = Field(description="Llamadas fallidas por motivo")
    failed_summary_emails: int
    tokens: ReportTokensOut


class ReportClientRowOut(BaseModel):
    client_id: str
    name: str
    tier: str | None
    conversations: int
    minutes: float
    quota_pct: float | None = Field(description="% de los minutos entrantes del mes en curso; None sin límite")
    conversion_pct: float | None
    errors: int
    last_activity_at: UTCDateTime | None
    delta_pct: float | None = Field(description="Conversaciones contra el período anterior")


class ReportAlertOut(BaseModel):
    client_id: str
    name: str
    kind: Literal["near_quota", "inactive"]
    detail: str


class ReportTierCountOut(BaseModel):
    tier: str
    count: int


class ReportDayCountOut(BaseModel):
    date: datetime.date
    count: int


class ReportBusinessOut(BaseModel):
    clients_by_tier: list[ReportTierCountOut]
    signups: list[ReportDayCountOut]
    mrr_ars: int = Field(description="Suscripciones activas o vencidas en gracia por el precio de su plan")
    payments_month_ars: int = Field(description="Pagos aprobados del mes en curso")
    past_due: int
    free_to_paid: int = Field(description="Clientes del registro con su primer pago en el período")


class ReportPeakOut(BaseModel):
    date: datetime.date
    hour: int
    peak: int


class ReportDayReasonOut(BaseModel):
    date: datetime.date
    reason: str
    count: int


class ReportOperationOut(BaseModel):
    peak_concurrency: list[ReportPeakOut]
    failures: list[ReportDayReasonOut]
    rejected: list[ReportReasonOut]


class ReportPlatformOut(BaseModel):
    clients: list[ReportClientRowOut]
    alerts: list[ReportAlertOut]
    business: ReportBusinessOut
    operation: ReportOperationOut


# --- Sistema: hardware y servicio (docs/OBSERVABILIDAD.md) ---

class SystemCpuOut(BaseModel):
    util_ratio: float | None
    cores: float | None
    load1: float | None
    load5: float | None
    load15: float | None
    pressure_ratio: float | None = Field(description="PSI: fracción del tiempo con tareas esperando CPU")
    temperature_c: float | None
    power_w: float | None = Field(description="Paquete de la CPU (RAPL)")


class SystemMemoryOut(BaseModel):
    total_bytes: float | None
    available_bytes: float | None
    used_ratio: float | None
    swap_total_bytes: float | None
    swap_used_bytes: float | None
    pressure_ratio: float | None
    oom_kills_24h: float | None


class SystemDiskOut(BaseModel):
    mountpoint: str
    device: str
    size_bytes: float
    avail_bytes: float | None
    used_ratio: float | None
    days_to_full: float | None = Field(description="Al ritmo de las últimas 6 h; null si no se llena en un año")


class SystemSmartOut(BaseModel):
    device: str
    model: str
    ok: bool
    io_busy_ratio: float | None
    wear_ratio: float | None
    media_errors: float | None
    temperature_c: float | None


class SystemNetOut(BaseModel):
    iface: str
    rx_bytes_s: float | None
    tx_bytes_s: float | None
    errors_s: float | None
    drops_s: float | None


class SystemPcieOut(BaseModel):
    gen: float | None
    gen_max: float | None
    width: float | None
    width_max: float | None


class SystemGpuProcessOut(BaseModel):
    service: str | None
    memory_bytes: float | None


class SystemGpuOut(BaseModel):
    index: int | str
    name: str
    bus: str
    util_ratio: float | None
    memory_used_bytes: float | None
    memory_total_bytes: float | None
    power_w: float | None
    power_limit_w: float | None
    temperature_c: float | None
    fan_ratio: float | None
    clock_sm_mhz: float | None
    clock_mem_mhz: float | None
    pcie: SystemPcieOut
    throttle: list[str] = Field(description="Motivos de recorte del reloj activos")
    throttle_bad: bool = Field(description="Recorte por temperatura o por hardware")
    xid_errors_24h: float | None
    processes: list[SystemGpuProcessOut]


class SystemPowerOut(BaseModel):
    gpus_w: float | None
    cpu_w: float | None
    estimated_w: float | None = Field(description="GPUs + CPU; sin medidor de pared")


class SystemClockOut(BaseModel):
    offset_s: float | None
    synced: bool | None


class SystemSipOut(BaseModel):
    registration: str
    ok: bool


class SystemConnectivityOut(BaseModel):
    internet_ok: bool | None
    public_ip_ok: bool | None
    sip: list[SystemSipOut]


class SystemServiceOut(BaseModel):
    service: str
    up: bool
    healthy: float | None = Field(description="1 healthy, 0,5 starting, 0 unhealthy, null sin healthcheck")
    restarts: float | None
    cpu_cores: float | None
    memory_bytes: float | None


class SystemProbeOut(BaseModel):
    name: str
    kind: str = Field(description="interna o externa")
    target: str
    ok: bool
    duration_s: float | None


class SystemQueueOut(BaseModel):
    running: float | None
    waiting: float | None
    kv_cache_ratio: float | None = Field(None, description="KV cache en uso (del TTS, el talker); el STT no tiene")
    kv_cache_tokens: float | None = Field(None, description="KV cache total en tokens (el TTS no lo publica)")
    kv_cache_used_tokens: float | None = None


class SystemSaturationOut(BaseModel):
    inference: dict[str, SystemQueueOut]
    llm_kv_cache_ratio: float | None
    calls_active: float | None
    anura_channels_busy: float | None
    anura_channels_total: float | None
    turn_latency_p95_s: float | None


class SystemHostOut(BaseModel):
    host: str
    collector_age_s: float | None = Field(description="Segundos desde la última vuelta de atentina-hostmon")
    uptime_s: float | None
    cpu: SystemCpuOut
    memory: SystemMemoryOut
    io_pressure_ratio: float | None
    disks: list[SystemDiskOut]
    smart: list[SystemSmartOut]
    network: list[SystemNetOut]
    udp_rcvbuf_errors_s: float | None
    gpus: list[SystemGpuOut]
    power: SystemPowerOut
    clock: SystemClockOut
    connectivity: SystemConnectivityOut
    services: list[SystemServiceOut]
    probes: list[SystemProbeOut]
    saturation: SystemSaturationOut


class SystemAlertOut(BaseModel):
    name: str
    severity: str
    state: str = Field(description="firing o pending")
    summary: str
    since: str | None
    host: str


class SystemNowOut(BaseModel):
    generated_at: float
    hosts: list[SystemHostOut]
    alerts: list[SystemAlertOut]


class SystemSeriesOut(BaseModel):
    host: str
    label: str = Field(description="GPU u otra etiqueta que separa las líneas; vacío si es una por host")
    points: list[list[float | None]] = Field(description="[[epoch, valor], ...]")


class SystemHistoryOut(BaseModel):
    window: str
    step_s: int
    start: float
    end: float
    series: dict[str, list[SystemSeriesOut]]


class SystemEventOut(BaseModel):
    name: str
    severity: str
    host: str
    detail: str
    start: float
    end: float | None = Field(description="null: sigue activa")


class SystemPeakOut(BaseModel):
    host: str
    day_end: float = Field(description="Medianoche local que cierra el día (epoch)")
    cpu_util_max: float | None = None
    memory_used_max: float | None = None
    gpu_power_max_w: float | None = None
    gpu_temp_max_c: float | None = None
    gpu_util_max: float | None = None
    llm_kv_cache_max: float | None = None
    calls_active_max: float | None = None
    alerts_critical: float | None = None
