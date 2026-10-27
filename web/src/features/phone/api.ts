// Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 13): llamar, volver a entrar, atender y
// rechazar, presencia y timbre, quién está disponible y el aviso de grabación del cliente.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import { BROWSER_TZ } from '@/features/calls/api';
import type { DirectCallIn, DirectCallSettings } from './types';

export const phoneKeys = {
  ringing: ['phone', 'ringing'] as const,
  teamPresence: (clientId?: string) => ['phone', 'team-presence', clientId ?? 'mine'] as const,
  settings: (clientId: string) => ['phone', 'settings', clientId] as const,
  // Bajo 'calls': se refrescan con el resto de las llamadas (callKeys.all).
  myCalls: (userId: string) => ['calls', 'phone', 'mine', userId] as const,
  recentCalls: ['calls', 'phone', 'recent'] as const,
};

// ---- Pedidos sueltos (los usa el CallProvider dentro de su flujo) ----

export function startDirectCall(body: DirectCallIn) {
  return unwrap(api.POST('/api/v1/direct-calls', { body }));
}

export function joinDirectCall(conversationId: string) {
  return unwrap(
    api.POST('/api/v1/direct-calls/{conversation_id}/join', {
      params: { path: { conversation_id: conversationId } },
    }),
  );
}

export function answerDirectCall(conversationId: string) {
  return unwrap(
    api.POST('/api/v1/direct-calls/{conversation_id}/answer', {
      params: { path: { conversation_id: conversationId } },
    }),
  );
}

export function declineDirectCall(conversationId: string) {
  return unwrap(
    api.POST('/api/v1/direct-calls/{conversation_id}/decline', {
      params: { path: { conversation_id: conversationId } },
    }),
  );
}

export function hangupCall(conversationId: string) {
  return unwrap(
    api.POST('/api/v1/calls/{conversation_id}/hangup', {
      params: { path: { conversation_id: conversationId } },
    }),
  );
}

export function putPresence(available: boolean) {
  return unwrap(api.PUT('/api/v1/me/presence', { body: { available } }));
}

// ---- Hooks ----

export function useStartDirectCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: startDirectCall,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['calls'] }),
  });
}

export function useJoinDirectCall() {
  return useMutation({ mutationFn: joinDirectCall });
}

export function useAnswerDirectCall() {
  return useMutation({ mutationFn: answerDirectCall });
}

export function useDeclineDirectCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: declineDirectCall,
    onSettled: () => void qc.invalidateQueries({ queryKey: phoneKeys.ringing }),
  });
}

/** Pulso de Disponible (cada ~20 s mientras está prendido) o `available: false` para apagarlo. */
export function useSetPresence() {
  return useMutation({ mutationFn: putPresence });
}

/** Entrantes que le suenan al usuario en el panel: cada 2 s mientras está Disponible y sin llamada. */
export function useRinging(enabled: boolean) {
  return useQuery({
    queryKey: phoneKeys.ringing,
    queryFn: () => unwrap(api.GET('/api/v1/me/ringing')),
    enabled,
    refetchInterval: enabled ? 2000 : false,
    refetchIntervalInBackground: true,
  });
}

/** Usuarios del cliente: Disponibles en el panel y ocupados. El admin indica el cliente. */
export function useTeamPresence(clientId?: string, enabled = true) {
  return useQuery({
    queryKey: phoneKeys.teamPresence(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/team/presence', { params: { query: { client_id: clientId } } })),
    enabled,
    refetchInterval: 20_000,
  });
}

export function useDirectCallSettings(clientId: string | null | undefined) {
  return useQuery({
    queryKey: phoneKeys.settings(clientId ?? ''),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/clients/{client_id}/direct-call-settings', {
          params: { path: { client_id: clientId! } },
        }),
      ),
    enabled: !!clientId,
  });
}

export function useUpdateDirectCallSettings(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DirectCallSettings) =>
      unwrap(
        api.PUT('/api/v1/clients/{client_id}/direct-call-settings', {
          params: { path: { client_id: clientId } },
          body,
        }),
      ),
    onSuccess: (data) => qc.setQueryData(phoneKeys.settings(clientId), data),
  });
}

/** Las llamadas que hizo o atendió el usuario (directas y entrantes del equipo). */
export function useMyCalls(userId: string, limit = 10) {
  return useQuery({
    queryKey: [...phoneKeys.myCalls(userId), limit],
    queryFn: () =>
      unwrap(api.GET('/api/v1/calls', { params: { query: { user_id: userId, limit, tz: BROWSER_TZ } } })),
    refetchInterval: 10_000,
  });
}

/**
 * Las últimas llamadas del cliente, para el historial de un contacto: la API no filtra por teléfono,
 * así que se buscan en las 200 más nuevas (agente y directas).
 */
export function useRecentCalls(enabled = true) {
  return useQuery({
    queryKey: phoneKeys.recentCalls,
    queryFn: () => unwrap(api.GET('/api/v1/calls', { params: { query: { limit: 200, tz: BROWSER_TZ } } })),
    enabled,
    staleTime: 15_000,
  });
}
