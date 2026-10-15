import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { LlmConnectionIn, LlmConnectionPatch } from '@/api/types';

export const llmKeys = {
  list: (clientId: string) => ['llm-connections', clientId] as const,
  models: (clientId: string, connectionId: string) => ['llm-connections', clientId, connectionId, 'models'] as const,
};

const BASE = '/api/v1/clients/{client_id}/llm-connections';

export function useLlmConnections(clientId: string | undefined) {
  return useQuery({
    queryKey: llmKeys.list(clientId ?? ''),
    queryFn: () => unwrap(api.GET(BASE, { params: { path: { client_id: clientId! } } })),
    enabled: !!clientId,
  });
}

export function useCreateLlmConnection(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LlmConnectionIn) =>
      unwrap(api.POST(BASE, { params: { path: { client_id: clientId } }, body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: llmKeys.list(clientId) }),
  });
}

export function useUpdateLlmConnection(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: LlmConnectionPatch }) =>
      unwrap(
        api.PATCH(`${BASE}/{connection_id}`, {
          params: { path: { client_id: clientId, connection_id: id } },
          body,
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: llmKeys.list(clientId) }),
  });
}

/** Pedido real al proveedor: detecta el modo de JSON y guarda el resultado en la conexion. */
export function useTestLlmConnection(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, model }: { id: string; model?: string }) =>
      unwrap(
        api.POST(`${BASE}/{connection_id}/test`, {
          params: { path: { client_id: clientId, connection_id: id } },
          body: { model: model || null },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: llmKeys.list(clientId) }),
  });
}

export function useDeleteLlmConnection(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE(`${BASE}/{connection_id}`, {
          params: { path: { client_id: clientId, connection_id: id } },
        }),
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: llmKeys.list(clientId) });
      void qc.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

/** Modelos que lista el proveedor. Solo cuando se pide (un pedido real a su API). */
export function useLlmModels(clientId: string | undefined, connectionId: string | null) {
  return useQuery({
    queryKey: llmKeys.models(clientId ?? '', connectionId ?? ''),
    queryFn: () =>
      unwrap(
        api.GET(`${BASE}/{connection_id}/models`, {
          params: { path: { client_id: clientId!, connection_id: connectionId! } },
        }),
      ),
    enabled: !!clientId && !!connectionId,
    staleTime: 5 * 60_000,
    retry: false,
  });
}
