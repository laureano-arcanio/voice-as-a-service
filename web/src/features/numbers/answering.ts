import type { PhoneNumber, PhoneNumberUpdate } from '@/api/types';
import { type ScheduleDraft, toDraft, toSchedule } from '@/features/team/schedule';

// Quién atiende las entrantes de un número (docs/features/EQUIPO_TELEFONIA.md): el equipo (las
// personas del número, en orden) o el agente.

export type AnswerMode = 'team' | 'agent';
export type RingFirst = 'phone' | 'panel';
export type TeamFallback = 'agent' | 'voicemail' | 'hangup';

export const RING_FIRST_OPTIONS: { value: RingFirst; label: string }[] = [
  { value: 'phone', label: 'En su celular' },
  { value: 'panel', label: 'En el panel' },
];

export const RING_FIRST_HELP: Record<RingFirst, string> = {
  phone:
    'Llama al celular de cada persona, en orden. Si ninguna atiende, suena en el panel a las que estén Disponibles.',
  panel:
    'Suena en el panel a las personas Disponibles, a todas a la vez. Si nadie atiende, llama a sus celulares en orden.',
};

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
  ring_first: RingFirst;
  ring_seconds: number | string;
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
    ring_first: n.ring_first,
    ring_seconds: n.ring_seconds,
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
    ring_first: v.ring_first,
    ring_seconds: Number(v.ring_seconds),
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
