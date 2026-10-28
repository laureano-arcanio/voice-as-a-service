import type { Definition } from '@/api/types';

// Borrador del formulario de un agente: la definicion (app/conversation/models.py, clase Workflow)
// en listas editables. fromDraft(toDraft(d)) da la misma definicion que normaliza el servidor.

export const FIELD_TYPES = [
  { value: 'string', label: 'Texto' },
  { value: 'integer', label: 'Número entero' },
  { value: 'boolean', label: 'Sí o no' },
  { value: 'choice', label: 'Opción de una lista' },
  { value: 'email', label: 'Email' },
  { value: 'email_or_phone', label: 'Email o teléfono' },
  { value: 'digits', label: 'Dígitos (leídos o dictados)' },
  { value: 'phone', label: 'Teléfono (el de la llamada, o lo pide)' },
] as const;

export type FieldType = (typeof FIELD_TYPES)[number]['value'];

/** Tu propio agente (definition.external, docs/features/LLM_CONEXIONES.md): el endpoint del cliente y que hacer
 * si falla. */
export interface ExternalDraft {
  /** Id de una conexion openai_compatible del cliente; '' = sin elegir. */
  connection: string;
  /** '' = el modelo por defecto de la conexion. */
  model: string;
  /** Prompt de sistema que se antepone; '' = ninguno (el prompt es del cliente). */
  system: string;
  firstTokenTimeoutMs: number;
  errorMessage: string;
  maxErrors: number;
  /** 'hang_up' o 'transfer:<area_id>'. */
  onErrors: string;
}

/** Defaults de ExternalConfig (app/conversation/models.py). */
export const EXTERNAL_DEFAULTS: Omit<ExternalDraft, 'connection'> = {
  model: '',
  system: '',
  firstTokenTimeoutMs: 4000,
  errorMessage: 'Disculpá, se me cortó. ¿Me lo repetís?',
  maxErrors: 2,
  onErrors: 'hang_up',
};

function toExternalDraft(raw: unknown): ExternalDraft | null {
  if (raw == null || typeof raw !== 'object') return null;
  const e = obj(raw);
  const num = (x: unknown, d: number) => (typeof x === 'number' ? x : d);
  return {
    connection: str(e.connection),
    model: str(e.model),
    system: str(e.system),
    firstTokenTimeoutMs: num(e.first_token_timeout_ms, EXTERNAL_DEFAULTS.firstTokenTimeoutMs),
    errorMessage: str(e.error_message) || EXTERNAL_DEFAULTS.errorMessage,
    maxErrors: num(e.max_errors, EXTERNAL_DEFAULTS.maxErrors),
    onErrors: str(e.on_errors) || EXTERNAL_DEFAULTS.onErrors,
  };
}

function fromExternalDraft(e: ExternalDraft): Record<string, unknown> {
  return {
    connection: e.connection,
    ...(e.model.trim() ? { model: e.model.trim() } : {}),
    ...(e.system.trim() ? { system: e.system } : {}),
    first_token_timeout_ms: e.firstTokenTimeoutMs,
    error_message: e.errorMessage,
    max_errors: e.maxErrors,
    on_errors: e.onErrors,
  };
}

/** Una herramienta del cliente (http o code, docs/features/HERRAMIENTAS.md) que usa el agente. */
export interface ClientToolGrantDraft {
  key: string;
  /** Slug de la herramienta. */
  tool: string;
}

/** Defaults de ToolSettings (app/conversation/models.py). */
export const TOOL_SETTINGS = { maxCallsPerTurn: 3, limitMessage: 'Disculpá, no pude completar eso.' };

/** id del elemento de una seccion del formulario (para llevar a un error). */
export const sectionId = (name: string) => `def-${name}`;

/** Pestañas de edicion del agente: cada seccion del formulario vive en una. */
export type Part = 'conversacion' | 'datos' | 'herramientas' | 'voz' | 'modelo';
export const PARTS: Part[] = ['conversacion', 'datos', 'herramientas', 'voz', 'modelo'];
export const SECTION_PART: Record<string, Part> = {
  agente: 'conversacion',
  objetivo: 'conversacion',
  reglas: 'conversacion',
  conocimiento: 'conversacion',
  datos: 'datos',
  dato: 'datos',
  resultados: 'datos',
  resultado: 'datos',
  herramientas: 'herramientas',
  derivacion: 'herramientas',
  voz: 'voz',
  externo: 'modelo',
  modelo: 'modelo',
};
export type Requirement = 'yes' | 'no' | 'if';
export type ConditionValue = string | number | boolean;

export interface ConditionDraft {
  key: string;
  field: string;
  value: ConditionValue | null;
}

export interface FieldDraft {
  key: string;
  name: string;
  label: string;
  type: FieldType;
  options: string[];
  description: string;
  question: string;
  requirement: Requirement;
  conditions: ConditionDraft[];
  priority: number;
}

export interface OutcomeDraft {
  key: string;
  id: string;
  label: string;
  goal: boolean;
  /** Campañas de voz: el contacto pidió que no lo llamen más; el teléfono pasa a la lista de bajas. */
  noContact: boolean;
  message: string;
  conditions: ConditionDraft[];
}

export interface RuleDraft {
  key: string;
  text: string;
}

/** Un parametro de generacion enviado al LLM (app/llm/params.py), agregado por el usuario. */
export interface ParamDraft {
  key: string;
  name: string;
  value: string | number | boolean;
}

export interface Draft {
  id: string;
  version: number | null;
  name: string;
  role: string;
  language: string;
  /** '' = la predeterminada (VLLM_TTS_VOICE). */
  voice: string;
  /** Un WAV por turno (telefono o WhatsApp), localmente. */
  recordAudio: boolean;
  /** Con recordAudio, el agente avisa que la llamada se graba antes de la apertura. */
  recordingNotice: boolean;
  /** Llamadas: al terminar, Atentina le manda al cliente el resumen por email (el cliente lo apaga en Mi cuenta). */
  callSummaryEmail: boolean;
  /** WhatsApp: minutos sin mensaje del contacto para dar la conversacion por terminada y abrir
   * otra en limpio (ventana de contexto temporal). null = el default global del servidor
   * (WA_SESSION_HOURS, 1440 min = 24 hs). */
  waSessionMinutes: number | null;
  objective: string;
  opening: string;
  /** Llamadas: la apertura se sintetiza entera al guardar y se reproduce ese audio. */
  openingAudio: boolean;
  /** Llamadas: espera antes de que el agente hable, en ms. */
  openingDelayMs: number;
  rules: RuleDraft[];
  knowledge: string;
  fields: FieldDraft[];
  outcomes: OutcomeDraft[];
  /** Herramientas del cliente (no con tu propio agente). */
  clientTools: ClientToolGrantDraft[];
  /** Tope de vueltas con herramientas por turno; null = el default del servidor (3). */
  maxToolCallsPerTurn: number | null;
  /** Lo que dice el agente al llegar al tope; '' = el default del servidor. */
  toolLimitMessage: string;
  /** Parametros de generacion por defecto del agente (todo el flujo). */
  generation: ParamDraft[];
  /** LLM por etapa de la conversacion (conexiones BYOK, docs/features/LLM_CONEXIONES.md). null = siempre el
   * servidor propio (no va a la definicion). */
  llm: LlmDraft | null;
  /** Derivacion a personas (docs/features/EQUIPO_TELEFONIA.md): areas del equipo del cliente y musica de espera. */
  handoff: HandoffDraft;
  /** Tu propio agente: prendido si no es null. */
  external: ExternalDraft | null;
}

/** Un area del equipo a la que el agente puede pasar la llamada. */
export interface HandoffAreaDraft {
  areaId: string;
  /** Cuando derivar, para el LLM; '' = la descripcion del area. */
  when: string;
}

export interface HandoffDraft {
  /** La definicion ya tenia handoff: se sigue mandando aunque no queden areas (guardar sin tocar nada no
   * cambia la version). Sin handoff previo y sin areas, no va a la definicion. */
  present: boolean;
  areas: HandoffAreaDraft[];
  holdMusic: { enabled: boolean; track: string; volume: number };
}

/** Defaults de HoldMusic (app/conversation/models.py). */
export const HOLD_MUSIC = { enabled: true, track: 'default', volume: 0.3 };
export const MAX_HANDOFF_AREAS = 10;

function toHandoffDraft(raw: unknown): HandoffDraft {
  const h = obj(raw);
  const music = obj(h.hold_music);
  return {
    present: raw != null && typeof raw === 'object',
    areas: (Array.isArray(h.areas) ? h.areas : []).map((r) => {
      const a = obj(r);
      return { areaId: str(a.area_id), when: str(a.when) };
    }),
    holdMusic: {
      enabled: music.enabled !== false,
      track: str(music.track) || HOLD_MUSIC.track,
      volume: typeof music.volume === 'number' ? music.volume : HOLD_MUSIC.volume,
    },
  };
}

function fromHandoffDraft(h: HandoffDraft): Record<string, unknown> | undefined {
  if (!h.areas.length && !h.present) return undefined;
  return {
    areas: h.areas.map((a) => ({ area_id: a.areaId, when: a.when.trim() })),
    hold_music: { enabled: h.holdMusic.enabled, track: h.holdMusic.track, volume: h.holdMusic.volume },
  };
}

export interface LlmStageDraft {
  key: string;
  /** Desde que turno del usuario (1 = su primer mensaje) responde este LLM. */
  fromTurn: number;
  /** Id de la conexion; null = el servidor propio. */
  connection: string | null;
  model: string;
  /** Parametros de generacion de esta etapa (pisan los del agente). */
  generation: ParamDraft[];
}

export interface LlmDraft {
  stages: LlmStageDraft[];
  fallbackLocal: boolean;
}

export const MAX_LLM_STAGES = 3;

/** Default de conversation.opening_delay_ms (app/conversation/models.py). */
export const OPENING_DELAY_MS = 200;

export const blankStage = (fromTurn: number): LlmStageDraft => ({
  key: newKey(),
  fromTurn,
  connection: null,
  model: '',
  generation: [],
});

export const blankParam = (name: string, value: string | number | boolean): ParamDraft => ({
  key: newKey(),
  name,
  value,
});

/** Definicion cruda {params: {...}} -> filas del formulario. */
function toParams(raw: unknown): ParamDraft[] {
  const params = obj(obj(raw).params);
  return Object.entries(params).map(([name, value]) => ({
    key: newKey(),
    name,
    value: typeof value === 'number' || typeof value === 'boolean' ? value : str(value),
  }));
}

/** Filas del formulario -> {params: {...}}: las que tienen nombre y un valor puesto ('' = sin poner). */
function fromParams(rows: ParamDraft[]): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  for (const row of rows) if (row.name && row.value !== '') params[row.name] = row.value;
  return { params };
}

/** Sin etapas externas ni parametros por etapa, y con el respaldo, no hay plan que guardar. */
function isLocalOnly(llm: LlmDraft): boolean {
  return llm.stages.every((st) => st.connection === null && st.generation.length === 0) && llm.fallbackLocal;
}

function toLlmDraft(raw: unknown): LlmDraft | null {
  const llm = obj(raw);
  if (!Array.isArray(llm.stages) || llm.stages.length === 0) return null;
  return {
    fallbackLocal: llm.fallback_local !== false,
    stages: llm.stages.map((r) => {
      const st = obj(r);
      return {
        key: newKey(),
        fromTurn: typeof st.from_turn === 'number' ? st.from_turn : 1,
        connection: typeof st.connection === 'string' && st.connection ? st.connection : null,
        model: str(st.model),
        // temperature suelta (definiciones viejas) se muestra como parametro.
        generation: (() => {
          const rows = toParams(st.generation);
          if (!rows.length && typeof st.temperature === 'number')
            return [blankParam('temperature', st.temperature)];
          return rows;
        })(),
      };
    }),
  };
}

function fromLlmDraft(llm: LlmDraft): Record<string, unknown> {
  return {
    stages: llm.stages.map((st) => ({
      from_turn: st.fromTurn,
      ...(st.connection ? { connection: st.connection, model: st.model.trim() } : {}),
      ...(st.generation.length ? { generation: fromParams(st.generation) } : {}),
    })),
    fallback_local: llm.fallbackLocal,
  };
}

let seq = 0;
/** Clave estable para las listas del formulario (no va a la definicion). */
export const newKey = () => `k${++seq}`;

const obj = (x: unknown): Record<string, unknown> =>
  x && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : {};
const str = (x: unknown): string => (typeof x === 'string' ? x : x == null ? '' : String(x));

function toConditions(when: unknown): ConditionDraft[] {
  return Object.entries(obj(when)).map(([field, value]) => ({
    key: newKey(),
    field,
    value:
      typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' ? value : null,
  }));
}

function fromConditions(conditions: ConditionDraft[]): Record<string, ConditionValue> {
  const out: Record<string, ConditionValue> = {};
  for (const c of conditions) if (c.field && c.value !== null && c.value !== '') out[c.field] = c.value;
  return out;
}

export function toDraft(d: Definition): Draft {
  const agent = obj(d.agent);
  const conv = obj(d.conversation);
  const fields = Object.entries(obj(d.fields))
    .map(([name, raw]): FieldDraft => {
      const f = obj(raw);
      const type = str(f.type);
      const requiredIf = toConditions(f.required_if);
      return {
        key: newKey(),
        name,
        label: str(f.label),
        // Un tipo que esta version de la UI no conoce se conserva: pasarlo a 'string' lo pisaba al guardar
        // (una pestana abierta antes de un deploy guardo el telefono como texto, 20-oct-2026).
        type: (type || 'string') as FieldType,
        options: Array.isArray(f.options) ? f.options.map(str) : [],
        description: str(f.description),
        question: str(f.question),
        requirement: requiredIf.length ? 'if' : f.required === true ? 'yes' : 'no',
        conditions: requiredIf,
        priority: typeof f.priority === 'number' ? f.priority : 0,
      };
    })
    .sort((a, b) => a.priority - b.priority);
  const outcomes = Array.isArray(obj(d.completion).outcomes) ? (obj(d.completion).outcomes as unknown[]) : [];
  return {
    id: str(d.id),
    version: typeof d.version === 'number' ? d.version : null,
    name: str(agent.name),
    role: str(agent.role),
    language: str(agent.language),
    voice: str(agent.voice),
    recordAudio: d.record_audio === true,
    recordingNotice: d.recording_notice === true,
    callSummaryEmail: d.call_summary_email === true,
    waSessionMinutes: typeof d.wa_session_minutes === 'number' ? d.wa_session_minutes : null,
    objective: str(obj(d.objective).description),
    opening: str(conv.opening),
    openingAudio: conv.opening_audio === true,
    openingDelayMs: typeof conv.opening_delay_ms === 'number' ? conv.opening_delay_ms : OPENING_DELAY_MS,
    rules: (Array.isArray(conv.rules) ? conv.rules : []).map((r) => ({ key: newKey(), text: str(r) })),
    knowledge: str(d.knowledge),
    fields,
    outcomes: outcomes.map((raw) => {
      const o = obj(raw);
      return {
        key: newKey(),
        id: str(o.id),
        label: str(o.label),
        goal: o.goal === true,
        noContact: o.no_contact === true,
        message: str(o.message),
        conditions: toConditions(o.when),
      };
    }),
    // Las entradas viejas de apps ({app, tools}) no tienen tool: se descartan, como en el servidor.
    clientTools: (Array.isArray(d.tools) ? d.tools : [])
      .filter((raw) => obj(raw).tool != null)
      .map((raw) => ({ key: newKey(), tool: str(obj(raw).tool) })),
    maxToolCallsPerTurn:
      typeof obj(d.tool_settings).max_calls_per_turn === 'number'
        ? (obj(d.tool_settings).max_calls_per_turn as number)
        : null,
    toolLimitMessage: str(obj(d.tool_settings).limit_message),
    generation: toParams(d.generation),
    llm: toLlmDraft(d.llm),
    handoff: toHandoffDraft(d.handoff),
    external: toExternalDraft(d.external),
  };
}

export function fromDraft(draft: Draft): Definition {
  const fields: Record<string, unknown> = {};
  for (const f of draft.fields) {
    const requiredIf = f.requirement === 'if' ? fromConditions(f.conditions) : {};
    fields[f.name] = {
      priority: f.priority,
      ...(f.label.trim() ? { label: f.label } : {}),
      description: f.description,
      type: f.type,
      ...(f.type === 'choice' ? { options: f.options } : {}),
      required: f.requirement === 'yes',
      ...(Object.keys(requiredIf).length ? { required_if: requiredIf } : {}),
      question: f.question,
    };
  }
  const last = draft.outcomes.length - 1;
  const handoff = fromHandoffDraft(draft.handoff);
  const external = draft.external;
  const toolSettings = {
    ...(draft.maxToolCallsPerTurn != null ? { max_calls_per_turn: draft.maxToolCallsPerTurn } : {}),
    ...(draft.toolLimitMessage.trim() ? { limit_message: draft.toolLimitMessage.trim() } : {}),
  };
  return {
    id: draft.id,
    ...(draft.version != null ? { version: draft.version } : {}),
    ...(draft.recordAudio ? { record_audio: true } : {}),
    ...(draft.recordAudio && draft.recordingNotice ? { recording_notice: true } : {}),
    ...(draft.callSummaryEmail ? { call_summary_email: true } : {}),
    ...(draft.waSessionMinutes != null ? { wa_session_minutes: draft.waSessionMinutes } : {}),
    // Con el agente del cliente no hay LLM nuestro: ni etapas ni parametros.
    ...(!external && draft.generation.length ? { generation: fromParams(draft.generation) } : {}),
    ...(!external && draft.llm && !isLocalOnly(draft.llm) ? { llm: fromLlmDraft(draft.llm) } : {}),
    ...(external ? { external: fromExternalDraft(external) } : {}),
    agent: {
      name: draft.name,
      role: draft.role,
      language: draft.language,
      ...(draft.voice ? { voice: draft.voice } : {}),
    },
    objective: { description: draft.objective },
    conversation: {
      opening: draft.opening,
      ...(draft.openingAudio ? { opening_audio: true } : {}),
      ...(draft.openingDelayMs !== OPENING_DELAY_MS ? { opening_delay_ms: draft.openingDelayMs } : {}),
      rules: draft.rules.map((r) => r.text).filter((t) => t.trim()),
    },
    knowledge: draft.knowledge,
    fields,
    completion: {
      when: 'all_required_fields_completed',
      outcomes: draft.outcomes.map((o, i) => ({
        id: o.id,
        label: o.label,
        // El ultimo es el resultado por defecto: sin condiciones.
        when: i === last ? {} : fromConditions(o.conditions),
        message: o.message,
        goal: o.goal,
        // Solo si esta marcado: las definiciones sin la bandera quedan igual.
        ...(o.noContact ? { no_contact: true } : {}),
      })),
    },
    // Con tu propio agente, las herramientas son las suyas (el servidor rechaza tools con external).
    ...(!external && draft.clientTools.length ? { tools: toolEntries(draft).map((e) => e.value) } : {}),
    ...(!external && Object.keys(toolSettings).length ? { tool_settings: toolSettings } : {}),
    ...(handoff ? { handoff } : {}),
  };
}

/** Las entradas de tools de la definicion, en el orden en que se mandan, con un nombre para los errores. */
export function toolEntries(draft: Draft): { name: string; value: Record<string, unknown> }[] {
  if (draft.external) return [];
  return draft.clientTools.map((g) => ({ name: g.tool, value: { tool: g.tool } }));
}

/** JSON con claves ordenadas: para comparar definiciones sin importar el orden. */
export function stableJson(x: unknown): string {
  if (Array.isArray(x)) return `[${x.map(stableJson).join(',')}]`;
  if (x && typeof x === 'object') {
    const o = x as Record<string, unknown>;
    return `{${Object.keys(o)
      .sort()
      .filter((k) => o[k] !== undefined)
      .map((k) => `${JSON.stringify(k)}:${stableJson(o[k])}`)
      .join(',')}}`;
  }
  return JSON.stringify(x);
}

/** Prioridades 10, 20, ... en el orden de la lista. */
export function renumber(fields: FieldDraft[]): FieldDraft[] {
  return fields.map((f, i) => ({ ...f, priority: (i + 1) * 10 }));
}

export function newField(fields: FieldDraft[]): FieldDraft {
  const names = new Set(fields.map((f) => f.name));
  let n = fields.length + 1;
  while (names.has(`dato_${n}`)) n++;
  return {
    key: newKey(),
    name: `dato_${n}`,
    label: '',
    type: 'string',
    options: [],
    description: '',
    question: '',
    requirement: 'yes',
    conditions: [],
    priority: Math.max(0, ...fields.map((f) => f.priority)) + 10,
  };
}

/** Tiene un dato de tipo phone: en las llamadas con número se completa solo; por el link, el agente lo pide. */
export function hasPhoneField(draft: Draft): boolean {
  return draft.fields.some((f) => f.type === 'phone');
}

/** Prender el resumen por email: el email lleva el teléfono, así que el agente necesita un dato de tipo
 * phone (por el link no hay número y lo tiene que pedir). Si no lo tiene, se agrega al final. */
export function withPhoneField(draft: Draft): Draft {
  if (draft.external || hasPhoneField(draft)) return draft;
  const names = new Set(draft.fields.map((f) => f.name));
  let name = 'telefono';
  for (let n = 2; names.has(name); n++) name = `telefono_${n}`;
  const field: FieldDraft = {
    ...newField(draft.fields),
    name,
    label: 'Teléfono',
    type: 'phone',
    description: 'Teléfono de contacto de quien llama.',
    question: '¿A qué número te podemos llamar?',
  };
  return { ...draft, fields: [...draft.fields, field] };
}

export function newOutcome(outcomes: OutcomeDraft[]): OutcomeDraft {
  const ids = new Set(outcomes.map((o) => o.id));
  let n = outcomes.length;
  while (ids.has(`resultado_${n}`)) n++;
  return {
    key: newKey(),
    id: `resultado_${n}`,
    label: '',
    goal: false,
    noContact: false,
    message: '',
    conditions: [],
  };
}

/** Renombra un dato y lo que lo nombra (condiciones de otros datos y de los resultados). */
export function renameField(draft: Draft, index: number, name: string): Draft {
  const old = draft.fields[index]?.name;
  if (old === undefined) return draft;
  const fix = (cs: ConditionDraft[]) => cs.map((c) => (c.field === old ? { ...c, field: name } : c));
  return {
    ...draft,
    fields: draft.fields.map((f, i) =>
      i === index ? { ...f, name } : { ...f, conditions: fix(f.conditions) },
    ),
    outcomes: draft.outcomes.map((o) => ({ ...o, conditions: fix(o.conditions) })),
  };
}

export function move<T>(list: T[], from: number, to: number): T[] {
  if (to < 0 || to >= list.length) return list;
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item!);
  return next;
}

// ---------- errores del servidor ----------

/** Seccion del formulario donde va un error de validacion (ruta de pydantic). */
export type ErrorTarget =
  | {
      section:
        | 'agente'
        | 'voz'
        | 'modelo'
        | 'objetivo'
        | 'reglas'
        | 'conocimiento'
        | 'datos'
        | 'resultados'
        | 'herramientas'
        | 'derivacion'
        | 'externo';
    }
  | { section: 'dato'; key: string }
  | { section: 'resultado'; key: string };

/** Resultado de una ruta de error: por indice (pydantic) o por id (validaciones propias). */
function outcomeAt(draft: Draft, seg: string | undefined): OutcomeDraft | undefined {
  if (seg === undefined) return undefined;
  return /^\d+$/.test(seg) ? draft.outcomes[Number(seg)] : draft.outcomes.find((o) => o.id === seg);
}

export function errorTarget(draft: Draft, path: string): ErrorTarget | null {
  const [head, second, third] = path.split('.');
  if (
    head === 'record_audio' ||
    head === 'recording_notice' ||
    head === 'call_summary_email' ||
    head === 'wa_session_minutes'
  )
    return { section: 'voz' };
  if (head === 'agent') return { section: second === 'voice' ? 'voz' : 'agente' };
  if (head === 'objective') return { section: 'objetivo' };
  if (head === 'conversation') {
    if (second === 'rules') return { section: 'reglas' };
    // La apertura pregenerada y la espera son de la voz, no del prompt.
    if (second === 'opening_audio' || second === 'opening_delay_ms') return { section: 'voz' };
    return { section: 'objetivo' };
  }
  if (head === 'knowledge') return { section: 'conocimiento' };
  if (head === 'tools' || head === 'tool_settings') return { section: 'herramientas' };
  if (head === 'llm' || head === 'generation') return { section: 'modelo' };
  if (head === 'handoff') return { section: 'derivacion' };
  if (head === 'external') return { section: 'externo' };
  if (head === 'fields') {
    const f = draft.fields.find((x) => x.name === second);
    return f ? { section: 'dato', key: f.key } : { section: 'datos' };
  }
  if (head === 'completion') {
    const o = second === 'outcomes' ? outcomeAt(draft, third) : undefined;
    return o ? { section: 'resultado', key: o.key } : { section: 'resultados' };
  }
  return null;
}

const PATH_WORDS: Record<string, string> = {
  agent: 'Agente',
  name: 'nombre',
  role: 'rol',
  language: 'idioma',
  voice: 'voz',
  record_audio: 'grabar audio',
  recording_notice: 'avisar que se graba',
  call_summary_email: 'resumen por email',
  wa_session_minutes: 'ventana de contexto de WhatsApp',
  objective: 'Objetivo',
  conversation: 'Conversación',
  opening: 'apertura',
  opening_audio: 'apertura pregenerada',
  opening_delay_ms: 'espera antes de la apertura',
  rules: 'reglas',
  knowledge: 'Base de conocimiento',
  fields: 'Datos',
  priority: 'orden',
  label: 'etiqueta',
  description: 'descripción',
  type: 'tipo',
  options: 'opciones',
  required: 'obligatorio',
  required_if: 'condición',
  question: 'pregunta',
  completion: 'Resultados',
  outcomes: '',
  id: 'ID',
  when: 'condiciones',
  message: 'mensaje',
  goal: 'objetivo cumplido',
  no_contact: 'no volver a llamar',
  tools: 'Herramientas',
  tool: 'herramienta',
  tool_settings: 'Herramientas',
  max_calls_per_turn: 'vueltas con herramientas por turno',
  limit_message: 'mensaje al llegar al tope',
  llm: 'Modelo de lenguaje',
  stages: '',
  from_turn: 'turno',
  connection: 'conexión',
  model: 'modelo',
  temperature: 'temperatura',
  fallback_local: 'respaldo',
  generation: 'Parámetros',
  params: '',
  handoff: 'Derivación a personas',
  external: 'Tu propio agente',
  system: 'prompt de sistema',
  first_token_timeout_ms: 'espera del primer texto',
  error_message: 'mensaje de error',
  max_errors: 'errores seguidos',
  on_errors: 'después de los errores',
  areas: 'áreas',
  area_id: 'área',
  hold_music: 'música de espera',
  enabled: 'prendida',
  track: 'tema',
  volume: 'volumen',
};

/** "fields.contacto.question" -> "Datos › contacto › pregunta". */
export function pathLabel(draft: Draft, path: string): string {
  const parts = path.split('.');
  const out: string[] = [];
  parts.forEach((p, i) => {
    if (parts[i - 1] === 'fields') out.push(p);
    else if (parts[i - 1] === 'outcomes') {
      const o = outcomeAt(draft, p);
      out.push(o?.label || o?.id || p);
    } else if (parts[i - 1] === 'rules' && /^\d+$/.test(p)) out.push(`regla ${Number(p) + 1}`);
    else if (parts[i - 1] === 'stages' && /^\d+$/.test(p)) out.push(`etapa ${Number(p) + 1}`);
    else if (parts[i - 1] === 'areas' && /^\d+$/.test(p)) out.push(`área ${Number(p) + 1}`);
    else if (p === 'tools' && i > 0) out.push('herramientas');
    else if (parts[i - 1] === 'tools' && /^\d+$/.test(p))
      out.push(toolEntries(draft)[Number(p)]?.name || `herramienta ${Number(p) + 1}`);
    else if (PATH_WORDS[p] !== '') out.push(PATH_WORDS[p] ?? p);
  });
  return out.join(' › ');
}
