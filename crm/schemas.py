"""Contrato de la API del CRM (docs/features/CRM_API.md). Lo que entra y sale por /api."""
import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Stage = Literal["nuevo", "contactado", "seguimiento", "respondio", "charla_agendada", "charla_hecha",
                "propuesta", "piloto", "cliente", "sin_respuesta", "no_interesa", "descartado"]
ContactKind = Literal["email", "phone", "whatsapp", "linkedin", "form"]
ContactLabel = Literal["persona", "area", "atencion"]
MessageKind = Literal["first", "follow_up", "other"]


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Leads ---

class SourceIn(BaseModel):
    url: str = Field(description="Pagina donde figura el dato (sitio, ficha de camara, boletin, prensa)")
    seen_at: datetime.date | None = Field(None, description="Cuando se abrio la fuente")
    title: str | None = None
    note: str | None = None


class PersonIn(BaseModel):
    name: str
    title: str | None = Field(None, description="Cargo")
    is_decision_maker: bool | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    source_url: str | None = None
    source_seen_at: datetime.date | None = None


class ContactIn(BaseModel):
    kind: ContactKind
    value: str = Field(description="Email, telefono (con codigo de pais), URL de LinkedIn o del formulario")
    label: ContactLabel | None = Field(None, description="persona (de alguien con nombre), area o atencion")
    person: str | None = Field(None, description="Nombre de la persona, si es suyo (se crea si no existe)")
    is_primary: bool | None = Field(None, description="El ★: destinatario de los mails")
    source_url: str | None = Field(None, description="Obligatorio para email, phone y whatsapp")
    source_seen_at: datetime.date | None = None
    verified_at: datetime.date | None = None


class LeadUpsert(BaseModel):
    """Alta o actualizacion. Se busca por dominio (de `domain` o `website`); si no hay, por `slug`.
    Suma personas, contactos y fuentes sin borrar los que ya estan."""
    name: str | None = Field(None, description="Obligatorio al crear")
    website: str | None = None
    domain: str | None = Field(None, description="Si falta, sale de website")
    slug: str | None = Field(None, description="utm_content de los links. Si falta, sale del nombre")
    legal_name: str | None = None
    description: str | None = Field(None, description="Rubro y que hace")
    kind: Literal["cliente", "canal"] | None = None
    industry: str | None = None
    tags: list[str] | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    stage: Stage | None = None
    next_action: str | None = None
    next_action_at: datetime.date | None = None
    do_not_contact: bool | None = None
    notes: str | None = None
    legacy_ref: str | None = None
    sources: list[SourceIn] | None = None
    people: list[PersonIn] | None = None
    contacts: list[ContactIn] | None = None


class LeadPatch(BaseModel):
    name: str | None = None
    website: str | None = None
    legal_name: str | None = None
    description: str | None = None
    kind: Literal["cliente", "canal"] | None = None
    industry: str | None = None
    tags: list[str] | None = Field(None, description="Reemplaza la lista")
    country: str | None = None
    province: str | None = None
    city: str | None = None
    stage: Stage | None = None
    next_action: str | None = None
    next_action_at: datetime.date | None = None
    do_not_contact: bool | None = None
    notes: str | None = None


class SourceOut(Out):
    id: int
    url: str
    title: str | None
    seen_at: datetime.date | None
    note: str | None


class PersonOut(Out):
    id: int
    name: str
    title: str | None
    is_decision_maker: bool
    linkedin_url: str | None
    notes: str | None
    source_id: int | None


class ContactOut(Out):
    id: int
    kind: str
    value: str
    label: str | None
    person_id: int | None
    is_primary: bool
    status: str
    verified_at: datetime.date | None
    source_id: int | None


class LeadSummary(Out):
    id: int
    slug: str
    name: str
    domain: str | None
    website: str | None
    description: str | None
    kind: str | None
    industry: str | None
    tags: list[str]
    city: str | None
    province: str | None
    stage: str
    stage_changed_at: datetime.datetime
    next_action: str | None
    next_action_at: datetime.date | None
    do_not_contact: bool
    legacy_ref: str | None
    primary_email: str | None = None
    last_out_at: datetime.datetime | None = None
    last_in_at: datetime.datetime | None = None
    ga_users: int = 0
    # Pendiente de salir: borradores para aprobar y mails en cola; y el seguimiento que le toca, si vencio
    draft_ids: list[int] = []
    queued: int = 0
    follow_up_step: int | None = None


class LeadOut(LeadSummary):
    legal_name: str | None
    country: str | None
    notes: str | None
    created_by: str
    created_at: datetime.datetime
    people: list[PersonOut]
    contacts: list[ContactOut]
    sources: list[SourceOut]


class UpsertResult(BaseModel):
    result: Literal["created", "updated"]
    lead: LeadOut


class Page(BaseModel):
    total: int
    items: list


class LeadPage(Page):
    items: list[LeadSummary]


# --- Blocklist ---

class BlockIn(BaseModel):
    value: str = Field(description="Email o dominio")
    reason: Literal["bounce", "complaint", "opt_out", "manual"] = "manual"
    note: str | None = None


class BlockOut(Out):
    id: int
    value: str
    reason: str
    note: str | None
    created_at: datetime.datetime


# --- Campanas y plantillas ---

class CampaignStep(BaseModel):
    days: int = Field(ge=1, le=60, description="Dias habiles despues del ultimo mail enviado")
    template_id: int | None = Field(None, description="Plantilla del paso. Con plantilla, el CRM arma "
                                                      "el borrador solo (campaña activa); sin ella, se elige al armarlo")


class CampaignIn(BaseModel):
    slug: str = Field(description="utm_campaign de los links, unico (ej. canales7)")
    name: str
    channel: Literal["email", "linkedin", "phone"] = "email"
    segment: str | None = Field(None, description="A quien va y por que")
    from_addr: str | None = Field(None, description="Remitente. Si falta, CRM_MAIL_FROM")
    status: Literal["draft", "active", "done"] = "active"
    started_at: datetime.date | None = None
    notes: str | None = None
    sequence: list[CampaignStep] = Field([], description="Seguimientos despues del primer mail, en orden. "
                                                         "Vacia: uno a los 4 dias habiles")


class CampaignPatch(BaseModel):
    name: str | None = None
    segment: str | None = None
    from_addr: str | None = None
    status: Literal["draft", "active", "done"] | None = None
    started_at: datetime.date | None = None
    notes: str | None = None
    sequence: list[CampaignStep] | None = None


class CampaignOut(Out):
    id: int
    slug: str
    name: str
    channel: str
    segment: str | None
    from_addr: str | None
    status: str
    started_at: datetime.date | None
    notes: str | None
    sequence: list[CampaignStep]
    created_at: datetime.datetime
    stats: dict = {}


class TemplateIn(BaseModel):
    name: str
    kind: MessageKind = "first"
    subject: str = Field(description="En un seguimiento se ignora: va 'Re: <asunto del primer mail>'")
    body: str = Field(description="A 'ustedes'. Variables: {{saludo}} {{nombre}} {{empresa}} {{link}}")
    body_personal: str | None = Field(None, description="Tuteo, cuando el destinatario es una persona con nombre")
    archived: bool = False


class TemplatePatch(BaseModel):
    name: str | None = None
    kind: MessageKind | None = None
    subject: str | None = None
    body: str | None = None
    body_personal: str | None = None
    archived: bool | None = None


class TemplateOut(Out):
    id: int
    name: str
    kind: str
    subject: str
    body: str
    body_personal: str | None
    archived: bool
    updated_at: datetime.datetime


class PreviewIn(BaseModel):
    lead_id: int
    campaign_id: int | None = None
    kind: MessageKind = "first"


class PreviewOut(BaseModel):
    to: str | None
    subject: str
    text: str


# --- Mensajes ---

class DraftIn(BaseModel):
    lead_id: int
    campaign_id: int | None = None
    kind: MessageKind = "first"
    template_id: int | None = Field(None, description="O subject + text")
    subject: str | None = None
    text: str | None = None
    to: str | None = Field(None, description="Si falta: el ★ (primer mail) o la direccion del hilo")


class MessagePatch(BaseModel):
    """Borrador: asunto y texto. Respuesta recibida: tambien canal, remitente y fecha."""
    subject: str | None = None
    text: str | None = None
    channel: Literal["email", "phone", "agent", "other"] | None = None
    from_addr: str | None = None
    at: datetime.datetime | None = None


class BulkDraftIn(BaseModel):
    lead_ids: list[int]
    template_id: int
    kind: MessageKind = "first"


class FollowUpDraftIn(BaseModel):
    lead_ids: list[int]
    template_id: int | None = Field(None, description="Si falta, la del paso en la secuencia de la campaña")


class Skipped(BaseModel):
    lead_id: int
    reason: str


class MessageOut(Out):
    id: int
    lead_id: int
    campaign_id: int | None
    kind: str
    step: int | None = None
    direction: str
    channel: str = "email"
    from_addr: str | None
    to_addr: str
    subject: str
    text: str
    status: str
    resend_id: str | None
    message_id: str | None
    in_reply_to: str | None
    utm_campaign: str | None
    error: str | None
    created_by: str
    created_at: datetime.datetime
    queued_at: datetime.datetime | None
    sent_at: datetime.datetime | None
    analysis: dict | None = None
    lead_name: str | None = None
    campaign_slug: str | None = None


class InboundEmailOut(Out):
    id: int
    resend_id: str
    from_addr: str
    to_addr: str
    subject: str
    text: str
    received_at: datetime.datetime
    status: str
    reason: str | None
    lead_id: int | None
    message_id: int | None


class AssignIn(BaseModel):
    lead_id: int


class BulkDraftOut(BaseModel):
    created: list[MessageOut]
    skipped: list[Skipped]


class MessagePage(Page):
    items: list[MessageOut]


class IdsIn(BaseModel):
    ids: list[int]


class InboundIn(BaseModel):
    channel: Literal["email", "phone", "agent", "other"] = Field(
        "email", description="Por dónde respondió: mail, teléfono, el agente de Atentina u otro")
    from_addr: str = Field("", description="Quién respondió: email, teléfono o solo el nombre (opcional)")
    subject: str = ""
    text: str = ""
    at: datetime.datetime | None = None
    auto_reply: bool = Field(False, description="Autorespuesta: se guarda pero no cambia la etapa")


class MessageImport(BaseModel):
    """Solo la key del usuario: carga historica (importacion inicial)."""
    lead_id: int
    campaign_id: int | None = None
    kind: MessageKind = "first"
    direction: Literal["out", "in"] = "out"
    from_addr: str | None = None
    to_addr: str
    subject: str
    text: str = ""
    status: Literal["sent", "delivered", "bounced", "complained", "failed", "received"] = "sent"
    resend_id: str | None = None
    message_id: str | None = None
    utm_campaign: str | None = None
    sent_at: datetime.datetime


# --- Actividad ---

class ActivityIn(BaseModel):
    kind: Literal["note", "call", "meeting", "linkedin", "task"]
    text: str
    at: datetime.datetime | None = None
    person_id: int | None = None
    due_at: datetime.date | None = Field(None, description="Para tareas")
    done: bool = True
    data: dict = {}


class ReminderIn(BaseModel):
    kind: Literal["reminder", "meeting"] = "reminder"
    starts_at: str = Field(description="'2026-10-27T11:00' (hora de Argentina si no trae zona) o '2026-10-27' "
                                       "(a las CRM_REMINDER_HOUR, 10)")
    title: str | None = Field(None, description="Si falta: 'Llamar a <persona> (<lead>)' o 'Reunión: <lead>'")
    duration_min: int | None = Field(None, ge=5, le=480, description="Por defecto 15 (recordatorio) o 30 (reunión)")
    person_id: int | None = None
    location: str | None = Field(None, description="Link de Meet o Zoom, teléfono o dirección")
    notes: str = ""


class ReminderPatch(BaseModel):
    starts_at: str | None = None
    title: str | None = None
    duration_min: int | None = Field(None, ge=5, le=480)
    person_id: int | None = None
    location: str | None = None
    notes: str | None = None


class ReminderDoneIn(BaseModel):
    outcome: str = Field("", description="Qué pasó: queda en la línea de tiempo")
    no_show: bool = Field(False, description="Reunión a la que no se presentó")


class ReminderOut(Out):
    id: int
    lead_id: int
    lead_name: str | None = None
    person_id: int | None
    kind: str
    title: str
    notes: str
    location: str | None
    starts_at: datetime.datetime
    duration_min: int
    status: str
    outcome: str | None
    done_at: datetime.datetime | None
    gcal_state: str
    gcal_error: str | None
    created_by: str
    created_at: datetime.datetime


class ActivityOut(Out):
    id: int
    lead_id: int
    person_id: int | None
    kind: str
    at: datetime.datetime
    text: str
    data: dict
    due_at: datetime.date | None
    done: bool
    created_by: str


class ActivityPatch(BaseModel):
    text: str | None = None
    done: bool | None = None
    due_at: datetime.date | None = None


# --- GA ---

class GaRow(BaseModel):
    date: datetime.date
    source_medium: str = "email / (not set)"
    utm_campaign: str
    utm_content: str
    active_users: int = 0
    sessions: int = 0
    events: int = 0


class GaVisitOut(Out):
    date: datetime.date
    source_medium: str
    utm_campaign: str
    utm_content: str
    active_users: int
    sessions: int
    events: int
    lead_id: int | None
    campaign_id: int | None
    follow_up: bool


# --- Timeline y Hoy ---

class TimelineItem(BaseModel):
    type: Literal["message", "activity", "visit", "reminder"]
    at: datetime.datetime
    data: dict


class ReplyRate(BaseModel):
    campaign_slug: str | None = Field(description="None: todas las campañas juntas")
    step: int = Field(description="Nivel: 0 el primer mail, 1.. los seguimientos")
    reached: int = Field(description="Leads que recibieron ese nivel (sin rebote)")
    replied: int = Field(description="De ellos, los que respondieron despues de ese nivel y antes del siguiente")
    rate: float = Field(description="replied / reached")


class FollowUpDue(BaseModel):
    lead: LeadSummary
    campaign_id: int | None
    campaign_slug: str | None
    step: int = Field(description="Numero de seguimiento que toca (1, 2, ...)")
    template_id: int | None = Field(description="Plantilla del paso en la secuencia")
    last_message_id: int
    sent_at: datetime.datetime = Field(description="Ultimo mail enviado")
    business_days: int
