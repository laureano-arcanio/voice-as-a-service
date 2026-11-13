import datetime
import re
from itertools import pairwise
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ..llm import params as llm_params
from . import legacy, variables


class AgentInfo(BaseModel):
    name: str
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


class VariableSpec(BaseModel):
    """Una variable dinamica declarada ({{nombre}}; app/conversation/variables.py): su valor por defecto."""
    name: str
    default: str | int | float | bool = ""
    description: str = Field(default="", max_length=variables.MAX_DESCRIPTION_CHARS)

    @field_validator("default")
    @classmethod
    def _default(cls, v):
        if isinstance(v, str) and len(v) > variables.MAX_VALUE_CHARS:
            raise ValueError(f"hasta {variables.MAX_VALUE_CHARS} caracteres")
        return v


class AnalysisField(BaseModel):
    """Un dato que saca el analisis de la conversacion (la extraccion, app/llm/prompt.py)."""
    name: str
    label: str | None = None
    description: str
    # phone: telefono de 8 a 15 digitos; email_or_phone: cualquiera de los dos (app/conversation/workflow.py).
    type: Literal["string", "integer", "boolean", "email", "email_or_phone", "choice", "phone"] = "string"
    options: list[str] | None = None  # valores posibles de un campo choice


class Outcome(BaseModel):
    id: str
    label: str                                    # para el dashboard
    when: dict[str, Any] = Field(default_factory=dict)  # igualdades sobre los campos; vacio = default
    goal: bool = False                            # cumple el objetivo del agente
    # El contacto pidio que no lo llamen mas: en una llamada de campaña, el telefono queda en la lista
    # de bajas de voz del cliente (contact_optouts, source "outcome": campaign_calls.apply_outcome_optout).
    no_contact: bool = False


class Analysis(BaseModel):
    """Lo que se saca de la conversacion al terminar, en una llamada guiada: datos, resumen y resultado."""
    summary: bool = True
    instructions: str = Field(default="", max_length=4000)
    # Lista y no mapa: jsonb no conserva el orden de las claves, y el orden es el del analisis y la UI.
    fields: list[AnalysisField] = Field(default_factory=list)
    # El primero cuyo `when` se cumple; si hay, el ultimo es el default, sin when.
    outcomes: list[Outcome] = Field(default_factory=list)

    @field_validator("fields", mode="before")
    @classmethod
    def _fields_list(cls, v):
        return _as_list(v, "name, type, description")


def _as_list(value: Any, keys: str) -> Any:
    """Las listas con name de la definicion: la forma mapa no se acepta (su orden se pierde en jsonb)."""
    if isinstance(value, dict):
        raise ValueError(f"debe ser una lista [{{{keys}}}]")
    return value


class ToolGrant(BaseModel):
    """Una herramienta del cliente que puede usar el agente: el slug de una herramienta http o code
    (docs/features/HERRAMIENTAS.md)."""
    tool: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")


class ToolSettings(BaseModel):
    """Limite de recursos del bucle de herramientas (docs/features/HERRAMIENTAS.md): vueltas al LLM con herramientas por
    turno. Al llegar, el turno termina con limit_message (no se fuerza al modelo a responder)."""
    max_calls_per_turn: int = Field(default=3, ge=1, le=10)
    limit_message: str = Field(default="Disculpá, no pude completar eso.", min_length=1, max_length=300)


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
    """Que LLM atiende cada turno de la conversacion (docs/features/LLM_CONEXIONES.md). Sin plan, el servidor
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


class ExternalConfig(BaseModel):
    """Tu propio agente (docs/features/LLM_CONEXIONES.md): cada turno lo contesta el agente del cliente, un endpoint
    compatible con OpenAI (chat completions en streaming) de una conexion suya (llm_connections). La plataforma
    pone la voz, la telefonia y los minutos; el prompt y las herramientas son del cliente."""
    connection: str = Field(min_length=1)
    # Lo que va en `model` del pedido; vacio = el default_model de la conexion.
    model: str | None = None
    # Prompt de sistema que se antepone a la conversacion; sin el, solo los mensajes (el prompt es del cliente).
    system: str | None = Field(default=None, max_length=20_000)
    # Cuanto se espera el primer texto (o la primera herramienta) antes de dar el turno por fallido.
    first_token_timeout_ms: int = Field(default=4000, ge=500, le=20_000)
    # Lo que dice el agente si el endpoint falla o no contesta a tiempo.
    error_message: str = Field(default="Disculpá, se me cortó. ¿Me lo repetís?", min_length=1, max_length=300)
    # Errores seguidos hasta aplicar on_errors: hang_up (cortar) o transfer:<area_id> (derivar a esa area).
    max_errors: int = Field(default=2, ge=1, le=10)
    on_errors: str = Field(default="hang_up", pattern=r"^(hang_up|transfer:\S+)$")

    @field_validator("model", "system")
    @classmethod
    def _blank(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None


class HandoffTarget(BaseModel):
    """Un area del equipo del cliente (handoff_areas) a la que el agente puede pasar la llamada."""
    area_id: str
    # Cuando derivar, en lenguaje natural, para el LLM; vacio = la descripcion del area.
    when: str = Field(default="", max_length=500)


class HoldMusic(BaseModel):
    """Musica mientras el cliente espera (llamando a la persona, durante el whisper)."""
    enabled: bool = True
    # storage/hold-music/<track>.ogg, o "default": la de LiveKit Agents (BuiltinAudioClip.HOLD_MUSIC).
    track: str = Field(default="default", pattern=r"^[a-z0-9_-]{1,64}$")
    volume: float = Field(default=0.3, ge=0.05, le=1)


class HandoffConfig(BaseModel):
    """Derivacion a personas (docs/features/EQUIPO_TELEFONIA.md): a que areas puede pasar la llamada el agente."""
    areas: list[HandoffTarget] = Field(default_factory=list, max_length=10)
    hold_music: HoldMusic = Field(default_factory=HoldMusic)


class PreCallWorkflow(BaseModel):
    """Herramienta oculta al modelo que corre antes de la conversacion; su `assign` trae los datos."""
    tool: str = Field(min_length=1)
    timeout_ms: int = Field(default=1500, ge=200, le=5000)


class PostCallWorkflow(BaseModel):
    """Herramienta oculta al modelo que corre una vez, al cumplirse `when`: si el operador acepto, o siempre."""
    tool: str = Field(min_length=1)
    when: Literal["handoff_accepted", "always"] = "handoff_accepted"


class AgentWorkflows(BaseModel):
    pre_call: PreCallWorkflow | None = None
    post_call: PostCallWorkflow | None = None


class Workflow(BaseModel):
    """Definicion de un agente. Se guarda como JSON (agents.definition en la base,
    app/agents/templates/*.json las plantillas). id y version los fija la app: el
    slug del agente y su version."""
    id: str
    version: int
    # Graba un WAV por mensaje/audio, localmente, con su numero en Message.recording:
    # llamadas y audios de WhatsApp (app/conversation/recordings.py).
    record_audio: bool = False
    # Con record_audio, el agente dice "Esta llamada está siendo grabada." antes de la apertura.
    recording_notice: bool = False
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
    # Lo que va al LLM tal cual (despues del canal), con sus {{variables}} sustituidas al empezar.
    prompt: str = Field(default="", max_length=40_000)
    # Lo primero que dice el agente (llamadas); por WhatsApp entrante escribe primero la persona.
    first_message: str = Field(default="", max_length=1000)
    # Llamadas: el primer mensaje se sintetiza entero al guardar el agente (suena mejor que frase por
    # frase) y se reproduce ese audio (app/conversation/opening_audio.py).
    first_message_audio: bool = False
    # Llamadas: espera desde que se conecta la llamada hasta que el agente empieza a hablar.
    first_message_delay_ms: int = Field(default=200, ge=0, le=10_000)
    # Variables declaradas con su default; las demas pueden venir del pedido, la campaña o una herramienta.
    # Lista, como analysis.fields: el orden de la declaracion se conserva en jsonb.
    variables: list[VariableSpec] = Field(default_factory=list)
    # Analisis al terminar; sin el, no hay extraccion ni resultado (salvo fuera de tema).
    analysis: Analysis | None = None
    # Herramientas del cliente que usa el agente (no con external: las tiene su propio agente).
    tools: list[ToolGrant] = Field(default_factory=list)
    # None: los defaults de ToolSettings (no se guarda, asi una definicion sin herramientas no cambia).
    tool_settings: ToolSettings | None = None
    # Llamadas: areas del equipo a las que puede derivar (herramienta transfer_call).
    handoff: HandoffConfig | None = None
    # Herramientas automaticas, ocultas al modelo (se validan al guardar: services/tools.check_agent_tools).
    workflows: AgentWorkflows | None = None
    # Tu propio agente: el endpoint del cliente contesta cada turno (sin el prompt de la definicion ni extraccion).
    external: ExternalConfig | None = None

    @model_validator(mode="before")
    @classmethod
    def _legacy(cls, data: Any) -> Any:
        """Definiciones viejas: `engine` y herramientas de apps ({app, tools}) se ignoran; objective, conversation,
        fields y completion se convierten (app/conversation/legacy.py)."""
        if not isinstance(data, dict):
            return data
        data = legacy.upgrade({k: v for k, v in data.items() if k != "engine"})
        if isinstance(data.get("tools"), list):
            data["tools"] = [{"tool": g["tool"]} for g in data["tools"] if isinstance(g, dict) and g.get("tool")]
        return data

    @field_validator("variables", mode="before")
    @classmethod
    def _variables_list(cls, v):
        return _as_list(v, "name, default, description")

    @model_validator(mode="after")
    def _consistent(self) -> "Workflow":
        """Lo que el motor da por sentado: las definiciones ahora se editan desde la UI."""
        if self.tools and self.external is not None:
            raise ValueError("tools: con tu propio agente, las herramientas son las de tu agente")
        slugs = [g.tool for g in self.tools]
        if len(set(slugs)) != len(slugs):
            raise ValueError("tools: una herramienta repetida")
        if len(self.variables) > variables.MAX_VARIABLES:
            raise ValueError(f"variables: hasta {variables.MAX_VARIABLES}")
        seen = set()
        for i, var in enumerate(self.variables):
            if msg := variables.name_error(var.name):
                raise ValueError(f"variables.{i}.name: {var.name}: {msg}")
            if var.name in seen:
                raise ValueError(f"variables.{i}.name: {var.name} repetida")
            seen.add(var.name)
        texts = [("prompt", self.prompt), ("first_message", self.first_message)]
        if self.analysis is not None:
            texts.append(("analysis.instructions", self.analysis.instructions))
            texts += [(f"analysis.fields.{i}.description", f.description) for i, f in enumerate(self.analysis.fields)]
        for path, text in texts:
            if bad := variables.forbidden_in_llm_text(text):
                raise ValueError(f"{path}: {bad} no puede ir al LLM (solo en herramientas)")
        if self.analysis is not None:
            fields = set()
            for i, spec in enumerate(self.analysis.fields):
                name = spec.name
                if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                    raise ValueError(f"analysis.fields.{i}.name: {name}: usar minusculas, numeros y _ (ej. contact_name)")
                if name in fields:
                    raise ValueError(f"analysis.fields.{i}.name: {name} repetido")
                if spec.type == "choice" and not spec.options:
                    raise ValueError(f"analysis.fields.{i}.options: {name}: un campo choice necesita options")
                fields.add(name)
            outcomes = self.analysis.outcomes
            if outcomes and outcomes[-1].when:
                raise ValueError("analysis.outcomes: el ultimo resultado tiene que ser el default, sin when")
            ids = [o.id for o in outcomes]
            if len(set(ids)) != len(ids):
                raise ValueError("analysis.outcomes: ids repetidos")
            for o in outcomes:
                for dep in o.when:
                    if dep not in fields:
                        raise ValueError(f"analysis.outcomes.{o.id}.when: {dep} no es un campo")
        if self.generation is not None and not self.generation.params:
            self.generation = None
        if self.handoff is not None and self.handoff.areas:
            ids = [a.area_id for a in self.handoff.areas]
            if len(set(ids)) != len(ids):
                raise ValueError("handoff.areas: un area repetida")
        if self.external and self.external.on_errors.startswith("transfer:"):
            area = self.external.on_errors.split(":", 1)[1]
            if area not in [a.area_id for a in (self.handoff.areas if self.handoff else [])]:
                raise ValueError("external.on_errors: el area no esta entre las de handoff del agente")
        return self

    @property
    def analysis_fields(self) -> dict[str, AnalysisField]:
        """Los datos del analisis {nombre: spec}, en el orden de la lista (vacio sin analysis)."""
        return {f.name: f for f in self.analysis.fields} if self.analysis is not None else {}

    @property
    def variable_specs(self) -> dict[str, VariableSpec]:
        """Las variables declaradas {nombre: spec}, en el orden de la lista."""
        return {v.name: v for v in self.variables}

    @property
    def outcomes(self) -> list[Outcome]:
        return self.analysis.outcomes if self.analysis is not None else []


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
    # Hora del mensaje (UTC), para la linea de tiempo del panel. Los de antes del 23-oct-2026 no la tienen.
    at: datetime.datetime | None = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    # Llamada derivada: lo que se hablo con la persona del equipo (modo escucha, app/voice/handoff.py) lleva el
    # tramo (handoff_legs.id); lo que dijo la persona va como assistant con su nombre en person.
    handoff_leg: str | None = None
    person: str | None = None
    # Respuesta del agente que llamo a transfer_call: el area. El historial del LLM la reconstruye como la
    # llamada a la herramienta y su resultado (app/llm/prompt.py), para que el modelo vea que derivar es la herramienta.
    handoff: str | None = None
    # Teclas que marco esa parte (app/voice/dtmf.py): los digitos del grupo, tal cual; text dice "Marcó <digitos>".
    dtmf: str | None = None


class TurnMedia(BaseModel):
    """Modalidad del turno en curso (WhatsApp); no se guarda. Cambia el prompt
    del turno solo en el canal whatsapp (app/llm/prompt.py)."""
    user_voice_note: bool = False    # el mensaje nuevo entero es transcripcion (mezclado con texto: VOICE_NOTE_TAG por linea)
    reply_voice_note: bool = False   # la respuesta sale como nota de voz: formato para escuchar


class Progress(BaseModel):
    """Registro de la app; no decide el flujo."""
    rejected: dict[str, Any] = Field(default_factory=dict)   # valores invalidos de la ultima extraccion (para el panel)
    outcome: str | None = None                               # Outcome.id al completar (para el dashboard)
    undo: dict[str, Any] | None = None                       # estado previo al ultimo turno (retract_last_turn)
    # Variables dinamicas (app/conversation/variables.py): valor, las ocultas al LLM y la fuente de cada una.
    variables: dict[str, Any] = Field(default_factory=dict)
    hidden_variables: list[str] = Field(default_factory=list)
    variable_sources: dict[str, str] = Field(default_factory=dict)
    # Datos de la llamada para {{call.*}} ({id, from, to, phone, direction, mode}) y hora de inicio ({{today}}).
    call: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    # El prompt de sistema, renderizado una vez en el primer turno: no cambia en la conversacion (prefix cache).
    system_prompt: str | None = None
    # Resumen del analisis (analysis.summary).
    summary: str | None = None
    # Llamada con derivacion: las areas que puede usar el agente, como las ve el LLM ({id, name, when, schedule}).
    # Las fija el worker al empezar (app/voice/handoff.py) y no cambian en la llamada.
    handoff_areas: list[dict[str, Any]] = Field(default_factory=list)
    # Tu propio agente: errores seguidos del endpoint del cliente (vuelve a 0 con un turno bueno).
    external_errors: int = 0
    # Prueba por texto desde el panel: el numero de quien llama, simulado ({{call.phone}} sin llamada). No se marca.
    caller_phone: str | None = None
    # Prueba desde el panel que corre las herramientas automaticas del agente (pre-call y post-call).
    test_workflows: bool = False


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
    # Tokens del LLM sumados de todos los turnos y extracciones (conversations.llm_input_tokens/llm_output_tokens).
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    # Solo el turno en curso: lo fija process_turn y no se guarda (exclude).
    media: TurnMedia = Field(default_factory=TurnMedia, exclude=True)


class AgentTurn(BaseModel):
    """Salida del LLM de conversacion. Los datos no van aca: los saca la
    extraccion, que corre aparte mientras suena la respuesta."""
    assistant_message: str
    status: Literal["active", "completed"] = "active"
    # Con status completed: "off_topic" si el agente corta porque la conversacion no tiene que ver con su
    # objetivo (end_call con motivo fuera_de_tema); None, el cierre normal. Tu propio agente:
    # "external_error" si corto despues de max_errors errores del endpoint, o "external_agent_not_in_plan".
    end_reason: Literal["off_topic", "external_error", "external_agent_not_in_plan"] | None = None
    # El agente pasa la llamada a esa area (transfer_call); status sigue active.
    handoff: str | None = None
    # Salida cruda del LLM y su razonamiento; no son parte del contrato.
    raw: str | None = Field(default=None, exclude=True)
    reasoning: str | None = Field(default=None, exclude=True)
    # Tokens del turno (el usage de las respuestas del proveedor; 0 si no lo da).
    input_tokens: int = Field(default=0, exclude=True)
    output_tokens: int = Field(default=0, exclude=True)


class Extraction(BaseModel):
    """Salida del LLM de extraccion: valor por campo, null si no hay dato, y el resumen si se pidio."""
    fields: dict[str, Any]
    summary: str | None = None
    raw: str | None = None
    reasoning: str | None = None
    # Tokens del pedido (el usage del proveedor; 0 si no lo da).
    input_tokens: int = 0
    output_tokens: int = 0
