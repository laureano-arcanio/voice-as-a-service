import type { PhoneNumber, PhoneNumberUpdate } from '@/api/types';
import { type ScheduleDraft, toDraft, toSchedule } from '@/features/team/schedule';

// Quién atiende las entrantes de un número (docs/features/EQUIPO_TELEFONIA.md): el equipo (las
// personas del número, en orden) o el agente.

export type AnswerMode = 'team' | 'agent';
export type RingFirst = 'phone' | 'panel';
export type TeamFallback = 'agent' | 'member' | 'voicemail' | 'hangup';
export type Strategy = NonNullable<PhoneNumberUpdate['strategy']>;

export const RING_FIRST_OPTIONS: { value: RingFirst; label: string }[] = [
  { value: 'phone', label: 'En su teléfono' },
  { value: 'panel', label: 'En el panel' },
];

export const RING_FIRST_HELP: Record<RingFirst, string> = {
  phone:
    'Llama al teléfono de cada persona, en orden. Si ninguna atiende, suena en el panel a las que estén Disponibles.',
  panel:
    'Suena en el panel a las personas Disponibles, a todas a la vez. Si nadie atiende, llama a sus teléfonos en orden.',
};

/** Ayuda de En orden / Rotativa en un número: el panel suena a todas a la vez, solo el teléfono rota. */
export const STRATEGY_HELP: Record<Strategy, string> = {
  sequential: 'Siempre empieza por la primera persona de la lista y sigue en orden.',
  round_robin:
    'En los teléfonos, empieza por la siguiente a la última que atendió (marcó 1), para repartirlas. En el panel suena a todas a la vez y no rota.',
};

/** ayuda de los switches de la espera: conectar al atender y música (docs/features/EQUIPO_TELEFONIA.md). */
export const CONNECT_ON_ANSWER_HELP =
  'Para una central telefónica: la llamada se conecta apenas atienden, sin mensaje ni tecla. No reconoce contestadores.';
export const CONNECT_ON_ANSWER_PANEL_HELP = 'Vale para los teléfonos; el panel se atiende con un clic.';
export const HOLD_MUSIC_HELP = 'Apagado, quien llama espera en silencio hasta que atiendan.';

/** Grabar la llamada completa (Asterisk, docs/features/EQUIPO_TELEFONIA.md): vale para las dos formas de atender. */
export const RECORD_FULL_CALL_HELP =
  'Guarda el audio entero de la llamada, de quien llama y de quien atiende, como respaldo. Solo llamadas por teléfono: no incluye el link para llamar, la prueba del panel ni WhatsApp.';

export const FALLBACK_LABELS: Record<TeamFallback, string> = {
  agent: 'Pasa al agente',
  member: 'Llama a una persona',
  voicemail: 'Deja un mensaje y graba lo que dice quien llama',
  hangup: 'Dice el mensaje y corta',
};

/** El mensaje que dice el número si no se escribe uno (el del worker). */
export const FALLBACK_MESSAGE_DEFAULTS: Record<'voicemail' | 'hangup', string> = {
  voicemail: 'Ahora no podemos atenderte. Dejá tu mensaje y te llamamos.',
  hangup: 'Ahora no podemos atenderte. Por favor, volvé a llamar más tarde.',
};

export const MESSAGE_MAX = 500;

/** Reintentos de la entrante al equipo (docs/features/EQUIPO_TELEFONIA.md): cuánto, cada cuánto y qué se avisa. */
export const RETRY_SECONDS = [0, 60, 120, 180, 300];
export const RETRY_INTERVALS = [15, 30, 60];
export const RETRY_INTERVAL_DEFAULT = 30;
/** El aviso que dice el worker si no se escribe uno. */
export const RETRY_MESSAGE_DEFAULT = 'En este momento no podemos atenderte. Por favor, esperá en línea.';
export const RETRY_HELP =
  'Si da ocupado o no atiende, le avisa a quien llama, lo deja en espera y vuelve a llamar. La espera gasta minutos entrantes.';
export const RETRY_INTERVAL_HELP = 'Espera con música entre un intento y el siguiente.';
export const RETRY_MESSAGE_HELP = 'Lo dice una vez, antes de la espera. Vacío usa el de siempre.';
export const RING_SECONDS_HELP = 'Segundos antes de pasar a la siguiente.';
export const RING_SECONDS_RETRY_HELP = `${RING_SECONDS_HELP} El buzón de un celular atiende a los ~33 s.`;

/** "3 min", "1 min", "45 s": como se dice en la fila y en el "Cada". */
export const shortSeconds = (s: number) => (s % 60 === 0 ? `${s / 60} min` : `${s} s`);

const retryDuration = (s: number) =>
  s === 0
    ? 'No, pasar al respaldo'
    : s % 60 === 0
      ? `Durante ${s / 60} ${s === 60 ? 'minuto' : 'minutos'}`
      : `Durante ${s} s`;

/** Las opciones de cuánto reintentar; un valor que dejó la API (múltiplo de 15) se agrega para no perderlo. */
export function retryOptions(current: number): { value: string; label: string }[] {
  const all = RETRY_SECONDS.includes(current) ? RETRY_SECONDS : [...RETRY_SECONDS, current].sort((a, b) => a - b);
  return all.map((s) => ({ value: String(s), label: retryDuration(s) }));
}

/** Las opciones de la espera entre intentos; un valor de la API fuera de la lista (15-120) se agrega. */
export function retryIntervalOptions(current: number): { value: string; label: string }[] {
  const all = RETRY_INTERVALS.includes(current) ? RETRY_INTERVALS : [...RETRY_INTERVALS, current].sort((a, b) => a - b);
  return all.map((s) => ({ value: String(s), label: shortSeconds(s) }));
}

/** " · reintenta 3 min cada 30 s" para la fila; vacío sin reintentos. */
export const retrySummary = (n: Pick<PhoneNumber, 'team_retry_seconds' | 'team_retry_interval_seconds'>) =>
  n.team_retry_seconds > 0
    ? ` · reintenta ${shortSeconds(n.team_retry_seconds)} cada ${shortSeconds(n.team_retry_interval_seconds)}`
    : '';

/** Lo que se edita de un número asignado. */
export interface AnsweringDraft {
  label: string;
  answer_mode: AnswerMode;
  agent_id: string;
  member_ids: string[];
  strategy: Strategy;
  ring_first: RingFirst;
  ring_seconds: number | string;
  team_connect_on_answer: boolean;
  team_hold_music: boolean;
  record_full_call: boolean;
  /** 0 = no reintenta. */
  team_retry_seconds: number;
  team_retry_interval_seconds: number;
  team_retry_message: string;
  schedule: ScheduleDraft;
  team_fallback: TeamFallback;
  /** Con team_fallback member: la persona, fuera del número, con teléfono. */
  team_fallback_member_id: string | null;
  team_fallback_message: string;
}

export function toAnsweringDraft(n: PhoneNumber): AnsweringDraft {
  return {
    label: n.label,
    answer_mode: n.answer_mode,
    agent_id: n.agent_id ?? '',
    member_ids: (n.members ?? []).map((m) => m.id),
    strategy: n.strategy,
    ring_first: n.ring_first,
    ring_seconds: n.ring_seconds,
    team_connect_on_answer: n.team_connect_on_answer,
    team_hold_music: n.team_hold_music,
    record_full_call: n.record_full_call,
    team_retry_seconds: n.team_retry_seconds,
    team_retry_interval_seconds: n.team_retry_interval_seconds,
    team_retry_message: n.team_retry_message,
    schedule: toDraft(n.schedule),
    team_fallback: n.team_fallback,
    team_fallback_member_id: n.team_fallback_member_id ?? null,
    team_fallback_message: n.team_fallback_message,
  };
}

/**
 * El PATCH de un número asignado. Con el agente, solo manda el modo, el agente y la grabación (lo del equipo queda como
 * está); con el equipo, todo lo del equipo y el agente, que es el de respaldo.
 */
export function toAnsweringBody(v: AnsweringDraft): PhoneNumberUpdate {
  const base: PhoneNumberUpdate = {
    label: v.label.trim(),
    answer_mode: v.answer_mode,
    agent_id: v.agent_id || null,
    record_full_call: v.record_full_call,
  };
  if (v.answer_mode === 'agent') return base;
  return {
    ...base,
    member_ids: v.member_ids,
    strategy: v.strategy,
    ring_first: v.ring_first,
    ring_seconds: Number(v.ring_seconds),
    team_connect_on_answer: v.team_connect_on_answer,
    team_hold_music: v.team_hold_music,
    team_retry_seconds: v.team_retry_seconds,
    team_retry_interval_seconds: v.team_retry_interval_seconds,
    team_retry_message: v.team_retry_message.trim(),
    schedule: toSchedule(v.schedule),
    team_fallback: v.team_fallback,
    team_fallback_member_id: v.team_fallback === 'member' ? v.team_fallback_member_id : null,
    team_fallback_message: v.team_fallback_message.trim(),
  };
}

/** Las personas del número, en orden. */
export const numberMembers = (n: PhoneNumber) => n.members ?? [];

/** El equipo está elegido pero no tiene personas: las entrantes van al agente del número, o no se atienden. */
export const teamWithoutPeople = (n: PhoneNumber) =>
  n.answer_mode === 'team' && numberMembers(n).length === 0;
