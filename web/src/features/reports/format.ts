import { createContext } from 'react';
import { formatNumber } from '@/lib/format';

/** Periodo y pestaña de la pantalla: para el nombre de los CSV. */
export const ReportContext = createContext<{ tab: string; from: string; to: string }>({
  tab: 'reportes',
  from: '',
  to: '',
});

export interface Kpi {
  label: string;
  value: string;
  sub?: string;
  /** Variacion contra el periodo anterior, ya en texto ("+12 %", "-3,1 pp"); null si no hay base. */
  delta?: { text: string; up: boolean } | null;
  tone?: 'red' | 'yellow';
}

/** Variacion porcentual de una cantidad (null si el periodo anterior es 0). */
export function deltaPct(cur: number | null | undefined, prev: number | null | undefined): Kpi['delta'] {
  if (cur == null || prev == null || !prev) return null;
  const d = ((cur - prev) / prev) * 100;
  return { text: `${d >= 0 ? '+' : ''}${formatNumber(d, 0)} %`, up: d >= 0 };
}

/** Variacion de un porcentaje, en puntos. */
export function deltaPoints(cur: number | null | undefined, prev: number | null | undefined): Kpi['delta'] {
  if (cur == null || prev == null) return null;
  const d = cur - prev;
  return { text: `${d >= 0 ? '+' : ''}${formatNumber(d)} pp`, up: d >= 0 };
}

export const pct = (v: number | null | undefined) => (v == null ? '–' : `${formatNumber(v)}%`);
