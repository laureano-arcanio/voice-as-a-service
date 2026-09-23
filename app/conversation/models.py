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
    type: Literal["string", "integer", "boolean", "email"] = "string"
    required: bool = False
    required_if: dict[str, Any] | None = None
    question: str


class Completion(BaseModel):
    when: Literal["all_required_fields_completed"] = "all_required_fields_completed"
    message_if_demo: str
    message_if_no_demo: str


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


class ConversationState(BaseModel):
    conversation_id: str
    workflow_id: str
    status: Literal["active", "completed"] = "active"
    fields: dict[str, Any]
    messages: list[Message] = Field(default_factory=list)


class AgentTurn(BaseModel):
    field_updates: dict[str, Any] = Field(default_factory=dict)
    next_objective: str | None = None
    assistant_message: str
    status: Literal["active", "completed"] = "active"
