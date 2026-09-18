import datetime

from sqlalchemy import (Boolean, DateTime, Integer, String, Text, create_engine, inspect, text)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from . import config

engine = create_engine(config.DB_DSN, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def now():
    return datetime.datetime.utcnow()


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    expected: Mapped[str] = mapped_column(Text)           # respuesta correcta de referencia
    weight: Mapped[int] = mapped_column(Integer, default=10)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    def as_dict(self):
        return {
            "id": self.id, "position": self.position, "text": self.text,
            "expected": self.expected, "weight": self.weight,
            "required": self.required, "active": self.active,
        }


class Band(Base):
    __tablename__ = "score_bands"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    min_score: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))  # rechazado | a_definir | aprobado

    def as_dict(self):
        return {"id": self.id, "min_score": self.min_score,
                "max_score": self.max_score, "outcome": self.outcome}


class Call(Base):
    __tablename__ = "calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32))
    client_name: Mapped[str] = mapped_column(String(120), default="")
    client_gender: Mapped[str] = mapped_column(String(16), default="")  # masculino | femenino | ""
    client_notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="pendiente")
    # pendiente | sonando | en_curso | finalizada | fallida
    # Llamada de prueba (sin telefono real): el agente no marca por SIP, espera
    # a que alguien se conecte a la room via LiveKit (Playground/meet.livekit.io).
    # Ver app/livekit_agent.py y el checkbox "Modo prueba" del dashboard.
    test_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str] = mapped_column(String(16), default="livekit")
    provider_call_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    ended_reason: Mapped[str] = mapped_column(String(128), default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    recording_url: Mapped[str] = mapped_column(Text, default="")
    recording_file: Mapped[str] = mapped_column(String(128), default="")
    transcript_json: Mapped[str] = mapped_column(LONGTEXT, default="")
    questions_snapshot: Mapped[str] = mapped_column(LONGTEXT, default="")
    bands_snapshot: Mapped[str] = mapped_column(LONGTEXT, default="")
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), default="")  # aprobado | a_definir | rechazado
    score_detail: Mapped[str] = mapped_column(LONGTEXT, default="")
    score_error: Mapped[str] = mapped_column(Text, default="")
    # Desglose de latencia por turno (ver app/latency.py): {turns: [...], stats: {...}}
    latency_json: Mapped[str] = mapped_column(LONGTEXT, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)

    def as_dict(self, full=False):
        d = {
            "id": self.id, "phone": self.phone, "status": self.status,
            "test_mode": bool(self.test_mode),
            "client_name": self.client_name, "client_gender": self.client_gender,
            "client_notes": self.client_notes,
            "ended_reason": self.ended_reason,
            "duration_seconds": self.duration_seconds,
            "score": self.score, "outcome": self.outcome,
            "has_recording": bool(self.recording_file),
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }
        if full:
            d.update({
                "transcript_json": self.transcript_json,
                "questions_snapshot": self.questions_snapshot,
                "bands_snapshot": self.bands_snapshot,
                "score_detail": self.score_detail,
                "score_error": self.score_error,
                "recording_file": self.recording_file,
                "provider_call_id": self.provider_call_id,
                "latency_json": self.latency_json,
            })
        return d


SEED_QUESTIONS = [
    # (texto, respuesta esperada, peso, requerida)
    ("¿Sabe usted que suscribió un plan de ahorro y no una compra directa del vehículo?",
     "El cliente reconoce que contrató un plan de ahorro (sistema de capitalización grupal), no una compra al contado ni un crédito prendario tradicional.", 13, True),
    ("¿Qué modelo de vehículo eligió en su plan?",
     "El cliente menciona correctamente el modelo contratado (coincide con lo que dice el vendedor en el pedido).", 8, False),
    ("¿En cuántas cuotas se compone su plan?",
     "El cliente conoce la cantidad de cuotas del plan (por ejemplo 84 o 120 cuotas).", 10, False),
    ("¿Conoce el valor aproximado de la cuota y sabe que es móvil?",
     "El cliente sabe el valor aproximado de la cuota y entiende que ajusta según el precio del vehículo (cuota móvil), no es fija.", 12, True),
    ("¿Sabe cómo se accede a la adjudicación del vehículo?",
     "El cliente entiende que la adjudicación es por sorteo o licitación mensual, y que puede requerir integración mínima de cuotas.", 12, True),
    ("¿Sabe que la entrega del vehículo no es inmediata?",
     "El cliente entiende que el vehículo se entrega recién al resultar adjudicado, no al firmar.", 10, False),
    ("¿Le informaron los gastos administrativos y otros cargos del plan?",
     "El cliente sabe que la cuota incluye gastos administrativos y conoce la existencia de cargos adicionales (derecho de adjudicación, gastos de entrega, etc.).", 8, False),
    ("¿Sabe que el plan incluye seguro de vida y que el vehículo deberá estar asegurado?",
     "El cliente conoce que hay un seguro de vida sobre saldo deudor incluido y que el vehículo adjudicado debe contratar seguro.", 7, False),
    ("¿Qué sucede si se atrasa en el pago de las cuotas?",
     "El cliente entiende que la mora genera punitorios y puede afectar la adjudicación o derivar en la baja del plan.", 8, False),
    ("¿Le explicaron cómo darse de baja del plan y en qué condiciones?",
     "El cliente conoce que puede rescindir, y que la devolución de lo aportado tiene condiciones y plazos (al finalizar el grupo, con deducciones).", 7, False),
    ("¿Recibió y leyó una copia del contrato y de las condiciones generales?",
     "El cliente confirma que recibió copia del contrato / solicitud de adhesión y tuvo oportunidad de leerla.", 5, False),
]

SEED_BANDS = [
    (0, 30, "rechazado"),
    (31, 55, "a_definir"),
    (56, 100, "aprobado"),
]


# Columnas agregadas despues del primer deploy: create_all() no altera tablas que
# ya existen, asi que se agregan a mano si faltan. (nombre, DDL)
_ADDED_COLUMNS = [
    ("calls", "latency_json", "LONGTEXT NULL"),
    ("calls", "test_mode", "BOOLEAN NOT NULL DEFAULT 0"),
]


def active_questionnaire():
    """Preguntas activas + bandas de score actuales, en el mismo formato que se
    graba en calls.questions_snapshot/bands_snapshot. Compartido por
    POST /api/calls (app/main.py) y el entrypoint de llamadas entrantes
    (app/livekit_agent.py) para no duplicar la query."""
    with SessionLocal() as s:
        questions = [q.as_dict() for q in s.query(Question)
                     .filter(Question.active.is_(True))
                     .order_by(Question.position, Question.id).all()]
        bands = [b.as_dict() for b in s.query(Band).order_by(Band.min_score).all()]
        return questions, bands


def ensure_schema():
    """Crea las tablas que falten y agrega columnas nuevas a tablas existentes.
    Idempotente; la corren tanto la app como el worker del agente al arrancar."""
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            existing = {c["name"] for c in insp.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db(seed=True):
    ensure_schema()
    if not seed:
        return
    with SessionLocal() as s:
        if s.query(Question).count() == 0:
            for i, (t, e, w, req) in enumerate(SEED_QUESTIONS, start=1):
                s.add(Question(position=i, text=t, expected=e, weight=w, required=req))
        if s.query(Band).count() == 0:
            for lo, hi, oc in SEED_BANDS:
                s.add(Band(min_score=lo, max_score=hi, outcome=oc))
        s.commit()
