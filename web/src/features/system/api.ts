import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';

export type SystemWindow = '1h' | '6h' | '24h' | '7d';

export const systemKeys = {
  now: ['system', 'now'] as const,
  history: (w: SystemWindow) => ['system', 'history', w] as const,
  events: (w: SystemWindow) => ['system', 'events', w] as const,
  peaks: ['system', 'peaks'] as const,
};

/** Foto actual; se refresca cada 10 s (Prometheus raspa cada 5 s). */
export function useSystemNow() {
  return useQuery({
    queryKey: systemKeys.now,
    queryFn: () => unwrap(api.GET('/api/v1/system/now')),
    refetchInterval: 10_000,
    placeholderData: keepPreviousData,
  });
}

export function useSystemHistory(window: SystemWindow) {
  return useQuery({
    queryKey: systemKeys.history(window),
    queryFn: () => unwrap(api.GET('/api/v1/system/history', { params: { query: { window } } })),
    refetchInterval: 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useSystemEvents(window: SystemWindow) {
  return useQuery({
    queryKey: systemKeys.events(window),
    queryFn: () => unwrap(api.GET('/api/v1/system/events', { params: { query: { window } } })),
    refetchInterval: 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useSystemPeaks() {
  return useQuery({
    queryKey: systemKeys.peaks,
    queryFn: () => unwrap(api.GET('/api/v1/system/peaks', { params: { query: { days: 7 } } })),
    staleTime: 5 * 60_000,
  });
}
