import re
from itertools import pairwise
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ..llm import params as llm_params


class AgentInfo(BaseModel):
    name: str
    role: str
    language: str
    # Voz del TTS (nombre en tts/finetune/voces.tsv); sin voz, el agente usa VLLM_TTS_VOICE.
    voice: str | None = None

    @field_validator("voice")
    @classmethod
    def _voice(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        # "default" o vacio mata el engine de vllm-tts (docs/TTS_FINETUNE.md, Trampas 8).
        if v in ("", "default"):
            raise ValueError("voice tiene que ser una voz del checkpoint, no vacia ni 'default'")
        return v


class Objective(BaseModel):
    description: str


class ConversationConfig(BaseModel):
    opening: str
    rules: list[str] = []
    # Llamadas: la apertura se sintetiza entera al guardar el agente (suena mejor que frase por
    # frase) y se reproduce ese audio (app/conversation/opening_audio.py).
    opening_audio: bool = False
    # Llamadas: espera desde que se conecta la llamada hasta que el agente empieza a hablar.
    opening_delay_ms: int = Field(default=200, ge=0, le=10_000)


class FieldSpec(BaseModel):
    priority: int
    label: str | None = None
    description: str
    # digits: como string, pero el agente de voz espera mas de silencio antes de responder
    # (DICTATED_TYPES en app/voice/worker.py), para no taparle el audio a quien lee numeros
    # con pausas (ej. un codigo de verificacion leido por una locucion).
    # phone: en las llamadas con numero (entrante, saliente, WhatsApp) se precarga con el de la otra
    # punta y el agente no lo pregunta; en las del link para llamar lo pide (engine.new_conversation).
    type: Literal["string", "integer", "boolean", "email", "email_or_phone", "choice", "digits", "phone"] = "string"
    options: list[str] | None = None  # valores posibles de un campo choice
    required: bool = False
    required_if: dict[str, Any] | None = None
    question: str


class Outcome(BaseModel):
    id: str
    label: str                                    # para el dashboard
    when: dict[str, Any] = Field(default_factory=dict)  # igualdades sobre los campos; vacio = default
    message: str                                  # cierre sugerido al LLM
    goal: bool = False                            # cumple el objetivo del workflow
    # El contacto pidio que no lo llamen mas: en una llamada de campaña, el telefono queda en la lista
    # de bajas de voz del cliente (contact_optouts, source "outcome": campaign_calls.apply_outcome_optout).
    no_contact: bool = False


class Completion(BaseModel):
    when: Literal["all_required_fields_completed"] = "all_required_fields_completed"
    outcomes: list[Outcome]


class ToolGrant(BaseModel):
    """Herramientas de una app (docs/APPS_PLAN.md) que puede usar un agente con motor assistant.
    tools: nombres del manifest de la app, o ["*"] para todas."""
    app: str
    tools: list[str] = Field(default_factory=lambda: ["*"])


class Generation(BaseModel):
    """Parametros de generacion que se le mandan al LLM (app/llm/params.py): temperatura, top_p,
    razonamiento, tope de tokens... Cada proveedor manda los que soporta y descarta el resto.
    Vacio = los defaults de la plataforma (por motor y por familia del modelo)."""
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def _validate(cls, value: dict) -> dict:
        try:
            return llm_params.validate_params(value)
        except ValueError as e:
            raise ValueError(str(e)) from None


class LlmStage(BaseModel):
    """Desde el turno `from_turn` del usuario (1 = su primer mensaje) responde este LLM.
    connection: id de una conexion del cliente (llm_connections); None = el servidor propio.
    generation: pisa el default del agente (Workflow.generation) en este tramo."""
    from_turn: int = Field(ge=1)
    connection: str | None = None
    model: str | None = None
    generation: Generation | None = None
    # Deprecado (se pliega en generation.temperature); se acepta para no romper definiciones viejas.
    temperature: float | None = Field(default=None, ge=0, le=2)

    @model_validator(mode="after")
    def _consistent(self) -> "LlmStage":
        if self.connection and not (self.model or "").strip():
            raise ValueError("model: una conexion externa necesita el modelo")
        if not self.connection and (self.model or "").strip():
            raise ValueError("connection: model solo vale con una conexion externa")
        if self.temperature is not None:
            self.generation = Generation(params={**(self.generation.params if self.generation else {}),
                                                 "temperature": self.temperature})
            self.temperature = None
        if self.generation is not None and not self.generation.params:
            self.generation = None
        return self


MAX_LLM_STAGES = 3


class LlmPlan(BaseModel):
    """Que LLM atiende cada turno de la conversacion (docs/BYOK_LLM_PLAN.md). Sin plan, el servidor
    propio en todos los turnos."""
    stages: list[LlmStage] = Field(min_length=1, max_length=MAX_LLM_STAGES)
    # Si el proveedor externo falla, ese turno lo contesta el servidor propio.
    fallback_local: bool = True

    @model_validator(mode="after")
    def _consistent(self) -> "LlmPlan":
        turns = [st.from_turn for st in self.stages]
        if turns[0] != 1:
            raise ValueError("stages: la primera etapa empieza en el turno 1")
        if any(b <= a for a, b in pairwise(turns)):
            raise ValueError("stages: from_turn tiene que crecer de una etapa a la siguiente")
        return self

    def stage_for(self, turn: int) -> LlmStage:
        return next(st for st in reversed(self.stages) if st.from_turn <= max(turn, 1))


class Workflow(BaseModel):
    """Definicion de un agente. Se guarda como JSON (agents.definition en la base,
    app/agents/templates/*.json las plantillas). id y version los fija la app: el
    slug del agente y su version."""
    id: str
    version: int
    # structured: por turno el LLM responde en JSON y otra llamada extrae los
    # datos, con estado. classic: prompt armado del YAML, conversacion
    # multiturno en texto y una sola extraccion al final. assistant: asistente
    # con herramientas de las apps del cliente (sin datos a extraer).
    engine: Literal["structured", "classic", "assistant"] = "structured"
    # Graba un WAV por mensaje/audio, localmente, con su numero en Message.recording:
    # llamadas y audios de WhatsApp (app/conversation/recordings.py).
    record_audio: bool = False
    # Llamadas: al terminar, Atentina le manda al cliente un email con el resumen (datos, resultado y
    # transcripcion; app/mail/call_summary.py). El cliente lo puede apagar para todos (clients.call_emails).
    call_summary_email: bool = False
    # WhatsApp: minutos sin mensaje del contacto para dar la conversacion por terminada y que
    # la siguiente arranque en limpio, sin el historial previo (ventana de contexto temporal).
    # None: el default global del servidor (WA_SESSION_HOURS, 1440 min = 24 hs).
    wa_session_minutes: int | None = Field(default=None, gt=0, le=60 * 24 * 90)
    # LLM por etapa de la conversacion (conexiones BYOK del cliente). None: el servidor propio.
    llm: LlmPlan | None = None
    # Parametros de generacion por defecto del agente (todo el flujo); las etapas de llm los pisan.
    generation: Generation | None = None
    agent: AgentInfo
    objective: Objective
    conversation: ConversationConfig
    knowledge: str = ""
    fields: dict[str, FieldSpec] = Field(default_factory=dict)
    completion: Completion
    tools: list[ToolGrant] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> "Workflow":
        """Lo que el motor da por sentado: las definiciones ahora se editan desde la UI."""
        if not self.fields and self.engine != "assistant":
            raise ValueError("fields: el agente necesita al menos un dato a obtener")
        if self.tools and self.engine != "assistant":
            raise ValueError("tools: solo el motor assistant usa herramientas")
        apps = [g.app for g in self.tools]
        if len(set(apps)) != len(apps):
            raise ValueError("tools: una app repetida")
        for name, spec in self.fields.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                raise ValueError(f"fields.{name}: usar minusculas, numeros y _ (ej. contact_name)")
            if spec.type == "choice" and not spec.options:
                raise ValueError(f"fields.{name}: un campo choice necesita options")
            for dep in spec.required_if or {}:
                if dep not in self.fields:
                    raise ValueError(f"fields.{name}.required_if: {dep} no es un campo")
        outcomes = self.completion.outcomes
        if not outcomes or outcomes[-1].when:
            raise ValueError("completion.outcomes: el ultimo resultado tiene que ser el default, sin when")
        ids = [o.id for o in outcomes]
        if len(set(ids)) != len(ids):
            raise ValueError("completion.outcomes: ids repetidos")
        for o in outcomes:
            for dep in o.when:
                if dep not in self.fields:
                    raise ValueError(f"completion.outcomes.{o.id}.when: {dep} no es un campo")
        if self.generation is not None and not self.generation.params:
            self.generation = None
        return self


class Message(BaseModel):
    role: Literal["assistant", "user"]
    text: str
    # En las respuestas del agente: la llamada al LLM del turno, con su salida
    # tal cual (para el dashboard).
    llm: list[dict[str, Any]] | None = None
    # WhatsApp. Usuario: el texto es la transcripcion de una nota de voz;
    # agente: la respuesta salio como nota de voz.
    voice_note: bool = False
    # Con record_audio: numero de secuencia de su WAV en CALL_RECORDINGS_DIR. En una
    # llamada telefónica/de WhatsApp, el recorte del lado de cada uno (app/voice/worker.py);
    # en WhatsApp de mensajeria, el audio entrante o la nota de voz saliente
    # (app/whatsapp/service.py). Se sirve en /calls/{id}/recordings/{n}.
    recording: int | None = None


class TurnMedia(BaseModel):
    """Modalidad del turno en curso (WhatsApp); no se guarda. Cambia el prompt
    del turno solo en el canal whatsapp (app/llm/prompt.py)."""
    user_voice_note: bool = False    # el mensaje nuevo entero es transcripcion (mezclado con texto: VOICE_NOTE_TAG por linea)
    reply_voice_note: bool = False   # la respuesta sale como nota de voz: formato para escuchar


class Progress(BaseModel):
    """Registro de la app; no decide el flujo."""
    rejected: dict[str, Any] = Field(default_factory=dict)   # valores invalidos de la ultima extraccion (se le informan al LLM)
    outcome: str | None = None                               # Outcome.id al completar (para el dashboard)
    undo: dict[str, Any] | None = None                       # estado previo al ultimo turno (retract_last_turn)
    asked: str | None = None                                 # objetivo que pregunto el ultimo mensaje del agente
    # Objetivos que el LLM dio por respondidos pero la extraccion no encontro:
    # no se vuelven a preguntar, y sin el dato el workflow queda incompleto.
    answered_empty: list[str] = Field(default_factory=list)
    # Motor assistant: accion destructiva o de envio esperando el si del usuario
    # ({tool, arguments, summary}); vale solo para el turno siguiente.
    pending: dict[str, Any] | None = None
    # Llamada de una campaña de voz (app/conversation/contact.py): los datos del contacto que van al prompt
    # y los campos que la campaña ya cargo en `fields` (el agente no los pregunta). No cambian en la conversacion.
    contact: dict[str, Any] = Field(default_factory=dict)
    preloaded: list[str] = Field(default_factory=list)


# Por donde se conversa: cambia las reglas del prompt (app/llm/prompt.py), no el agente.
Channel = Literal["voice", "whatsapp"]


class ConversationState(BaseModel):
    conversation_id: str
    # Agente (su definicion es el workflow) y version con que corre la conversacion.
    # Con plantillas (eval, tests) agent_id es el id de la plantilla.
    agent_id: str
    agent_version: int = 1
    client_id: str | None = None
    channel: Channel = "voice"
    status: Literal["active", "completed"] = "active"
    fields: dict[str, Any]
    messages: list[Message] = Field(default_factory=list)
    progress: Progress = Field(default_factory=Progress)
    # Solo el turno en curso: lo fija process_turn y no se guarda (exclude).
    media: TurnMedia = Field(default_factory=TurnMedia, exclude=True)


class AgentTurn(BaseModel):
    """Salida del LLM de conversacion. Los datos no van aca: los saca la
    extraccion, que corre aparte mientras suena la respuesta."""
    answered: bool = False          # el usuario respondio lo que pregunto el mensaje anterior
    next_objective: str | None = None
    assistant_message: str
    status: Literal["active", "completed"] = "active"
    # Salida cruda del LLM y su razonamiento; no son parte del contrato.
    raw: str | None = Field(default=None, exclude=True)
    reasoning: str | None = Field(default=None, exclude=True)


class Extraction(BaseModel):
    """Salida del LLM de extraccion: valor por campo, null si no hay dato."""
    fields: dict[str, Any]
    raw: str | None = None
    reasoning: str | None = None
