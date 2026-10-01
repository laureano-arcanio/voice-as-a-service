import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import { isLiveStatus, LIVE_STATUSES } from '@/lib/labels';
import type { CallDetail, CallIn } from './types';

export interface CallFilters {
  client_id?: string;
  agent_id?: string;
  date_from?: string;
  date_to?: string;
}

export interface CallListParams extends CallFilters {
  status?: string[];
  mode?: string;
  limit: number;
  offset: number;
}

/** Zona del navegador: los dias de los filtros y del grafico son dias locales. */
export const BROWSER_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

export const callKeys = {
  all: ['calls'] as const,
  list: (p: CallListParams) => ['calls', 'list', p] as const,
  live: (p: CallFilters) => ['calls', 'live', p] as const,
  detail: (id: string) => ['calls', 'detail', id] as const,
  stats: (p: CallFilters) => ['stats', p] as const,
  daily: (p: CallFilters) => ['stats', 'daily', p] as const,
};

export function useCalls(p: CallListParams) {
  return useQuery({
    queryKey: callKeys.list(p),
    queryFn: () => unwrap(api.GET('/api/v1/calls', { params: { query: { ...p, tz: BROWSER_TZ } } })),
    refetchInterval: 2000,
    placeholderData: keepPreviousData,
  });
}

/** Llamadas en curso (pendiente, sonando, en_curso) en un pedido, refresco cada 2 s. */
export function useLiveCalls(p: CallFilters) {
  return useQuery({
    queryKey: callKeys.live(p),
    queryFn: async () => {
      const page = await unwrap(
        api.GET('/api/v1/calls', {
          params: {
            query: {
              client_id: p.client_id,
              agent_id: p.agent_id,
              status: LIVE_STATUSES,
              limit: 50,
              tz: BROWSER_TZ,
            },
          },
        }),
      );
      return page.items;
    },
    refetchInterval: 2000,
  });
}

export function useStats(p: CallFilters) {
  return useQuery({
    queryKey: callKeys.stats(p),
    queryFn: () => unwrap(api.GET('/api/v1/stats', { params: { query: { ...p, tz: BROWSER_TZ } } })),
    refetchInterval: 5000,
    placeholderData: keepPreviousData,
  });
}

export function useDailyStats(p: CallFilters & { date_from: string; date_to: string }) {
  return useQuery({
    queryKey: callKeys.daily(p),
    queryFn: () => unwrap(api.GET('/api/v1/stats/daily', { params: { query: { ...p, tz: BROWSER_TZ } } })),
    refetchInterval: 30_000,
    placeholderData: keepPreviousData,
  });
}

export function isCallLive(c: CallDetail | undefined): boolean {
  if (!c) return false;
  return c.call ? isLiveStatus(c.call.status) : c.workflow_status === 'active';
}

/** Refresco del detalle: 1 s en una llamada en curso; 3 s en un chat de WhatsApp activo
 * (los mensajes llegan de a uno y el cliente puede volver a escribir horas despues). */
export function detailRefetchMs(c: CallDetail | undefined): number | false {
  if (!isCallLive(c)) return false;
  return c?.whatsapp ? 3000 : 1000;
}

export function useCallDetail(id: string | undefined) {
  return useQuery({
    queryKey: callKeys.detail(id ?? ''),
    queryFn: () =>
      unwrap(api.GET('/api/v1/calls/{conversation_id}', { params: { path: { conversation_id: id! } } })),
    enabled: !!id,
    refetchInterval: (q) => detailRefetchMs(q.state.data),
  });
}

export function useStartCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CallIn) => unwrap(api.POST('/api/v1/calls', { body })),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: callKeys.all });
      void qc.invalidateQueries({ queryKey: ['stats'] });
      void qc.invalidateQueries({ queryKey: ['clients'] });
    },
  });
}

// ---- Conversacion por texto (sin llamada) ----

export function useStartConversation() {
  return useMutation({
    mutationFn: (agentId: string) =>
      unwrap(api.POST('/api/v1/conversations', { body: { agent_id: agentId } })),
  });
}

export function useSendTurn() {
  return useMutation({
    mutationFn: ({ conversationId, message }: { conversationId: string; message: string }) =>
      unwrap(
        api.POST('/api/v1/conversations/{conversation_id}/turns', {
          params: { path: { conversation_id: conversationId } },
          body: { message },
        }),
      ),
  });
}
