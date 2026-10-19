"""Apps por cliente (docs/APPS_PLAN.md): contenedores con API, MCP y vistas, generados desde la
plantilla de atentina-apps. Inventario como los numeros: una app se registra libre y el admin
la asigna a un cliente; sus herramientas las usa un agente con motor assistant.

app_links: links firmados a las vistas de una app (apps.atentina.com.ar). En la base va el
hash del token, no el token."""
import datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin, TimestampMixin


class App(IdMixin, TimestampMixin, Base):
    __tablename__ = "apps"
    __table_args__ = (
        CheckConstraint("status IN ('ok', 'down', 'invalid')", name="ck_apps_status"),
    )
    # Slug del manifest (sugym-gestion): nombre del contenedor (app-<slug>) y de la app en los links.
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    # NULL: inventario (registrada, sin cliente). SET NULL: si se borra el cliente vuelve al inventario.
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    base_url: Mapped[str] = mapped_column(String(255))          # http://app-<slug>:8000
    token_enc: Mapped[str] = mapped_column(Text)                 # APP_TOKEN, "fernet:..." (WA_TOKEN_KEY)
    version: Mapped[str] = mapped_column(String(32), default="")
    manifest: Mapped[dict] = mapped_column(JSONDoc, default=dict)  # copia del ultimo /manifest valido
    # ok: responde. down: no responde /health. invalid: el manifest no cumple el contrato.
    status: Mapped[str] = mapped_column(String(16), default="ok", server_default="ok")
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_health_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class AppLink(IdMixin, Base):
    __tablename__ = "app_links"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)   # SHA-256 hex del token
    app_id: Mapped[str] = mapped_column(String(36), ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    view: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict] = mapped_column(JSONDoc, default=dict)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), default="")     # wa:<wa_id>, user:<id>
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    opens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_opened_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class AppJobRun(IdMixin, Base):
    """Una corrida de un aviso programado (contrato v1.1): una por dia y job, la reclama el scheduler
    con el unique antes de llamar a la app."""
    __tablename__ = "app_job_runs"
    __table_args__ = (UniqueConstraint("app_id", "job", "run_on", name="uq_app_job_runs_day"),)
    app_id: Mapped[str] = mapped_column(String(36), ForeignKey("apps.id", ondelete="CASCADE"))
    job: Mapped[str] = mapped_column(String(64))
    run_on: Mapped[datetime.date] = mapped_column(Date)          # dia local (ASSISTANT_TIMEZONE)
    # corriendo, enviado (avisó), sin_novedades (la app devolvio message null), error
    status: Mapped[str] = mapped_column(String(16), default="corriendo")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
