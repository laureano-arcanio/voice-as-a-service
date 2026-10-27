import { useSearchParams } from 'react-router';
import { lastDays, toIsoDate } from '@/lib/format';
import type { Channel, ReportQuery } from './types';

// Mismos nombres que los filtros de Inicio (client, agent, range, from, to): el link entre las dos
// pantallas los conserva.
export type ReportRange = '7' | '30' | '90' | 'month' | 'prev_month' | 'custom';

const RANGES: ReportRange[] = ['7', '30', '90', 'month', 'prev_month', 'custom'];
const CHANNELS: Channel[] = ['voice', 'whatsapp', 'web'];

export interface ReportFilters {
  client: string | null;
  agent: string | null;
  channel: Channel | null;
  range: ReportRange;
  from: string | null;
  to: string | null;
  tests: boolean;
  tab: string | null;
}

/** Dias del preset, relativos a hoy. */
export function rangeDates(
  range: ReportRange,
  from: string | null,
  to: string | null,
  today = new Date(),
): { from: string; to: string } {
  switch (range) {
    case 'custom':
      return from && to ? { from, to } : lastDays(30, today);
    case 'month':
      return { from: toIsoDate(new Date(today.getFullYear(), today.getMonth(), 1)), to: toIsoDate(today) };
    case 'prev_month':
      return {
        from: toIsoDate(new Date(today.getFullYear(), today.getMonth() - 1, 1)),
        to: toIsoDate(new Date(today.getFullYear(), today.getMonth(), 0)),
      };
    default:
      return lastDays(Number(range), today);
  }
}

/** Filtros de Reportes en la URL (se pueden compartir y sobreviven al refresco). */
export function useReportFilters() {
  const [params, setParams] = useSearchParams();
  const rawRange = params.get('range') as ReportRange | null;
  const rawChannel = params.get('channel') as Channel | null;
  const filters: ReportFilters = {
    client: params.get('client'),
    agent: params.get('agent'),
    channel: rawChannel && CHANNELS.includes(rawChannel) ? rawChannel : null,
    range: rawRange && RANGES.includes(rawRange) ? rawRange : '30',
    from: params.get('from'),
    to: params.get('to'),
    tests: params.get('tests') === '1',
    tab: params.get('tab'),
  };

  const update = (patch: Partial<ReportFilters>) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(patch)) {
          if (v == null || v === '' || v === false || (k === 'range' && v === '30')) next.delete(k);
          else next.set(k, v === true ? '1' : String(v));
        }
        return next;
      },
      { replace: true },
    );
  };

  const dates = rangeDates(filters.range, filters.from, filters.to);
  const query: ReportQuery = {
    client_id: filters.client ?? undefined,
    agent_id: filters.agent ?? undefined,
    channel: filters.channel ?? undefined,
    date_from: dates.from,
    date_to: dates.to,
    include_tests: filters.tests || undefined,
  };
  return { filters, update, dates, query };
}
