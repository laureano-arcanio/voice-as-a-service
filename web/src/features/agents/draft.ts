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
  { value: 'phone', label: 'Teléfono' },
] as const;

export type FieldType = (typeof FIELD_TYPES)[number]['value'];

/** Límites de la definición (app/conversation/models.py). */
export const MAX_PROMPT = 40_000;
export const MAX_FIRST_MESSAGE = 1_000;
export const MAX_VARIABLES = 30;
export const MAX_VARIABLE_VALUE = 2_000;

/** Espera por defecto antes del primer mensaje (Workflow.first_message_delay_ms). */
export const FIRST_MESSAGE_DELAY_MS = 200;

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
  prompt: 'conversacion',
  primer_mensaje: 'conversacion',
  variables: 'conversacion',
  analisis: 'datos',
  dato: 'datos',
  resultado: 'datos',
  herramientas: 'herramientas',
  derivacion: 'herramientas',
  automaticas: 'herramientas',
  voz: 'voz',
  externo: 'modelo',
  modelo: 'modelo',
};
export type ConditionValue = string | number | boolean;

export interface ConditionDraft {
  key: string;
  field: string;
  value: ConditionValue | null;
}

/** Un dato del analisis (Analysis.fields). Lista y no mapa: el orden es el del analisis y de jsonb. */
export interface FieldDraft {
  key: string;
  name: string;
  label: string;
  type: FieldType;
  options: string[];
  description: string;
}

/** Un resultado del analisis (Analysis.outcomes): el primero cuyo `when` se cumple; el ultimo es el default. */
export interface OutcomeDraft {
  key: string;
  id: string;
  label: string;
  goal: boolean;
  /** Campañas de voz: el contacto pidió que no lo llamen más; el teléfono pasa a la lista de bajas. */
  noContact: boolean;
  conditions: ConditionDraft[];
}

export type VariableValue = string | number | boolean;

/** Una variable declarada (VariableSpec): su default y qué es. */
export interface VariableDraft {
  key: string;
  name: string;
  default: VariableValue;
  description: string;
}

/** Lo que se saca de la conversacion al terminar (Analysis). Sin datos, instrucciones ni resultados, no va a
 * la definicion: un agente sin analisis no extrae nada. */
export interface AnalysisDraft {
  summary: boolean;
  instructions: string;
  fields: FieldDraft[];
  outcomes: OutcomeDraft[];
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
  /** Lo que va al LLM tal cual, con sus {{variables}} (Workflow.prompt). */
  prompt: string;
  /** Lo primero que dice en las llamadas (Workflow.first_message). */
  firstMessage: string;
  /** Llamadas: el primer mensaje se sintetiza entero al guardar y se reproduce ese audio. */
  firstMessageAudio: boolean;
  /** Llamadas: espera antes de que el agente hable, en ms. */
  firstMessageDelayMs: number;
  /** Variables declaradas con su default, en el orden en que se agregaron. */
  variables: VariableDraft[];
  /** Analisis al terminar. */
  analysis: AnalysisDraft;
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
  /** Herramientas automaticas, ocultas al modelo: pre-call y post-call (docs/features/HERRAMIENTAS.md). */
  workflows: WorkflowsDraft;
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

/** Defaults de PreCallWorkflow y PostCallWorkflow (app/conversation/models.py). */
export const PRE_CALL_TIMEOUT = { default: 1500, min: 200, max: 5000 };
export type PostCallWhen = 'handoff_accepted' | 'always';

export interface WorkflowsDraft {
  /** Corre antes de la conversacion; sus datos llegan al agente. null = sin pre-call. */
  preCall: { tool: string; timeoutMs: number } | null;
  /** Corre una vez, al cumplirse la condicion. null = sin post-call. */
  postCall: { tool: string; when: PostCallWhen } | null;
}

function toWorkflowsDraft(raw: unknown): WorkflowsDraft {
  const w = obj(raw);
  const pre = obj(w.pre_call);
  const post = obj(w.post_call);
  return {
    preCall: str(pre.tool)
      ? {
          tool: str(pre.tool),
          timeoutMs: typeof pre.timeout_ms === 'number' ? pre.timeout_ms : PRE_CALL_TIMEOUT.default,
        }
      : null,
    postCall: str(post.tool)
      ? { tool: str(post.tool), when: post.when === 'always' ? 'always' : 'handoff_accepted' }
      : null,
  };
}

function fromWorkflowsDraft(w: WorkflowsDraft): Record<string, unknown> | undefined {
  if (!w.preCall && !w.postCall) return undefined;
  return {
    ...(w.preCall ? { pre_call: { tool: w.preCall.tool, timeout_ms: w.preCall.timeoutMs } } : {}),
    ...(w.postCall ? { post_call: { tool: w.postCall.tool, when: w.postCall.when } } : {}),
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

function toVariables(raw: unknown): VariableDraft[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((r) => {
    const v = obj(r);
    const value = v.default;
    return {
      key: newKey(),
      name: str(v.name),
      // El default conserva su tipo (número o booleano) hasta que se edita.
      default: typeof value === 'number' || typeof value === 'boolean' ? value : str(value),
      description: str(v.description),
    };
  });
}

function toFields(raw: unknown): FieldDraft[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((r) => {
    const f = obj(r);
    return {
      key: newKey(),
      name: str(f.name),
      label: str(f.label),
      // Un tipo que esta version de la UI no conoce se conserva: pasarlo a 'string' lo pisaba al guardar
      // (una pestana abierta antes de un deploy guardo el telefono como texto, 20-oct-2026).
      type: (str(f.type) || 'string') as FieldType,
      options: Array.isArray(f.options) ? f.options.map(str) : [],
      description: str(f.description),
    };
  });
}

function toOutcomes(raw: unknown): OutcomeDraft[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((r) => {
    const o = obj(r);
    return {
      key: newKey(),
      id: str(o.id),
      label: str(o.label),
      goal: o.goal === true,
      noContact: o.no_contact === true,
      conditions: toConditions(o.when),
    };
  });
}

export function toDraft(d: Definition): Draft {
  const agent = obj(d.agent);
  const analysis = d.analysis != null && typeof d.analysis === 'object' ? obj(d.analysis) : {};
  return {
    id: str(d.id),
    version: typeof d.version === 'number' ? d.version : null,
    name: str(agent.name),
    language: str(agent.language),
    voice: str(agent.voice),
    recordAudio: d.record_audio === true,
    recordingNotice: d.recording_notice === true,
    callSummaryEmail: d.call_summary_email === true,
    waSessionMinutes: typeof d.wa_session_minutes === 'number' ? d.wa_session_minutes : null,
    prompt: str(d.prompt),
    firstMessage: str(d.first_message),
    firstMessageAudio: d.first_message_audio === true,
    firstMessageDelayMs:
      typeof d.first_message_delay_ms === 'number' ? d.first_message_delay_ms : FIRST_MESSAGE_DELAY_MS,
    variables: toVariables(d.variables),
    analysis: {
      summary: analysis.summary !== false,
      instructions: str(analysis.instructions),
      fields: toFields(analysis.fields),
      outcomes: toOutcomes(analysis.outcomes),
    },
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
    workflows: toWorkflowsDraft(d.workflows),
    external: toExternalDraft(d.external),
  };
}

/** Sin datos, instrucciones ni resultados no hay analisis: el agente no extrae nada al terminar. */
export function hasAnalysis(a: AnalysisDraft): boolean {
  return a.fields.length > 0 || a.outcomes.length > 0 || a.instructions.trim() !== '';
}

/** Los datos del analisis como van a la definicion, en el orden de las filas. */
function fromFields(fields: FieldDraft[]): Record<string, unknown>[] {
  return fields.map((f) => ({
    name: f.name,
    ...(f.label.trim() ? { label: f.label } : {}),
    description: f.description,
    type: f.type,
    ...(f.type === 'choice' ? { options: f.options } : {}),
  }));
}

/** La lista de variables declaradas; '' en el nombre (una fila a medio completar) no se guarda. */
function fromVariables(variables: VariableDraft[]): Record<string, unknown>[] {
  return variables
    .filter((v) => v.name.trim())
    .map((v) => ({ name: v.name.trim(), default: v.default, description: v.description }));
}

export function fromDraft(draft: Draft): Definition {
  const last = draft.analysis.outcomes.length - 1;
  const handoff = fromHandoffDraft(draft.handoff);
  const workflows = fromWorkflowsDraft(draft.workflows);
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
      language: draft.language,
      ...(draft.voice ? { voice: draft.voice } : {}),
    },
    prompt: draft.prompt,
    first_message: draft.firstMessage,
    ...(draft.firstMessageAudio ? { first_message_audio: true } : {}),
    ...(draft.firstMessageDelayMs !== FIRST_MESSAGE_DELAY_MS
      ? { first_message_delay_ms: draft.firstMessageDelayMs }
      : {}),
    ...(draft.variables.length ? { variables: fromVariables(draft.variables) } : {}),
    ...(hasAnalysis(draft.analysis)
      ? {
          analysis: {
            summary: draft.analysis.summary,
            instructions: draft.analysis.instructions,
            fields: fromFields(draft.analysis.fields),
            outcomes: draft.analysis.outcomes.map((o, i) => ({
              id: o.id,
              label: o.label,
              // El ultimo es el resultado por defecto: sin condiciones.
              when: i === last ? {} : fromConditions(o.conditions),
              goal: o.goal,
              // Solo si esta marcado: las definiciones sin la bandera quedan igual.
              ...(o.noContact ? { no_contact: true } : {}),
            })),
          },
        }
      : {}),
    // Con tu propio agente, las herramientas son las suyas (el servidor rechaza tools con external).
    ...(!external && draft.clientTools.length ? { tools: toolEntries(draft).map((e) => e.value) } : {}),
    ...(!external && Object.keys(toolSettings).length ? { tool_settings: toolSettings } : {}),
    ...(handoff ? { handoff } : {}),
    // Tambien con tu propio agente: el pre-call y el post-call (el cobro) corren igual.
    ...(workflows ? { workflows } : {}),
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
  };
}

export function newVariable(variables: VariableDraft[]): VariableDraft {
  const names = new Set(variables.map((v) => v.name));
  let n = variables.length + 1;
  while (names.has(`variable_${n}`)) n++;
  return { key: newKey(), name: `variable_${n}`, default: '', description: '' };
}

/** Tiene un campo del analisis de tipo phone: el email del resumen lleva el teléfono. */
export function hasPhoneField(draft: Draft): boolean {
  return draft.analysis.fields.some((f) => f.type === 'phone');
}

/** Prender el resumen por email: el email lleva el teléfono, así que el análisis necesita un dato de tipo
 * phone (por el link no hay número y lo tiene que pedir). Si no lo tiene, se agrega al final. */
export function withPhoneField(draft: Draft): Draft {
  if (draft.external || hasPhoneField(draft)) return draft;
  const names = new Set(draft.analysis.fields.map((f) => f.name));
  let name = 'telefono';
  for (let n = 2; names.has(name); n++) name = `telefono_${n}`;
  const field: FieldDraft = {
    ...newField(draft.analysis.fields),
    name,
    label: 'Teléfono',
    type: 'phone',
    description: 'Teléfono de contacto de quien llama.',
  };
  return { ...draft, analysis: { ...draft.analysis, fields: [...draft.analysis.fields, field] } };
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
    conditions: [],
  };
}

/** Renombra un dato del analisis y lo que lo nombra (las condiciones de los resultados). */
export function renameField(draft: Draft, index: number, name: string): Draft {
  const old = draft.analysis.fields[index]?.name;
  if (old === undefined) return draft;
  const fix = (cs: ConditionDraft[]) => cs.map((c) => (c.field === old ? { ...c, field: name } : c));
  return {
    ...draft,
    analysis: {
      ...draft.analysis,
      fields: draft.analysis.fields.map((f, i) => (i === index ? { ...f, name } : f)),
      outcomes: draft.analysis.outcomes.map((o) => ({ ...o, conditions: fix(o.conditions) })),
    },
  };
}

export function move<T>(list: T[], from: number, to: number): T[] {
  if (to < 0 || to >= list.length) return list;
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item!);
  return next;
}

/** Conserva las claves de las filas ya abiertas después de guardar (la definición vuelve del servidor). */
export function keepKeys(draft: Draft, fresh: Draft): Draft {
  const keep = <T extends { key: string }>(old: T[], next: T[], id: (x: T) => string): T[] =>
    next.map((x) => {
      const prev = old.find((y) => id(y) === id(x));
      return prev ? { ...x, key: prev.key } : x;
    });
  return {
    ...fresh,
    variables: keep(draft.variables, fresh.variables, (v) => v.name),
    analysis: {
      ...fresh.analysis,
      fields: keep(draft.analysis.fields, fresh.analysis.fields, (f) => f.name),
      outcomes: keep(draft.analysis.outcomes, fresh.analysis.outcomes, (o) => o.id),
    },
  };
}

// ---------- variables ----------

/** Por qué `name` no sirve como variable (como el backend, app/conversation/variables.py), o null. */
export function variableNameError(
  name: string,
  catalog: { name_pattern?: string; reserved?: string[]; reserved_prefixes?: string[] } | undefined,
  taken: string[] = [],
  index = -1,
): string | null {
  const n = name.trim();
  if (!n) return 'Ponele un nombre.';
  if (catalog?.reserved?.includes(n)) return `${n} es del sistema.`;
  if (catalog?.reserved_prefixes?.some((p) => n.startsWith(p))) return `${n} es del sistema.`;
  let re = /^[a-z][a-z0-9_]{0,63}$/;
  try {
    if (catalog?.name_pattern) re = new RegExp(catalog.name_pattern);
  } catch {
    // un catálogo raro no rompe el formulario: se valida con la regla de siempre.
  }
  if (!re.test(n)) return 'Minúsculas, números y _; empieza con una letra (hasta 64).';
  if (taken.some((t, i) => i !== index && t.trim() === n)) return 'Repetida.';
  return null;
}

// ---------- errores del servidor ----------

/** Seccion del formulario donde va un error de validacion (ruta de pydantic). */
export type ErrorTarget =
  | {
      section:
        | 'agente'
        | 'voz'
        | 'modelo'
        | 'prompt'
        | 'primer_mensaje'
        | 'variables'
        | 'analisis'
        | 'herramientas'
        | 'derivacion'
        | 'automaticas'
        | 'externo';
    }
  | { section: 'variable'; key: string }
  | { section: 'dato'; key: string }
  | { section: 'resultado'; key: string };

/** El resultado de una ruta: por indice (pydantic) o por id (validaciones propias). */
function outcomeAt(draft: Draft, seg: string | undefined): OutcomeDraft | undefined {
  if (seg === undefined) return undefined;
  const list = draft.analysis.outcomes;
  return /^\d+$/.test(seg) ? list[Number(seg)] : list.find((o) => o.id === seg);
}

/** La fila de una lista por indice (las dos son listas en la definicion). */
function at<T>(list: T[], seg: string | undefined): T | undefined {
  if (seg === undefined || !/^\d+$/.test(seg)) return undefined;
  return list[Number(seg)];
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
  if (head === 'prompt') return { section: 'prompt' };
  // La espera y el audio pregenerado son del primer mensaje.
  if (head === 'first_message' || head === 'first_message_audio' || head === 'first_message_delay_ms')
    return { section: 'primer_mensaje' };
  if (head === 'variables') {
    const v = at(draft.variables, second);
    return v ? { section: 'variable', key: v.key } : { section: 'variables' };
  }
  if (head === 'tools' || head === 'tool_settings') return { section: 'herramientas' };
  if (head === 'llm' || head === 'generation') return { section: 'modelo' };
  if (head === 'handoff') return { section: 'derivacion' };
  if (head === 'workflows') return { section: 'automaticas' };
  if (head === 'external') return { section: 'externo' };
  if (head === 'analysis') {
    if (second === 'fields') {
      const f = at(draft.analysis.fields, third);
      return f ? { section: 'dato', key: f.key } : { section: 'analisis' };
    }
    if (second === 'outcomes') {
      const o = outcomeAt(draft, third);
      return o ? { section: 'resultado', key: o.key } : { section: 'analisis' };
    }
    return { section: 'analisis' };
  }
  return null;
}

const PATH_WORDS: Record<string, string> = {
  agent: 'Agente',
  name: 'nombre',
  language: 'idioma',
  voice: 'voz',
  record_audio: 'grabar audio',
  recording_notice: 'avisar que se graba',
  call_summary_email: 'resumen por email',
  wa_session_minutes: 'ventana de contexto de WhatsApp',
  prompt: 'Prompt',
  first_message: 'Primer mensaje',
  first_message_audio: 'audio pregenerado',
  first_message_delay_ms: 'espera antes del primer mensaje',
  variables: 'Variables',
  default: 'valor por defecto',
  description: 'descripción',
  analysis: 'Análisis al terminar',
  summary: 'resumen',
  instructions: 'instrucciones',
  fields: 'Datos',
  label: 'etiqueta',
  type: 'tipo',
  options: 'opciones',
  outcomes: '',
  id: 'ID',
  when: 'condiciones',
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
  workflows: 'Automáticas',
  pre_call: 'antes de la conversación',
  post_call: 'después de la conversación',
  timeout_ms: 'tiempo máximo',
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

/** "analysis.fields.0.description" -> "Análisis al terminar › Datos › contacto › descripción". */
export function pathLabel(draft: Draft, path: string): string {
  const parts = path.split('.');
  const out: string[] = [];
  parts.forEach((p, i) => {
    const prev = parts[i - 1];
    if (prev === 'variables' && /^\d+$/.test(p))
      out.push(draft.variables[Number(p)]?.name || `variable ${Number(p) + 1}`);
    else if (prev === 'fields' && /^\d+$/.test(p))
      out.push(draft.analysis.fields[Number(p)]?.name || `dato ${Number(p) + 1}`);
    else if (prev === 'outcomes') {
      const o = outcomeAt(draft, p);
      out.push(o?.label || o?.id || p);
    } else if (prev === 'rules' && /^\d+$/.test(p)) out.push(`regla ${Number(p) + 1}`);
    else if (prev === 'stages' && /^\d+$/.test(p)) out.push(`etapa ${Number(p) + 1}`);
    else if (prev === 'areas' && /^\d+$/.test(p)) out.push(`área ${Number(p) + 1}`);
    else if (prev === 'tools' && /^\d+$/.test(p))
      out.push(toolEntries(draft)[Number(p)]?.name || `herramienta ${Number(p) + 1}`);
    else if (PATH_WORDS[p] !== '') out.push(PATH_WORDS[p] ?? p);
  });
  return out.join(' › ');
}
