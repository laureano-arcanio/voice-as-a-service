// Ayudas de las listas del teléfono: dirección de una llamada, agrupado por día y letras de la agenda.
import type { CallSummary } from '@/api/types';

/** Saliente (la hizo el usuario) o entrante (la atendió); `missed`: la saliente que no atendieron. */
export function callDirection(c: CallSummary): { kind: 'out' | 'in'; missed: boolean } {
  const kind = c.mode === 'directa' || c.mode === 'saliente' ? 'out' : 'in';
  const missed = c.status === 'fallida' || c.status === 'cancelada' || c.status === 'rechazada';
  return { kind, missed };
}

const DAY = new Intl.DateTimeFormat('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
const TIME = new Intl.DateTimeFormat('es-AR', { hour: '2-digit', minute: '2-digit' });

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

/** "Hoy", "Ayer" o la fecha, para agrupar las recientes. */
export function dayLabel(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return '';
  const d = new Date(iso);
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (dayKey(d) === dayKey(now)) return 'Hoy';
  if (dayKey(d) === dayKey(yesterday)) return 'Ayer';
  const label = DAY.format(d);
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function timeLabel(iso: string | null | undefined): string {
  return iso ? TIME.format(new Date(iso)) : '';
}

/** Las llamadas agrupadas por día, en el orden en que vienen (de la más nueva a la más vieja). */
export function groupByDay(items: CallSummary[]): { label: string; items: CallSummary[] }[] {
  const groups: { label: string; items: CallSummary[] }[] = [];
  for (const c of items) {
    const label = dayLabel(c.created_at);
    const last = groups.at(-1);
    if (last && last.label === label) last.items.push(c);
    else groups.push({ label, items: [c] });
  }
  return groups;
}

/** La letra de cada contacto y si abre una sección nueva (la agenda, ordenada por nombre). */
export function withLetters<T>(items: T[], label: (item: T) => string): { item: T; head: string | null }[] {
  return items.map((item, i) => {
    const letter = letterOf(label(item));
    const prev = i > 0 ? letterOf(label(items[i - 1]!)) : null;
    return { item, head: letter !== prev ? letter : null };
  });
}

function letterOf(label: string): string {
  const first = (label[0] ?? '').toUpperCase();
  return /\p{L}/u.test(first) ? first : '#';
}
