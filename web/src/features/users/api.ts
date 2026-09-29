import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { UserIn, UserUpdate } from '@/api/types';

export const userKeys = {
  all: ['users'] as const,
  list: (clientId?: string) => ['users', clientId ?? 'all'] as const,
};

export function useUsers(clientId?: string, enabled = true) {
  return useQuery({
    queryKey: userKeys.list(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/users', { params: { query: { client_id: clientId } } })),
    enabled,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UserIn) => unwrap(api.POST('/api/v1/users', { body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: userKeys.all }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UserUpdate }) =>
      unwrap(api.PATCH('/api/v1/users/{user_id}', { params: { path: { user_id: id } }, body })),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: userKeys.all });
      void qc.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/users/{user_id}', { params: { path: { user_id: id } } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: userKeys.all }),
  });
}
