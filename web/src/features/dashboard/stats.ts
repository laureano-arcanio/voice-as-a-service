import type { Daily, Stats } from '@/api/types';
import { formatDayLabel, formatDuration, formatNumber, formatSeconds } from '@/lib/format';

export interface Tile {
  label: string;
  value: string;
  tone?: 'ok' | 'bad' | 'warn';
}

export function statTiles(s: Stats): Tile[] {
  const withPct = (n: number, pct: number) => (s.total ? `${n} · ${formatNumber(pct)}%` : String(n));
  return [
    { label: 'Conversaciones', value: String(s.total) },
    { label: 'Llamadas finalizadas', value: String(s.finished) },
    { label: 'Workflow completo', value: withPct(s.completed, s.completed_pct), tone: 'ok' },
    { label: 'Objetivo cumplido', value: withPct(s.goal, s.goal_pct), tone: 'ok' },
    { label: 'Fallidas', value: String(s.failed), tone: 'bad' },
    { label: 'Rechazadas', value: String(s.rejected), tone: 'warn' },
    {
      label: 'Minutos (prom. por llamada)',
      value: `${formatNumber(s.total_minutes)}${s.finished ? ` (${formatDuration(s.avg_duration)})` : ''}`,
    },
    { label: 'Latencia por turno', value: formatSeconds(s.latency_avg) },
  ];
}

export function dailyRows(d: Daily) {
  return d.labels.map((label, i) => ({
    day: formatDayLabel(label),
    Conversaciones: d.totals[i] ?? 0,
    '% workflow completo': d.completed_pct[i] ?? null,
    '% objetivo cumplido': d.goal_pct[i] ?? null,
  }));
}
