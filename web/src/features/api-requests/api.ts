import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import { BROWSER_TZ } from '@/features/calls/api';

export type ApiKind = 'llm' | 'stt' | 'tts';
export type ApiRequestStatus = 'ok' | 'cut' | 'error' | 'rejected';
export type ApiSource = 'api' | 'voice_test_panel' | 'voice_test_api' | 'voice_test_landing';

export interface ApiRequestParams {
  client_id?: string;
  api_key_id?: string;
  kind?: ApiKind[];
  status?: ApiRequestStatus[];
  source?: ApiSource[];
  stream?: boolean;
  date_from?: string;
  date_to?: string;
  limit: number;
  offset: number;
}

export const apiRequestKeys = {
  list: (p: ApiRequestParams) => ['api-requests', p] as const,
};

/** Pedidos a la API de inferencia con los totales del filtro; se refresca cada 5 s. */
export function useApiRequests(p: ApiRequestParams) {
  return useQuery({
    queryKey: apiRequestKeys.list(p),
    queryFn: () => unwrap(api.GET('/api/v1/api-requests', { params: { query: { ...p, tz: BROWSER_TZ } } })),
    refetchInterval: 5000,
    placeholderData: keepPreviousData,
  });
}

export const apiRequestContentKeys = {
  one: (id: string) => ['api-request-content', id] as const,
};

/** Pedido y respuesta guardados de un pedido (404 si no hay, venció o se borró). */
export function useApiRequestContent(id: string, enabled: boolean) {
  return useQuery({
    queryKey: apiRequestContentKeys.one(id),
    queryFn: () =>
      unwrap(api.GET('/api/v1/api-requests/{request_id}/content', { params: { path: { request_id: id } } })),
    enabled,
    retry: false,
  });
}

/** El audio se sirve con la sesión del panel: el `<audio>` y el link de bajada usan esta URL. */
export function apiAudioUrl(id: string, which: 'input' | 'output', download = false): string {
  return `/api/v1/api-requests/${id}/audio/${which}${download ? '?download=true' : ''}`;
}

/** Borra el contenido guardado; el pedido (consumo, estado) queda. */
export function useDeleteApiRequestContent(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/v1/api-requests/{request_id}/content', { params: { path: { request_id: id } } }),
      ),
    onSuccess: (_d, id) => {
      qc.removeQueries({ queryKey: apiRequestContentKeys.one(id) });
      void qc.invalidateQueries({ queryKey: ['api-requests'] });
      void qc.invalidateQueries({ queryKey: ['clients', clientId, 'api-content'] });
    },
  });
}
