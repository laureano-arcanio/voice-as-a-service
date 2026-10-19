// Fecha y hora de inicio y fin de una campaña: se escriben en la hora de la campaña (BILLING_TIMEZONE,
// la misma de su horario permitido) y viajan como instante UTC.

export const DEFAULT_TZ = 'America/Argentina/Buenos_Aires';

/** Minutos que la zona `tz` esta adelantada de UTC en el instante `ms`. */
function offsetMinutes(ms: number, tz: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(new Date(ms));
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value);
  const asUtc = Date.UTC(
    get('year'),
    get('month') - 1,
    get('day'),
    get('hour'),
    get('minute'),
    get('second'),
  );
  return Math.round((asUtc - Math.floor(ms / 1000) * 1000) / 60000);
}

/** "2026-10-20T09:30" (hora de `tz`) a ISO UTC. Vacio o invalido: null. */
export function localToIso(local: string, tz = DEFAULT_TZ): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(local);
  if (!m) return null;
  const [y, mo, d, h, mi] = m.slice(1).map(Number);
  const guess = Date.UTC(y, mo - 1, d, h, mi);
  const ms = guess - offsetMinutes(guess, tz) * 60000;
  return new Date(ms).toISOString();
}

/** ISO UTC a "2026-10-20T09:30" en la hora de `tz`, para un input datetime-local. */
export function isoToLocal(iso: string | null | undefined, tz = DEFAULT_TZ): string {
  if (!iso) return '';
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return '';
  return new Date(ms + offsetMinutes(ms, tz) * 60000).toISOString().slice(0, 16);
}
