// Progreso de una derivación a una persona, que el worker publica en el tema de datos `handoff_status`
// (docs/features/EQUIPO_TELEFONIA.md). Módulo puro, sin React ni DOM: lo usan el modal de la prueba del panel
// (React) y la página del link para llamar (TS plano). Cada mensaje es un snapshot completo: uno perdido lo
// corrige el siguiente.

export const HANDOFF_TOPIC = 'handoff_status';

/** `names`: prueba del panel (con el nombre de la persona). `anonymous`: link público ("Persona 2"). */
export type HandoffMode = 'names' | 'anonymous';

export type HandoffState = 'running' | 'connected' | 'failed' | 'notified';
export type PhaseSeconds = [phase: string, seconds: number];

export interface HandoffLeg {
  /** Posición de la persona entre las que se prueban en esa área, y cuántas son. */
  n: number;
  of: number | null;
  area: string | null;
  person: string | null;
  /** Es la persona de "Si nadie atiende". */
  no_answer: boolean;
  /** Nulo mientras el intento sigue en curso. */
  result: string | null;
  phases: PhaseSeconds[];
  total: number;
}

export interface HandoffReroute {
  at: number;
  from: string | null;
  to: string | null;
  reason: string | null;
}

export interface HandoffSnapshot {
  v: 1;
  id: number;
  state: HandoffState;
  result: string | null;
  area: string | null;
  elapsed: number;
  phase: string | null;
  /** `null` entre intentos (sin fase en curso); se cuenta como 0. */
  phase_elapsed: number | null;
  pre: PhaseSeconds[];
  reroutes: HandoffReroute[];
  legs: HandoffLeg[];
  total: number | null;
}

const PHASES: Record<string, string> = {
  preparing: 'Preparando',
  announcing: 'Avisándote',
  notifying: 'Avisando al equipo',
  dialing: 'Marcando',
  ringing: 'Sonando',
  summary: 'Armando el resumen',
  whisper: 'Contándole el caso',
  waiting_digit: 'Esperando que marque 1',
};

const RESULTS: Record<string, string> = {
  confirmed: 'Atendió',
  no_answer: 'No atendió',
  busy: 'Ocupado',
  failed: 'No se pudo llamar',
  machine: 'Buzón de voz',
  not_confirmed: 'Atendió y no confirmó',
};

/** Cómo termina una derivación que no conectó (motivo del snapshot final). */
const FAILURES: Record<string, string> = {
  no_answer: 'Nadie atendió',
  busy: 'Estaban ocupados',
  failed: 'No se pudo llamar',
  machine: 'Atendió un buzón de voz',
  not_confirmed: 'Nadie confirmó',
  after_hours: 'Fuera de horario',
  no_members: 'No había nadie a quien llamar',
  no_channel: 'No había líneas libres',
  outbound_minutes: 'Sin minutos de salida',
  too_many_attempts: 'Demasiados intentos',
  unknown_area: 'El área no existe',
  customer_hung_up: 'Cortaste antes de que atendieran',
  error: 'Falló la derivación',
};

export function phaseLabel(phase: string | null | undefined): string {
  return (phase && PHASES[phase]) || '';
}

export function resultLabel(result: string | null | undefined): string {
  return (result && RESULTS[result]) || '';
}

const num = (v: unknown, fallback = 0): number => (typeof v === 'number' && Number.isFinite(v) ? v : fallback);
const str = (v: unknown): string | null => (typeof v === 'string' && v ? v : null);

function phases(v: unknown): PhaseSeconds[] {
  if (!Array.isArray(v)) return [];
  return v.flatMap((p): PhaseSeconds[] =>
    Array.isArray(p) && typeof p[0] === 'string' ? [[p[0], num(p[1])]] : [],
  );
}

const STATES: HandoffState[] = ['running', 'connected', 'failed', 'notified'];

/** Lee un mensaje del tema (bytes, texto u objeto). Tolerante: `null` si no es JSON o `v` no es 1. */
export function parseHandoffStatus(raw: unknown): HandoffSnapshot | null {
  let msg: unknown = raw;
  try {
    if (ArrayBuffer.isView(raw)) msg = JSON.parse(new TextDecoder().decode(raw));
    else if (typeof raw === 'string') msg = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!msg || typeof msg !== 'object') return null;
  const m = msg as Record<string, unknown>;
  if (m.v !== 1) return null;
  const state = STATES.find((s) => s === m.state);
  if (!state) return null;
  const legs = (Array.isArray(m.legs) ? m.legs : []).flatMap((l): HandoffLeg[] => {
    if (!l || typeof l !== 'object') return [];
    const o = l as Record<string, unknown>;
    return [
      {
        n: num(o.n),
        of: typeof o.of === 'number' && o.of > 0 ? o.of : null,
        area: str(o.area),
        person: str(o.person),
        no_answer: o.no_answer === true,
        result: str(o.result),
        phases: phases(o.phases),
        total: num(o.total),
      },
    ];
  });
  const reroutes = (Array.isArray(m.reroutes) ? m.reroutes : []).flatMap((r): HandoffReroute[] => {
    if (!r || typeof r !== 'object') return [];
    const o = r as Record<string, unknown>;
    return [{ at: num(o.at), from: str(o.from), to: str(o.to), reason: str(o.reason) }];
  });
  return {
    v: 1,
    id: num(m.id),
    state,
    result: str(m.result),
    area: str(m.area),
    elapsed: num(m.elapsed),
    phase: str(m.phase),
    phase_elapsed: typeof m.phase_elapsed === 'number' && Number.isFinite(m.phase_elapsed) ? m.phase_elapsed : null,
    pre: phases(m.pre),
    reroutes,
    legs,
    total: typeof m.total === 'number' && Number.isFinite(m.total) ? m.total : null,
  };
}

/** Segundos de la derivación y de la fase actual a las `now`: lo que dijo el worker + lo que pasó desde que llegó. */
export function liveSeconds(s: HandoffSnapshot, receivedAt: number, now: number): { total: number; phase: number } {
  if (s.state !== 'running') return { total: s.total ?? s.elapsed, phase: s.phase_elapsed ?? 0 };
  const since = Math.max(0, (now - receivedAt) / 1000);
  return { total: s.elapsed + since, phase: (s.phase_elapsed ?? 0) + since };
}

export function seconds(v: number): string {
  const s = Math.max(0, Math.round(v));
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

const timed = (label: string, t: number) => `${label}: ${seconds(t)}`;

/** Fases ya cerradas; las de menos de medio segundo no se muestran ("Armando el resumen: 0 s" no dice nada). */
function phaseList(list: PhaseSeconds[]): string {
  return list
    .filter(([p, t]) => phaseLabel(p) && t >= 0.5)
    .map(([p, t]) => timed(phaseLabel(p), t))
    .join(' · ');
}

export interface AttemptView {
  /** "Ana (Ventas)" o "Persona 2 de 3". */
  who: string;
  /** Para "Llamando a …" y "Conectado con …": "Ana (Ventas)" o "la persona 2 de 3". */
  whom: string;
  /** "Si nadie atiende: Ana" / "Si nadie atiende: persona 3"; vacío en un intento común. */
  note: string;
  /** Vacío mientras el intento sigue en curso. */
  result: string;
  /** "Marcando: 2 s · Sonando: 20 s". */
  detail: string;
}

export interface HandoffView {
  state: HandoffState;
  /** Título: a quién se llama, o cómo terminó. */
  headline: string;
  note: string;
  /** Fase actual con su contador ("Sonando: 12 s"); vacío al terminar. */
  live: string;
  /** Tiempo total desde que empezó la derivación; al terminar, el final del worker. */
  total: string;
  /** Intentos ya resueltos (todos, al terminar), del más viejo al más nuevo. */
  attempts: AttemptView[];
  /** Etapas previas al primer intento ("Preparando: 1 s · Avisándote: 3 s") y pases entre áreas. */
  extra: string[];
}

function attempt(l: HandoffLeg, mode: HandoffMode): AttemptView {
  const names = mode === 'names';
  const person = names ? l.person : null;
  const nth = l.of && l.n <= l.of ? `Persona ${l.n} de ${l.of}` : `Persona ${l.n}`;
  const who = person ? (l.area ? `${person} (${l.area})` : person) : nth;
  return {
    who,
    whom: person ? who : `la ${nth.charAt(0).toLowerCase()}${nth.slice(1)}`,
    note: l.no_answer ? `Si nadie atiende: ${person ?? `persona ${l.n}`}` : '',
    result: resultLabel(l.result),
    detail: phaseList(l.phases),
  };
}

/** Lo que muestran las dos pantallas, calculado igual para ambas. */
export function buildView(s: HandoffSnapshot, mode: HandoffMode, receivedAt: number, now: number): HandoffView {
  const t = liveSeconds(s, receivedAt, now);
  const names = mode === 'names';
  const last = s.legs.at(-1);
  const current = s.state === 'running' && last && last.result === null ? last : null;
  const done = s.legs.filter((l) => l !== current).map((l) => attempt(l, mode));
  const extra: string[] = [];
  const pre = phaseList(s.pre);
  if (pre) extra.push(pre);
  if (names)
    for (const r of s.reroutes)
      if (r.to) extra.push(`Pasó ${r.from ? `de ${r.from} ` : ''}a ${r.to}${r.reason ? ` (${failure(r.reason)})` : ''}`);

  let headline: string;
  let note = '';
  let live = '';
  if (s.state === 'running') {
    if (current) {
      const a = attempt(current, mode);
      headline = `Llamando a ${a.whom}`;
      note = a.note;
      const earlier = phaseList(current.phases);
      live = s.phase ? timed(phaseLabel(s.phase), t.phase) : '';
      if (earlier && live) live = `${live} · antes: ${earlier}`;
    } else {
      headline = s.legs.length
        ? 'Buscando a la siguiente persona'
        : s.phase === 'preparing' || !s.phase
          ? 'Preparando la derivación'
          : phaseLabel(s.phase);
      if (names && s.area) headline += ` (${s.area})`;
      live = s.phase ? timed(phaseLabel(s.phase), t.phase) : '';
    }
  } else if (s.state === 'connected') {
    const winner = [...s.legs].reverse().find((l) => l.result === 'confirmed') ?? last;
    headline = winner ? `Conectado con ${attempt(winner, mode).whom}` : 'Conectado';
  } else if (s.state === 'notified') {
    headline = names && s.area ? `Se avisó a ${s.area}` : 'Se avisó al equipo';
  } else {
    headline = `No se pudo derivar: ${failure(s.result)}`;
  }
  return { state: s.state, headline, note, live, total: seconds(t.total), attempts: done, extra };
}

function failure(reason: string | null): string {
  return (reason && FAILURES[reason]) || 'sin respuesta';
}
