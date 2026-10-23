import type { HandoffSchedule } from '@/api/types';

// Horario de un area, como lo guarda la API: franjas "HH:MM" por dia, dias cerrados y zona.
// Sin horario (null) el area atiende siempre.

export const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type Day = (typeof DAYS)[number];

export const DAY_LABEL: Record<Day, string> = {
  mon: 'Lunes',
  tue: 'Martes',
  wed: 'Miércoles',
  thu: 'Jueves',
  fri: 'Viernes',
  sat: 'Sábado',
  sun: 'Domingo',
};

export const DEFAULT_TZ = 'America/Argentina/Buenos_Aires';

export type Range = [string, string];
export type Week = Record<Day, Range[]>;

export interface ScheduleDraft {
  always: boolean;
  tz: string;
  week: Week;
  closed: string[];
}

/** Lunes a viernes de 9 a 18: el punto de partida al dejar de atender siempre. */
export function officeHours(): Week {
  return Object.fromEntries(
    DAYS.map((d) => [d, d === 'sat' || d === 'sun' ? [] : [['09:00', '18:00']]]),
  ) as Week;
}

/** El horario como llega de la API: las franjas pueden venir tipadas como listas sueltas. */
type ScheduleIn = { tz?: string; week?: Record<string, string[][]>; closed?: string[] } | null | undefined;

export function toDraft(schedule: ScheduleIn): ScheduleDraft {
  if (!schedule) return { always: true, tz: DEFAULT_TZ, week: officeHours(), closed: [] };
  const week = Object.fromEntries(
    DAYS.map((d) => [d, (schedule.week?.[d] ?? []).map(([a, b]) => [a ?? '', b ?? ''] as Range)]),
  ) as Week;
  return { always: false, tz: schedule.tz || DEFAULT_TZ, week, closed: [...(schedule.closed ?? [])] };
}

export function toSchedule(draft: ScheduleDraft): HandoffSchedule | null {
  if (draft.always) return null;
  const week: Record<string, [string, string][]> = {};
  for (const d of DAYS) {
    const ranges = draft.week[d].filter(([a, b]) => a || b);
    if (ranges.length) week[d] = [...ranges].sort((x, y) => x[0].localeCompare(y[0]));
  }
  return { tz: draft.tz, week, closed: [...draft.closed].sort() };
}

const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;

/** El primer problema del horario (como lo diria la API), o null. */
export function scheduleError(draft: ScheduleDraft): string | null {
  if (draft.always) return null;
  for (const d of DAYS) {
    const day = DAY_LABEL[d].toLowerCase();
    const ranges = draft.week[d].filter(([a, b]) => a || b);
    for (const [a, b] of ranges) {
      if (!HHMM.test(a) || !HHMM.test(b)) return `Completá la franja del ${day} (desde y hasta).`;
      if (a >= b) return `El ${day}: ${a} tiene que ser antes que ${b}.`;
    }
    const sorted = [...ranges].sort((x, y) => x[0].localeCompare(y[0]));
    for (let i = 1; i < sorted.length; i++)
      if (sorted[i][0] < sorted[i - 1][1]) return `El ${day} hay franjas superpuestas.`;
  }
  if (DAYS.every((d) => draft.week[d].length === 0))
    return 'Cargá al menos una franja, o elegí que atiende siempre.';
  return null;
}

/** El horario de la API ("los lunes de 09:00 a 18:00") con mayúscula inicial. */
export function scheduleLabel(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}
