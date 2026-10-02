import type { Daily, Stats } from '@/api/types';
import { formatDayLabel, formatDuration, formatNumber, formatSeconds } from '@/lib/format';

export interface Tile {
  label: string;
  value: string;
  /** Dato de apoyo al lado del numero (porcentaje, promedio). */
  sub?: string;
  /** Color de estado, solo si el numero indica un problema. */
  tone?: 'red' | 'yellow';
}

/** Metricas del periodo. El cliente no ve vocabulario interno (workflow, latencia). */
export function statTiles(s: Stats, isAdmin: boolean): Tile[] {
  const pct = (p: number) => (s.total ? `${formatNumber(p)}%` : undefined);
  return [
    {
      label: 'Conversaciones',
      value: String(s.total),
      sub: s.whatsapp ? `${s.whatsapp} por WhatsApp` : undefined,
    },
    { label: 'Llamadas finalizadas', value: String(s.finished) },
    {
      label: isAdmin ? 'Workflow completo' : 'Completas',
      value: String(s.completed),
      sub: pct(s.completed_pct),
    },
    { label: 'Objetivo cumplido', value: String(s.goal), sub: pct(s.goal_pct) },
    { label: 'Fallidas', value: String(s.failed), tone: s.failed ? 'red' : undefined },
    { label: 'Rechazadas', value: String(s.rejected), tone: s.rejected ? 'yellow' : undefined },
    {
      label: 'Minutos',
      value: formatNumber(s.total_minutes),
      sub: s.finished ? `${formatDuration(s.avg_duration)} por llamada` : undefined,
    },
    { label: isAdmin ? 'Latencia por turno' : 'Tiempo de respuesta', value: formatSeconds(s.latency_avg) },
  ];
}

export function dailyRows(d: Daily) {
  return d.labels.map((label, i) => ({
    day: formatDayLabel(label),
    total: d.totals[i] ?? 0,
    completed: d.completed_pct[i] ?? null,
    goal: d.goal_pct[i] ?? null,
  }));
}
