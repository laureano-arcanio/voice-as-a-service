"""OAuth 2.1 del servidor MCP (docs/features/MCP.md): los agentes de IA (Claude.ai, ChatGPT, Cursor...)
se conectan con el login del panel en vez de una API key.

- OAuthClient: la app que pide acceso. Por registro dinámico (RFC 7591) o por Client ID Metadata Document
  (el client_id es la URL de un JSON del cliente).
- OAuthGrant: el permiso que dio un usuario a esa app para actuar en un cliente (empresa). Revocarlo corta
  todos sus tokens: es lo que se ve en "Agentes conectados".
- OAuthCode: el código de autorización, de un solo uso, atado a PKCE, al redirect_uri y al recurso.
- OAuthToken: access (1 h) y refresh (30 días, con rotación). Se guarda el SHA-256, como las API keys.
- McpToolUsage: uso del MCP por herramienta, cliente y día (fase 5): llamadas, errores y tiempo.
"""
import datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin


class OAuthClient(Base):
    __tablename__ = "oauth_clients"
    # Aleatorio (registro dinámico) o la URL del metadata document.
    id: Mapped[str] = mapped_column(String(512), primary_key=True)
    kind: Mapped[str] = mapped_column(String(8))                 # dcr | cimd
    name: Mapped[str] = mapped_column(String(128), default="")
    client_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    redirect_uris: Mapped[list] = mapped_column(JSONDoc, default=list)
    # Solo los confidenciales (token_endpoint_auth_method client_secret_*): SHA-256 del secreto.
    secret_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    # cimd: cuándo se leyó el documento (se vuelve a leer pasado un día).
    fetched_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class OAuthGrant(IdMixin, Base):
    __tablename__ = "oauth_grants"
    oauth_client_id: Mapped[str] = mapped_column(String(512), ForeignKey("oauth_clients.id", ondelete="CASCADE"),
                                                 index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # El cliente (empresa) en el que actúa: el del usuario, o el que eligió un admin. None: un admin que
    # autorizó "Toda la plataforma" (actúa como admin, con el toolset `admin`).
    client_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"),
                                                  index=True, nullable=True)
    scope: Mapped[str] = mapped_column(String(64), default="mcp")
    resource: Mapped[str] = mapped_column(String(512))           # la URL del MCP para la que vale
    # User.session_version al dar el permiso: cambiar la clave o cerrar todas las sesiones lo corta.
    session_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class OAuthCode(Base):
    __tablename__ = "oauth_codes"
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    grant_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_grants.id", ondelete="CASCADE"), index=True)
    redirect_uri: Mapped[str] = mapped_column(Text)
    code_challenge: Mapped[str] = mapped_column(String(128))     # S256
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class OAuthToken(IdMixin, Base):
    __tablename__ = "oauth_tokens"
    grant_id: Mapped[str] = mapped_column(String(36), ForeignKey("oauth_grants.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(8))                 # access | refresh
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class McpToolUsage(IdMixin, Base):
    """Una fila por día (en BILLING_TIMEZONE), cliente y herramienta. client_id None: un admin que actúa en
    toda la plataforma. Sin argumentos ni respuestas: solo cuántas, cuántas fallaron y cuánto tardaron."""
    __tablename__ = "mcp_tool_usage"
    __table_args__ = (Index("ix_mcp_tool_usage_day_client", "day", "client_id"),)
    day: Mapped[datetime.date] = mapped_column(Date)
    client_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"),
                                                  nullable=True)
    tool: Mapped[str] = mapped_column(String(64))
    calls: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    errors: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_ms: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
