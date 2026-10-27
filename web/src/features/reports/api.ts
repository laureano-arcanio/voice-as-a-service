import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import { BROWSER_TZ } from '@/features/calls/api';
import type { ReportByName, ReportName, ReportQuery } from './types';

// Un solo fetch para los 8 reportes (el path lleva el nombre): se piden por el mismo cliente (cookie y
// manejo del 401), sin el tipado del path. Las respuestas, con los tipos de types.ts (iguales a los del schema).
type LooseGet = (
  path: string,
  init: { params: { query: Record<string, string | boolean | undefined> } },
) => Promise<{ data?: unknown; error?: unknown; response: Response }>;

export const reportKeys = {
  all: ['reports'] as const,
  report: (name: ReportName, q: ReportQuery) => ['reports', name, q] as const,
};

export function fetchReport<N extends ReportName>(name: N, q: ReportQuery): Promise<ReportByName[N]> {
  const get = api.GET as unknown as LooseGet;
  return unwrap(get(`/api/v1/reports/${name}`, { params: { query: { ...q, tz: BROWSER_TZ } } })) as Promise<
    ReportByName[N]
  >;
}

/** Un reporte con los filtros de la pantalla. `enabled` en false (plan sin la funcion) no pide nada. */
export function useReport<N extends ReportName>(name: N, q: ReportQuery, enabled = true) {
  return useQuery({
    queryKey: reportKeys.report(name, q),
    queryFn: () => fetchReport(name, q),
    enabled,
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });
}
