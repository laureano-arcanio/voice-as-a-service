import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { PhoneNumberUpdate } from '@/api/types';

export type NumberStatus = 'free' | 'assigned';

export interface NumberFilters {
  clientId?: string;
  status?: NumberStatus;
}

export const numberKeys = {
  all: ['phone-numbers'] as const,
  list: (f: NumberFilters) => ['phone-numbers', f.clientId ?? 'all', f.status ?? 'all'] as const,
};

/** Numeros del inventario: admin ve todos; un usuario de cliente, los suyos. */
export function usePhoneNumbers(f: NumberFilters = {}, enabled = true) {
  return useQuery({
    queryKey: numberKeys.list(f),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/phone-numbers', { params: { query: { client_id: f.clientId, status: f.status } } }),
      ),
    enabled,
  });
}

/** Cambios de numeros: afectan el inventario, los contadores y el consumo de los clientes. */
function useInvalidateNumbers() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: numberKeys.all });
    void qc.invalidateQueries({ queryKey: ['clients'] });
  };
}

export function useBulkLoadNumbers() {
  const invalidate = useInvalidateNumbers();
  return useMutation({
    mutationFn: (body: { numbers: string[]; label: string; provider: string }) =>
      unwrap(api.POST('/api/v1/phone-numbers/bulk', { body })),
    onSuccess: invalidate,
  });
}

export function useAssignNumber() {
  const invalidate = useInvalidateNumbers();
  return useMutation({
    mutationFn: ({ id, clientId }: { id: string; clientId: string }) =>
      unwrap(
        api.POST('/api/v1/phone-numbers/{number_id}/assign', {
          params: { path: { number_id: id } },
          body: { client_id: clientId },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useReleaseNumber() {
  const invalidate = useInvalidateNumbers();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.POST('/api/v1/phone-numbers/{number_id}/release', { params: { path: { number_id: id } } })),
    onSuccess: invalidate,
  });
}

export function useUpdateNumber() {
  const invalidate = useInvalidateNumbers();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: PhoneNumberUpdate }) =>
      unwrap(api.PATCH('/api/v1/phone-numbers/{number_id}', { params: { path: { number_id: id } }, body })),
    onSuccess: invalidate,
  });
}

export function useDeleteNumber() {
  const invalidate = useInvalidateNumbers();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/phone-numbers/{number_id}', { params: { path: { number_id: id } } })),
    onSuccess: invalidate,
  });
}
