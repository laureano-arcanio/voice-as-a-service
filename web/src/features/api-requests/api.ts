import { keepPreviousData, useQuery } from '@tanstack/react-query';
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
