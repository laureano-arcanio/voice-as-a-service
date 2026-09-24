from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    name: str
    role: str
    language: str


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
    rejected: dict[str, Any] = Field(default_factory=dict)   # valores invalidos del ultimo turno (se le informan al LLM)
    outcome: str | None = None                               # Outcome.id al completar (para el dashboard)
    undo: dict[str, Any] | None = None                       # estado previo al ultimo turno (retract_last_turn)


class ConversationState(BaseModel):
    conversation_id: str
    workflow_id: str
    status: Literal["active", "completed"] = "active"
    fields: dict[str, Any]
    messages: list[Message] = Field(default_factory=list)
    progress: Progress = Field(default_factory=Progress)


class AgentTurn(BaseModel):
    field_updates: dict[str, Any] = Field(default_factory=dict)
    next_objective: str | None = None
    assistant_message: str
    status: Literal["active", "completed"] = "active"
    # Salida cruda del LLM y su razonamiento; no son parte del contrato.
    raw: str | None = Field(default=None, exclude=True)
    reasoning: str | None = Field(default=None, exclude=True)
