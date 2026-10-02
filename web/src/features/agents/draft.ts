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
] as const;

export type FieldType = (typeof FIELD_TYPES)[number]['value'];
export type Engine = 'classic' | 'structured';

export const ENGINE_HELP: Record<Engine, string> = {
  classic:
    'Conversa en texto con un prompt de sistema armado de esta definición y extrae los datos al final de la conversación. Es el motor por defecto.',
  structured:
    'En cada turno el LLM responde en JSON (mensaje, objetivo siguiente y estado) y otra llamada extrae los datos y lleva el estado de la conversación.',
};

/** id del elemento de una seccion del formulario (para llevar a un error). */
export const sectionId = (name: string) => `def-${name}`;
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
  message: string;
  conditions: ConditionDraft[];
}

export interface RuleDraft {
  key: string;
  text: string;
}

export interface Draft {
  id: string;
  version: number | null;
  engine: Engine;
  name: string;
  role: string;
  language: string;
  /** '' = la predeterminada (VLLM_TTS_VOICE). */
  voice: string;
  objective: string;
  opening: string;
  rules: RuleDraft[];
  knowledge: string;
  fields: FieldDraft[];
  outcomes: OutcomeDraft[];
}

let seq = 0;
/** Clave estable para las listas del formulario (no va a la definicion). */
export const newKey = () => `k${++seq}`;

const obj = (x: unknown): Record<string, unknown> =>
  x && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : {};
const str = (x: unknown): string => (typeof x === 'string' ? x : x == null ? '' : String(x));
const isType = (t: string): t is FieldType => FIELD_TYPES.some((f) => f.value === t);

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
        type: isType(type) ? type : 'string',
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
    engine: d.engine === 'structured' ? 'structured' : 'classic',
    name: str(agent.name),
    role: str(agent.role),
    language: str(agent.language),
    voice: str(agent.voice),
    objective: str(obj(d.objective).description),
    opening: str(conv.opening),
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
        message: str(o.message),
        conditions: toConditions(o.when),
      };
    }),
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
  return {
    id: draft.id,
    ...(draft.version != null ? { version: draft.version } : {}),
    engine: draft.engine,
    agent: {
      name: draft.name,
      role: draft.role,
      language: draft.language,
      ...(draft.voice ? { voice: draft.voice } : {}),
    },
    objective: { description: draft.objective },
    conversation: {
      opening: draft.opening,
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
      })),
    },
  };
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

export function newOutcome(outcomes: OutcomeDraft[]): OutcomeDraft {
  const ids = new Set(outcomes.map((o) => o.id));
  let n = outcomes.length;
  while (ids.has(`resultado_${n}`)) n++;
  return { key: newKey(), id: `resultado_${n}`, label: '', goal: false, message: '', conditions: [] };
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
  | { section: 'agente' | 'voz' | 'objetivo' | 'reglas' | 'conocimiento' | 'datos' | 'resultados' }
  | { section: 'dato'; key: string }
  | { section: 'resultado'; key: string };

/** Resultado de una ruta de error: por indice (pydantic) o por id (validaciones propias). */
function outcomeAt(draft: Draft, seg: string | undefined): OutcomeDraft | undefined {
  if (seg === undefined) return undefined;
  return /^\d+$/.test(seg) ? draft.outcomes[Number(seg)] : draft.outcomes.find((o) => o.id === seg);
}

export function errorTarget(draft: Draft, path: string): ErrorTarget | null {
  const [head, second, third] = path.split('.');
  if (head === 'engine') return { section: 'agente' };
  if (head === 'agent') return { section: second === 'voice' ? 'voz' : 'agente' };
  if (head === 'objective') return { section: 'objetivo' };
  if (head === 'conversation') return { section: second === 'rules' ? 'reglas' : 'objetivo' };
  if (head === 'knowledge') return { section: 'conocimiento' };
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
  engine: 'Motor',
  objective: 'Objetivo',
  conversation: 'Conversación',
  opening: 'apertura',
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
    else if (PATH_WORDS[p] !== '') out.push(PATH_WORDS[p] ?? p);
  });
  return out.join(' › ');
}
