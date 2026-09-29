import type { Definition } from '@/api/types';

// Vista tipada (y tolerante) de la definicion de un agente: app/conversation/models.py, clase Workflow.

export interface FieldSpec {
  priority: number;
  description: string;
  type: string;
  options?: string[] | null;
  required: boolean;
  required_if?: Record<string, unknown> | null;
  question: string;
}

export interface Outcome {
  id: string;
  label: string;
  when: Record<string, unknown>;
  message: string;
  goal: boolean;
}

export interface WorkflowView {
  id: string;
  version: number | null;
  engine: string;
  agent: { name: string; role: string; language: string; voice: string | null };
  objective: string;
  opening: string;
  rules: string[];
  knowledge: string;
  fields: [string, FieldSpec][];
  outcomes: Outcome[];
}

const obj = (x: unknown): Record<string, unknown> =>
  x && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : {};
const str = (x: unknown): string => (typeof x === 'string' ? x : x == null ? '' : String(x));

export function readWorkflow(d: Definition): WorkflowView {
  const agent = obj(d.agent);
  const conv = obj(d.conversation);
  const fields = Object.entries(obj(d.fields)).map(([name, raw]): [string, FieldSpec] => {
    const f = obj(raw);
    return [
      name,
      {
        priority: typeof f.priority === 'number' ? f.priority : 0,
        description: str(f.description),
        type: str(f.type) || 'string',
        options: Array.isArray(f.options) ? f.options.map(str) : null,
        required: f.required === true,
        required_if: f.required_if ? obj(f.required_if) : null,
        question: str(f.question),
      },
    ];
  });
  fields.sort((a, b) => a[1].priority - b[1].priority);
  const outcomes = (
    Array.isArray(obj(d.completion).outcomes) ? (obj(d.completion).outcomes as unknown[]) : []
  ).map((raw) => {
    const o = obj(raw);
    return {
      id: str(o.id),
      label: str(o.label),
      when: obj(o.when),
      message: str(o.message),
      goal: o.goal === true,
    };
  });
  return {
    id: str(d.id),
    version: typeof d.version === 'number' ? d.version : null,
    engine: str(d.engine) || 'structured',
    agent: {
      name: str(agent.name),
      role: str(agent.role),
      language: str(agent.language),
      voice: agent.voice ? str(agent.voice) : null,
    },
    objective: str(obj(d.objective).description).trim(),
    opening: str(conv.opening).trim(),
    rules: Array.isArray(conv.rules) ? conv.rules.map(str) : [],
    knowledge: str(d.knowledge).trim(),
    fields,
    outcomes,
  };
}

/** "Sí", "No" o "Si a = x y b = y". */
export function requiredLabel(f: FieldSpec): string {
  if (f.required_if && Object.keys(f.required_if).length) {
    return `Si ${Object.entries(f.required_if)
      .map(([k, v]) => `${k} = ${String(v)}`)
      .join(' y ')}`;
  }
  return f.required ? 'Sí' : 'No';
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
 * Posicion aproximada de una ruta de error (ej. "fields.zone.question") en el texto
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
