import type { Definition } from '@/api/types';

// Vista tipada (y tolerante) de la definicion de un agente: app/conversation/models.py, clase Workflow.

export interface FieldSpec {
  name: string;
  label: string;
  description: string;
  type: string;
  options: string[] | null;
}

export interface Outcome {
  id: string;
  label: string;
  when: Record<string, unknown>;
  goal: boolean;
  noContact: boolean;
}

export interface VariableSpec {
  name: string;
  default: string;
  description: string;
}

export interface WorkflowView {
  id: string;
  version: number | null;
  /** Tu propio agente (definition.external). */
  external: boolean;
  agent: { name: string; language: string; voice: string | null };
  recordAudio: boolean;
  /** Llamadas: resumen por email al cliente al terminar. */
  callSummaryEmail: boolean;
  /** WhatsApp: ventana de contexto temporal (minutos sin mensaje del contacto para abrir otra
   * conversacion). null = el default global del servidor (1440 min = 24 hs). */
  waSessionMinutes: number | null;
  /** Etapas del LLM (workflow.llm); vacio = siempre el servidor propio. */
  llm: { fromTurn: number; connection: string | null; model: string }[];
  /** Lo que va al LLM tal cual, con sus {{variables}}. */
  prompt: string;
  firstMessage: string;
  firstMessageAudio: boolean;
  firstMessageDelayMs: number;
  /** Variables declaradas, en el orden en que se guardaron. */
  variables: VariableSpec[];
  summary: boolean;
  analysisInstructions: string;
  fields: FieldSpec[];
  outcomes: Outcome[];
  /** Herramientas del cliente (APIs y codigo), por slug. */
  clientTools: { tool: string }[];
}

const obj = (x: unknown): Record<string, unknown> =>
  x && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : {};
const str = (x: unknown): string => (typeof x === 'string' ? x : x == null ? '' : String(x));

/** Un default de variable tal como se editó: número o booleano se muestran igual. */
const value = (x: unknown): string =>
  typeof x === 'string' ? x : typeof x === 'number' || typeof x === 'boolean' ? String(x) : '';

export function readWorkflow(d: Definition): WorkflowView {
  const agent = obj(d.agent);
  const analysis = obj(d.analysis);
  const fields = (Array.isArray(analysis.fields) ? analysis.fields : []).map((raw): FieldSpec => {
    const f = obj(raw);
    return {
      name: str(f.name),
      label: str(f.label),
      description: str(f.description),
      type: str(f.type) || 'string',
      options: Array.isArray(f.options) ? f.options.map(str) : null,
    };
  });
  const outcomes = (Array.isArray(analysis.outcomes) ? analysis.outcomes : []).map((raw) => {
    const o = obj(raw);
    return {
      id: str(o.id),
      label: str(o.label),
      when: obj(o.when),
      goal: o.goal === true,
      noContact: o.no_contact === true,
    };
  });
  return {
    id: str(d.id),
    version: typeof d.version === 'number' ? d.version : null,
    external: d.external != null && typeof d.external === 'object',
    agent: {
      name: str(agent.name),
      language: str(agent.language),
      voice: agent.voice ? str(agent.voice) : null,
    },
    recordAudio: d.record_audio === true,
    callSummaryEmail: d.call_summary_email === true,
    waSessionMinutes: typeof d.wa_session_minutes === 'number' ? d.wa_session_minutes : null,
    llm: (Array.isArray(obj(d.llm).stages) ? (obj(d.llm).stages as unknown[]) : []).map((raw) => {
      const st = obj(raw);
      return {
        fromTurn: typeof st.from_turn === 'number' ? st.from_turn : 1,
        connection: typeof st.connection === 'string' && st.connection ? st.connection : null,
        model: str(st.model),
      };
    }),
    prompt: str(d.prompt),
    firstMessage: str(d.first_message),
    firstMessageAudio: d.first_message_audio === true,
    firstMessageDelayMs: typeof d.first_message_delay_ms === 'number' ? d.first_message_delay_ms : 200,
    variables: (Array.isArray(d.variables) ? d.variables : []).map((raw): VariableSpec => {
      const v = obj(raw);
      return { name: str(v.name), default: value(v.default), description: str(v.description) };
    }),
    summary: analysis.summary !== false,
    analysisInstructions: str(analysis.instructions),
    fields,
    outcomes,
    clientTools: (Array.isArray(d.tools) ? d.tools : [])
      .filter((raw) => obj(raw).tool != null)
      .map((raw) => ({ tool: str(obj(raw).tool) })),
  };
}

/** Las primeras `lines` líneas de un texto, para la vista en limpio. */
export function firstLines(text: string, lines = 6): string {
  return text.split('\n').slice(0, lines).join('\n').trim();
}

export function conditionLabel(when: Record<string, unknown>): string {
  const entries = Object.entries(when);
  if (!entries.length) return 'en otro caso';
  return entries.map(([k, v]) => `${k} = ${String(v)}`).join(' y ');
}

/** JSON indentado para el editor. */
export function toJsonText(d: unknown): string {
  return JSON.stringify(d, null, 2);
}

/**
 * Posicion aproximada de una ruta de error (ej. "analysis.fields.0.description") en el texto
 * JSON: busca cada clave en orden. Indices de listas se saltean. -1 si no la encuentra.
 */
export function findPathOffset(text: string, path: string): number {
  if (!path) return -1;
  let pos = 0;
  let found = -1;
  for (const seg of path.split('.')) {
    if (/^\d+$/.test(seg)) continue;
    const i = text.indexOf(JSON.stringify(seg) + ':', pos);
    const j = i >= 0 ? i : text.indexOf(JSON.stringify(seg), pos);
    if (j < 0) break;
    found = j;
    pos = j + seg.length + 2;
  }
  return found;
}

export type Parsed = { ok: true; value: Definition } | { ok: false; error: string };

export function parseDefinition(text: string): Parsed {
  try {
    const value: unknown = JSON.parse(text);
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return { ok: false, error: 'La definición tiene que ser un objeto JSON ({...}).' };
    }
    return { ok: true, value: value as Definition };
  } catch (e) {
    return { ok: false, error: `JSON inválido: ${e instanceof Error ? e.message : String(e)}` };
  }
}
