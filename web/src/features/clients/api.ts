import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { ApiScope, ClientIn, ClientUpdate } from '@/api/types';

export const clientKeys = {
  all: ['clients'] as const,
  detail: (id: string) => ['clients', id] as const,
  usage: (id: string, month: string) => ['clients', id, 'usage', month] as const,
};

export const apiKeyKeys = {
  list: (clientId: string) => ['api-keys', clientId] as const,
};

export function useClients(enabled = true) {
  return useQuery({
    queryKey: clientKeys.all,
    queryFn: () => unwrap(api.GET('/api/v1/clients')),
    enabled,
  });
}

export function useClient(id: string | undefined) {
  return useQuery({
    queryKey: clientKeys.detail(id ?? ''),
    queryFn: () => unwrap(api.GET('/api/v1/clients/{client_id}', { params: { path: { client_id: id! } } })),
    enabled: !!id,
  });
}

export function useClientUsage(
  id: string | undefined,
  month: string,
  refetchInterval: number | false = false,
) {
  return useQuery({
    queryKey: clientKeys.usage(id ?? '', month),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/clients/{client_id}/usage', {
          params: { path: { client_id: id! }, query: { month } },
        }),
      ),
    enabled: !!id,
    placeholderData: keepPreviousData,
    refetchInterval,
  });
}

export function useCreateClient() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ClientIn) => unwrap(api.POST('/api/v1/clients', { body })),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: clientKeys.all });
      void qc.invalidateQueries({ queryKey: ['tiers'] });
    },
  });
}

export function useUpdateClient(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ClientUpdate) =>
      unwrap(api.PATCH('/api/v1/clients/{client_id}', { params: { path: { client_id: id } }, body })),
    onSuccess: (client) => {
      qc.setQueryData(clientKeys.detail(id), client);
      void qc.invalidateQueries({ queryKey: clientKeys.all });
      void qc.invalidateQueries({ queryKey: ['tiers'] });
    },
  });
}

export function useDeleteClient() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/clients/{client_id}', { params: { path: { client_id: id } } })),
    onSuccess: (_, id) => {
      qc.removeQueries({ queryKey: clientKeys.detail(id) });
      void qc.invalidateQueries({ queryKey: clientKeys.all });
      void qc.invalidateQueries({ queryKey: ['tiers'] });
    },
  });
}

// ---- API keys ----

export function useApiKeys(clientId: string | undefined) {
  return useQuery({
    queryKey: apiKeyKeys.list(clientId ?? ''),
    queryFn: () =>
      unwrap(api.GET('/api/v1/clients/{client_id}/api-keys', { params: { path: { client_id: clientId! } } })),
    enabled: !!clientId,
  });
}

export function useCreateApiKey(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, scopes }: { name: string; scopes: ApiScope[] }) =>
      unwrap(
        api.POST('/api/v1/clients/{client_id}/api-keys', {
          params: { path: { client_id: clientId } },
          body: { name, scopes },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: apiKeyKeys.list(clientId) }),
  });
}

export function useRevokeApiKey(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      unwrap(
        api.DELETE('/api/v1/clients/{client_id}/api-keys/{key_id}', {
          params: { path: { client_id: clientId, key_id: keyId } },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: apiKeyKeys.list(clientId) }),
  });
}
