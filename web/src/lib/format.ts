// Formatos para la UI: es-AR, hora local. La API da ISO con zona (+00:00 o Z).

const EMPTY = '–';

/** Segundos a m:ss (o h:mm:ss); 0 o null → guion, como el dashboard viejo. */
export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds < 0 || !Number.isFinite(seconds)) return EMPTY;
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`;
}

/** Tiempo de reproduccion m:ss (0:00 si no hay duracion). */
export function formatClock(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
}

function parse(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Fecha y hora local: 29/9/2026 14:05. */
export function formatDateTime(iso: string | null | undefined): string {
  const d = parse(iso);
  if (!d) return EMPTY;
  return `${d.toLocaleDateString('es-AR')} ${d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })}`;
}

/** Fecha y hora local con segundos. */
export function formatDateTimeLong(iso: string | null | undefined): string {
  const d = parse(iso);
  return d ? d.toLocaleString('es-AR', { hourCycle: 'h23' }) : EMPTY;
}

export function formatDate(iso: string | null | undefined): string {
  const d = parse(iso);
  return d ? d.toLocaleDateString('es-AR') : EMPTY;
}

/** Numero con coma decimal: 1,5. */
export function formatNumber(x: number | null | undefined, digits = 1): string {
  if (x == null || !Number.isFinite(x)) return EMPTY;
  return x.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: digits });
}

/** Segundos con 2 decimales: 1,23 s. */
export function formatSeconds(x: number | null | undefined): string {
  if (x == null || !Number.isFinite(x)) return EMPTY;
  return `${x.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} s`;
}

/** Fecha local YYYY-MM-DD (para los filtros de la API, sin pasar por UTC). */
export function toIsoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** YYYY-MM-DD a Date local (mediodia no hace falta: se usa a las 0 h locales). */
export function fromIsoDate(s: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

/** Rango de los ultimos `days` dias, hoy incluido. */
export function lastDays(days: number, today = new Date()): { from: string; to: string } {
  const from = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (days - 1));
  return { from: toIsoDate(from), to: toIsoDate(today) };
}

/** Mes YYYY-MM de una fecha local. */
export function toMonth(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** "septiembre de 2026". */
export function formatMonth(month: string): string {
  const [y, m] = month.split('-').map(Number);
  if (!y || !m) return month;
  return new Date(y, m - 1, 1).toLocaleDateString('es-AR', { month: 'long', year: 'numeric' });
}

/** Ultimos `n` meses (el actual primero). */
export function recentMonths(n: number, today = new Date()): string[] {
  return Array.from({ length: n }, (_, i) => toMonth(new Date(today.getFullYear(), today.getMonth() - i, 1)));
}

/** Etiqueta dd/mm de un dia YYYY-MM-DD (eje del grafico). */
export function formatDayLabel(isoDay: string): string {
  const d = fromIsoDate(isoDay);
  return d ? d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' }) : isoDay;
}

/** Slug como el del server: minusculas, numeros y _, sin acentos, hasta 64. */
export function slugify(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 64);
}

export const SLUG_RE = /^[a-z0-9][a-z0-9_]{0,63}$/;
export const E164_RE = /^\+\d{8,15}$/;

/** Valor de un dato capturado para mostrar. */
export function formatValue(v: unknown): string {
  if (v == null) return '';
  if (v === true) return 'Sí';
  if (v === false) return 'No';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

/** Salida del LLM tal cual; si es JSON, indentado. */
export function prettyJson(raw: unknown): string {
  if (typeof raw !== 'string') return JSON.stringify(raw, null, 2) ?? '';
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

/** Porcentaje usado (0 si no hay limite o es 0). */
export function usagePercent(used: number, limit: number | null | undefined): number | null {
  if (limit == null) return null;
  if (limit <= 0) return used > 0 ? 100 : 0;
  return (used / limit) * 100;
}

/** Color de una barra de consumo por % usado. */
export function usageColor(pct: number | null): string {
  if (pct == null) return 'gray';
  if (pct >= 90) return 'red';
  if (pct >= 70) return 'yellow';
  return 'green';
}

/** Periodo [inicio, fin) como fechas locales inclusivas: "1/9/2026 al 30/9/2026". */
export function formatPeriod(startIso: string, endIso: string): string {
  const end = parse(endIso);
  const last = end ? new Date(end.getTime() - 1).toISOString() : null;
  return `${formatDate(startIso)} al ${formatDate(last)}`;
}

/** Limite de un tier: null = ilimitado. */
export function formatLimit(v: number | null | undefined, unit = ''): string {
  return v == null ? 'Ilimitado' : `${formatNumber(v, 0)}${unit}`;
}
