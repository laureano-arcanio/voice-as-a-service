import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { LlmConnectionIn, LlmConnectionPatch } from '@/api/types';

export const llmKeys = {
  list: (clientId: string) => ['llm-connections', clientId] as const,
  models: (clientId: string, connectionId: string) =>
    ['llm-connections', clientId, connectionId, 'models'] as const,
  params: ['llm-params'] as const,
};

/** Catalogo de parametros de generacion por proveedor y defaults del LLM local (app/llm/params.py). */
export function useLlmParams() {
  return useQuery({
    queryKey: llmKeys.params,
    queryFn: () => unwrap(api.GET('/api/v1/llm/params', {})),
    staleTime: 10 * 60_000,
    retry: false,
  });
}

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

/** Pedido real al proveedor: detecta el modo de JSON y guarda el resultado en la conexion. mode external:
 * la prueba como endpoint de un agente propio (un turno en streaming; docs/features/LLM_CONEXIONES.md). */
export function useTestLlmConnection(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, model, mode = 'llm' }: { id: string; model?: string; mode?: 'llm' | 'external' }) =>
      unwrap(
        api.POST(`${BASE}/{connection_id}/test`, {
          params: { path: { client_id: clientId, connection_id: id } },
          body: { model: model || null, mode },
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
