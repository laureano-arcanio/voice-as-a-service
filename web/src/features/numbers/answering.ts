import type { PhoneNumber, PhoneNumberUpdate } from '@/api/types';
import { type ScheduleDraft, toDraft, toSchedule } from '@/features/team/schedule';

// Quién atiende las entrantes de un número (docs/features/EQUIPO_TELEFONIA.md): el equipo (las
// personas del número, en orden) o el agente.

export type AnswerMode = 'team' | 'agent';
export type RingFirst = 'phone' | 'panel';
export type TeamFallback = 'agent' | 'voicemail' | 'hangup';
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

export const FALLBACK_OPTIONS: { value: TeamFallback; label: string }[] = [
  { value: 'agent', label: 'Pasa al agente' },
  { value: 'voicemail', label: 'Deja un mensaje y graba lo que dice quien llama' },
  { value: 'hangup', label: 'Dice el mensaje y corta' },
];

/** El mensaje que dice el número si no se escribe uno (el del worker). */
export const FALLBACK_MESSAGE_DEFAULTS: Record<'voicemail' | 'hangup', string> = {
  voicemail: 'Ahora no podemos atenderte. Dejá tu mensaje y te llamamos.',
  hangup: 'Ahora no podemos atenderte. Por favor, volvé a llamar más tarde.',
};

export const MESSAGE_MAX = 500;

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
  schedule: ScheduleDraft;
  team_fallback: TeamFallback;
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
    schedule: toDraft(n.schedule),
    team_fallback: n.team_fallback,
    team_fallback_message: n.team_fallback_message,
  };
}

/**
 * El PATCH de un número asignado. Con el agente, solo manda el modo y el agente (lo del equipo queda como
 * está); con el equipo, todo lo del equipo y el agente, que es el de respaldo.
 */
export function toAnsweringBody(v: AnsweringDraft): PhoneNumberUpdate {
  const base: PhoneNumberUpdate = {
    label: v.label.trim(),
    answer_mode: v.answer_mode,
    agent_id: v.agent_id || null,
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
    schedule: toSchedule(v.schedule),
    team_fallback: v.team_fallback,
    team_fallback_message: v.team_fallback_message.trim(),
  };
}

/** Las personas del número, en orden. */
export const numberMembers = (n: PhoneNumber) => n.members ?? [];

/** El equipo está elegido pero no tiene personas: las entrantes van al agente del número, o no se atienden. */
export const teamWithoutPeople = (n: PhoneNumber) =>
  n.answer_mode === 'team' && numberMembers(n).length === 0;
