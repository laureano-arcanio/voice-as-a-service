import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


class FieldSpec(BaseModel):
    priority: int
    label: str | None = None
    description: str
    type: Literal["string", "integer", "boolean", "email", "email_or_phone", "choice"] = "string"
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


class Completion(BaseModel):
    when: Literal["all_required_fields_completed"] = "all_required_fields_completed"
    outcomes: list[Outcome]


class Workflow(BaseModel):
    """Definicion de un agente. Se guarda como JSON (agents.definition en la base,
    app/agents/templates/*.json las plantillas). id y version los fija la app: el
    slug del agente y su version."""
    id: str
    version: int
    # structured: por turno el LLM responde en JSON y otra llamada extrae los
    # datos, con estado. classic: prompt armado del YAML, conversacion
    # multiturno en texto y una sola extraccion al final.
    engine: Literal["structured", "classic"] = "structured"
    agent: AgentInfo
    objective: Objective
    conversation: ConversationConfig
    knowledge: str = ""
    fields: dict[str, FieldSpec]
    completion: Completion

    @model_validator(mode="after")
    def _consistent(self) -> "Workflow":
        """Lo que el motor da por sentado: las definiciones ahora se editan desde la UI."""
        if not self.fields:
            raise ValueError("fields: el agente necesita al menos un dato a obtener")
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
    # conversations.version al leerla (store.get): el guardado solo pisa si nadie guardo
    # en el medio (app/conversation/store.py). None: nueva o armada a mano, sin control.
    version: int | None = None
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
