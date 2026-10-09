import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';

export const inferenceKeys = {
  usage: (clientId: string, month: string) => ['clients', clientId, 'inference-usage', month] as const,
};

/** Consumo del mes de la API de inferencia contra los limites del tier. */
export function useInferenceUsage(
  clientId: string | undefined,
  month: string,
  refetchInterval: number | false = false,
) {
  return useQuery({
    queryKey: inferenceKeys.usage(clientId ?? '', month),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/clients/{client_id}/inference-usage', {
          params: { path: { client_id: clientId! }, query: { month } },
        }),
      ),
    enabled: !!clientId,
    placeholderData: keepPreviousData,
    refetchInterval,
  });
}
