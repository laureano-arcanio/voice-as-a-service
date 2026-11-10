import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import { isLiveStatus } from '@/lib/labels';
import { reportKeys } from '@/features/reports/api';
import type { CallDetail, CallIn } from './types';

export interface CallFilters {
  client_id?: string;
  agent_id?: string;
  campaign_id?: string;
  date_from?: string;
  date_to?: string;
}

export interface CallListParams extends CallFilters {
  status?: string[];
  mode?: string[];
  /** true: solo las llamadas de prueba de la landing; false: sin ellas. */
  landing?: boolean;
  /** Llamadas directas: las entrantes que atendió el agente o el equipo, y las de ese usuario. */
  answered_by?: 'agent' | 'team';
  user_id?: string;
  limit: number;
  offset: number;
}

/** Zona del navegador: los dias de los filtros y del grafico son dias locales. */
export const BROWSER_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

export const callKeys = {
  all: ['calls'] as const,
  list: (p: CallListParams) => ['calls', 'list', p] as const,
  detail: (id: string) => ['calls', 'detail', id] as const,
};

export function useCalls(p: CallListParams) {
  return useQuery({
    queryKey: callKeys.list(p),
    queryFn: () => unwrap(api.GET('/api/v1/calls', { params: { query: { ...p, tz: BROWSER_TZ } } })),
    refetchInterval: 2000,
    placeholderData: keepPreviousData,
  });
}

/** URL del WAV de ese mensaje (agent.record_audio): la cookie de sesion viaja sola, mismo origen. */
export function recordingUrl(conversationId: string, n: number): string {
  return `/api/v1/calls/${conversationId}/recordings/${n}`;
}

export function isCallLive(c: CallDetail | undefined): boolean {
  if (!c || c.whatsapp?.closed_at) return false;
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
      void qc.invalidateQueries({ queryKey: reportKeys.all });
      void qc.invalidateQueries({ queryKey: ['clients'] });
    },
  });
}

/** Borra conversaciones (solo admin): la llamada con su consumo del mes, el hilo y los
 * mensajes de WhatsApp y las grabaciones. Los ids inexistentes se ignoran. */
export function useDeleteConversations() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => unwrap(api.POST('/api/v1/calls/bulk-delete', { body: { ids } })),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: callKeys.all });
      void qc.invalidateQueries({ queryKey: reportKeys.all });
      void qc.invalidateQueries({ queryKey: ['clients'] });
    },
  });
}

/** Corta una llamada en curso (cuelga a la otra punta). */
export function useHangUp(conversationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/v1/calls/{conversation_id}/hangup', {
          params: { path: { conversation_id: conversationId } },
        }),
      ),
    onSettled: () => void qc.invalidateQueries({ queryKey: callKeys.all }),
  });
}

/** Cierra un chat de WhatsApp: el proximo mensaje del contacto empieza otra conversacion. */
export function useCloseWhatsApp(conversationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/api/v1/whatsapp/threads/{conversation_id}/close', {
          params: { path: { conversation_id: conversationId } },
        }),
      ),
    onSettled: () => void qc.invalidateQueries({ queryKey: callKeys.all }),
  });
}

// ---- Conversacion por texto (sin llamada) ----

/** `callerPhone` y `workflows` son solo de las pruebas del panel (la API key recibe 403 `panel_test_only`). */
export function useStartConversation() {
  return useMutation({
    mutationFn: ({ agentId, callerPhone }: { agentId: string; callerPhone?: string }) =>
      unwrap(
        api.POST('/api/v1/conversations', {
          body: { agent_id: agentId, ...(callerPhone ? { caller_phone: callerPhone } : {}), workflows: true },
        }),
      ),
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

// ---- Llamada de prueba por el navegador ----

/** POST /calls sin teléfono (modo prueba) y las credenciales para entrar. Desde el panel de prueba lleva el
 * número simulado y `workflows`; Inicio no manda ninguno. */
export async function startBrowserCall(
  agentId: string,
  opts: { callerPhone?: string; workflows?: boolean } = {},
) {
  const body: CallIn = { agent_id: agentId };
  if (opts.callerPhone) body.caller_phone = opts.callerPhone;
  if (opts.workflows) body.workflows = true;
  const started = await unwrap(api.POST('/api/v1/calls', { body }));
  const creds = await unwrap(
    api.POST('/api/v1/calls/{conversation_id}/join', {
      params: { path: { conversation_id: started.conversation_id } },
    }),
  );
  return { conversationId: started.conversation_id, ...creds };
}

export async function hangUpCall(conversationId: string) {
  await api.POST('/api/v1/calls/{conversation_id}/hangup', {
    params: { path: { conversation_id: conversationId } },
  });
}
