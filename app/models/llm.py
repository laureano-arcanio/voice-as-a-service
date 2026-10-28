"""Conexiones de LLM de un cliente (BYOK, docs/features/LLM_CONEXIONES.md): proveedor externo, su API key
(cifrada con WA_TOKEN_KEY) y el modelo por defecto. Los agentes las referencian por id desde
`Workflow.llm`."""
import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ._common import IdMixin, TimestampMixin


class LlmConnection(IdMixin, TimestampMixin, Base):
    __tablename__ = "llm_connections"

    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    # openai_compatible | openrouter | anthropic
    kind: Mapped[str] = mapped_column(String(24))
    base_url: Mapped[str] = mapped_column(String(255))
    api_key_enc: Mapped[str] = mapped_column(Text)
    last4: Mapped[str] = mapped_column(String(8), default="")
    default_model: Mapped[str] = mapped_column(String(128), default="")
    # Como pedir JSON: json_schema (estricto) | json_object | prompt (el esquema va en el prompt).
    # Lo detecta el test de la conexion.
    json_mode: Mapped[str] = mapped_column(String(16), default="json_schema", server_default="json_schema")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_test_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_test_detail: Mapped[str] = mapped_column(String(255), default="")
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
