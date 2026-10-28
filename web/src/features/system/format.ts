import type { SystemSeries } from '@/api/types';
import { formatNumber } from '@/lib/format';

const EMPTY = '–';

/** Fracción a porcentaje: 0,253 → "25 %". */
export function pct(ratio: number | null | undefined, digits = 0): string {
  return ratio == null ? EMPTY : `${formatNumber(ratio * 100, digits)} %`;
}

/** Bytes en GB o MB (base 1024, como nvidia-smi y free). */
export function bytes(b: number | null | undefined): string {
  if (b == null) return EMPTY;
  const gb = b / 1024 ** 3;
  if (gb >= 1000) return `${formatNumber(gb / 1024, 2)} TB`;
  if (gb >= 1) return `${formatNumber(gb, 1)} GB`;
  return `${formatNumber(b / 1024 ** 2, 0)} MB`;
}

/** Bytes por segundo en Mbit/s. */
export function bitrate(bps: number | null | undefined): string {
  return bps == null ? EMPTY : `${formatNumber((bps * 8) / 1e6, 1)} Mbit/s`;
}

export function watts(w: number | null | undefined): string {
  return w == null ? EMPTY : `${formatNumber(w, 0)} W`;
}

export function celsius(c: number | null | undefined): string {
  return c == null ? EMPTY : `${formatNumber(c, 0)} °C`;
}

/** Segundos a "3 d 4 h" o "12 min". */
export function uptime(s: number | null | undefined): string {
  if (s == null) return EMPTY;
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  if (d) return `${d} d ${h} h`;
  if (h) return `${h} h ${Math.floor((s % 3600) / 60)} min`;
  return `${Math.max(1, Math.floor(s / 60))} min`;
}

/** Color de estado de un uso: verde hasta 70 %, amarillo hasta 90 %, rojo arriba (como el consumo). */
export function usageTone(ratio: number | null | undefined): 'green' | 'yellow' | 'red' {
  if (ratio == null || ratio < 0.7) return 'green';
  return ratio < 0.9 ? 'yellow' : 'red';
}

/** Hora de un punto de un gráfico: 14:05, o 28/10 14:05 si la ventana es de días. */
export function chartTime(epoch: number, withDay: boolean): string {
  const d = new Date(epoch * 1000);
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  return withDay ? `${d.getDate()}/${d.getMonth() + 1} ${hm}` : hm;
}

export function epochDateTime(epoch: number | null | undefined): string {
  if (epoch == null) return EMPTY;
  return chartTime(epoch, true);
}

export interface ChartLine {
  key: string;
  label: string;
  series: SystemSeries;
}

/** Filas de un LineChart a partir de varias series (una columna por línea, alineadas por tiempo). */
export function chartRows(lines: ChartLine[], withDay: boolean, scale = 1) {
  const byTime = new Map<number, Record<string, number | string | null>>();
  for (const l of lines) {
    for (const [t, v] of l.series.points) {
      if (t == null) continue;
      const row = byTime.get(t) ?? { time: chartTime(t, withDay) };
      row[l.key] = v == null ? null : v * scale;
      byTime.set(t, row);
    }
  }
  return [...byTime.entries()].sort((a, b) => a[0] - b[0]).map(([, r]) => r);
}
