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
    expected: Mapped[str] = mapped_column(Text)           # criterio de calificacion (lo usa el evaluador)
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
    outcome: Mapped[str] = mapped_column(String(20))  # frio | tibio | caliente

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
    outcome: Mapped[str] = mapped_column(String(20), default="")  # caliente | tibio | frio
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
    # Calificacion del lead (llamada comercial de Browix). "expected" es el
    # criterio que usa el evaluador (app/scoring.py) para decidir si la
    # respuesta califica; el agente no lo ve.
    # (texto, criterio de calificacion, peso, requerida)
    # El nombre no se pregunta aca: en las entrantes es INBOUND_CALLER_NAME y en
    # las salientes viene del dashboard (si falta, lo pide el prompt).
    ("¿En qué empresa trabajás?",
     "El interesado dice el nombre de su empresa.", 10, True),
    ("¿A qué se dedica la empresa?",
     "Menciona el rubro o la actividad de la empresa (por ejemplo limpieza, seguridad, logística, trade "
     "marketing, retail o gastronomía con sucursales, construcción, u otra empresa con personal a cargo).", 8, False),
    ("¿Cuántos empleados tienen, aproximadamente?",
     "Da una cantidad o un rango concreto de empleados (por ejemplo 'unos ochenta'). No califica si no lo "
     "sabe o no lo quiere decir.", 12, False),
    ("¿Dónde trabaja tu personal: en una oficina, en varias sucursales o en la calle?",
     "Describe dónde trabaja el personal. Califica si hay personal distribuido: varias sucursales, "
     "servicios en clientes, obras, o personal itinerante o en la calle.", 10, False),
    ("¿Cómo controlan hoy la asistencia y los horarios del personal?",
     "Describe el método actual, y es manual o le genera problemas: planillas, papel, WhatsApp, un reloj "
     "que no funciona bien, u otro sistema con el que no está conforme.", 10, False),
    ("¿Qué es lo que más te gustaría resolver o mejorar hoy?",
     "Plantea al menos una necesidad concreta que Browix resuelve: control horario o presentismo, "
     "liquidación de horas, turnos, recibos de sueldo digitales, legajo y vencimientos, tareas u operaciones "
     "en terreno, comunicación interna, uniformes y elementos de protección personal, capacitaciones o "
     "selección de personal.", 15, True),
    ("¿Para cuándo te gustaría tenerlo funcionando?",
     "Indica un plazo concreto y cercano, de hasta unos tres meses (por ejemplo 'ya', 'este mes', 'el mes "
     "que viene'). No califica 'más adelante', 'el año que viene' o 'no sé'.", 10, False),
    ("¿Quién toma la decisión de sumar un sistema así en tu empresa?",
     "El interesado decide o participa directamente de la decisión (dueño, gerente, recursos humanos, "
     "operaciones), o nombra con claridad a quién decide.", 8, False),
    ("¿Te gustaría coordinar una demo sin compromiso con un asesor, para verlo funcionando sobre tu operación?",
     "Acepta coordinar una demo o una reunión con un asesor.", 12, True),
    ("¿A qué correo te escribimos para coordinarla?",
     "Da un correo electrónico de contacto.", 5, False),
]

SEED_BANDS = [
    (0, 39, "frio"),
    (40, 69, "tibio"),
    (70, 100, "caliente"),
]

# Resultados posibles de una banda / del scoring de una llamada.
OUTCOMES = ("frio", "tibio", "caliente")


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
