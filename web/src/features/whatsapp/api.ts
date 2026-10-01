import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { WaAccountIn, WaAccountPatch } from '@/api/types';

export const waKeys = {
  all: ['wa-accounts'] as const,
  list: (clientId?: string) => ['wa-accounts', clientId ?? 'all'] as const,
};

/** Numeros de WhatsApp conectados (solo admin). El token nunca viene: solo has_token. */
export function useWaAccounts(clientId?: string) {
  return useQuery({
    queryKey: waKeys.list(clientId),
    queryFn: () =>
      unwrap(api.GET('/api/v1/whatsapp/accounts', { params: { query: { client_id: clientId } } })),
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: waKeys.all });
}

export function useCreateWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaAccountIn) => unwrap(api.POST('/api/v1/whatsapp/accounts', { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WaAccountPatch }) =>
      unwrap(
        api.PATCH('/api/v1/whatsapp/accounts/{account_id}', { params: { path: { account_id: id } }, body }),
      ),
    onSuccess: invalidate,
  });
}

export function useDeactivateWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.POST('/api/v1/whatsapp/accounts/{account_id}/deactivate', {
          params: { path: { account_id: id } },
        }),
      ),
    onSuccess: invalidate,
  });
}
