from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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
    id: str
    version: int
    agent: AgentInfo
    objective: Objective
    conversation: ConversationConfig
    knowledge: str = ""
    fields: dict[str, FieldSpec]
    completion: Completion


class Message(BaseModel):
    role: Literal["assistant", "user"]
    text: str
    # En las respuestas del agente: la llamada al LLM del turno, con su salida
    # tal cual (para el dashboard).
    llm: list[dict[str, Any]] | None = None


class Progress(BaseModel):
    """Registro de la app; no decide el flujo."""
    rejected: dict[str, Any] = Field(default_factory=dict)   # valores invalidos de la ultima extraccion (se le informan al LLM)
    outcome: str | None = None                               # Outcome.id al completar (para el dashboard)
    undo: dict[str, Any] | None = None                       # estado previo al ultimo turno (retract_last_turn)
    asked: str | None = None                                 # objetivo que pregunto el ultimo mensaje del agente
    # Objetivos que el LLM dio por respondidos pero la extraccion no encontro:
    # no se vuelven a preguntar, y sin el dato el workflow queda incompleto.
    answered_empty: list[str] = Field(default_factory=list)


class ConversationState(BaseModel):
    conversation_id: str
    workflow_id: str
    status: Literal["active", "completed"] = "active"
    fields: dict[str, Any]
    messages: list[Message] = Field(default_factory=list)
    progress: Progress = Field(default_factory=Progress)


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
