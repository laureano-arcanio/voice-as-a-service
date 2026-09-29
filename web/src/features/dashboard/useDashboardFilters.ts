import { useSearchParams } from 'react-router';
import { lastDays } from '@/lib/format';
import type { CallFilters } from '@/features/calls/api';

export type RangePreset = '7' | '30' | 'custom';

export interface DashboardFilters {
  client: string | null;
  agent: string | null;
  range: RangePreset;
  from: string | null;
  to: string | null;
  status: string | null;
  mode: string | null;
  page: number;
}

/** Filtros del dashboard en la URL (se pueden compartir y sobreviven al refresco). */
export function useDashboardFilters() {
  const [params, setParams] = useSearchParams();
  const range = (
    ['7', '30', 'custom'].includes(params.get('range') ?? '') ? params.get('range') : '30'
  ) as RangePreset;
  const filters: DashboardFilters = {
    client: params.get('client'),
    agent: params.get('agent'),
    range,
    from: params.get('from'),
    to: params.get('to'),
    status: params.get('status'),
    mode: params.get('mode'),
    page: Math.max(1, Number(params.get('page')) || 1),
  };

  const update = (patch: Partial<DashboardFilters>) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(patch)) {
          if (v == null || v === '' || (k === 'range' && v === '30') || (k === 'page' && v === 1))
            next.delete(k);
          else next.set(k, String(v));
        }
        // Cambiar un filtro vuelve a la primera pagina.
        if (!('page' in patch)) next.delete('page');
        return next;
      },
      { replace: true },
    );
  };

  // Rango efectivo: los presets son relativos a hoy; el personalizado necesita las dos fechas.
  const dates =
    range === 'custom'
      ? filters.from && filters.to
        ? { from: filters.from, to: filters.to }
        : lastDays(30)
      : lastDays(Number(range));

  const apiFilters: CallFilters = {
    client_id: filters.client ?? undefined,
    agent_id: filters.agent ?? undefined,
    date_from: dates.from,
    date_to: dates.to,
  };

  return { filters, update, dates, apiFilters };
}
