import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { TierIn } from '@/api/types';

export const tierKeys = { all: ['tiers'] as const };

export function useTiers(enabled = true) {
  return useQuery({
    queryKey: tierKeys.all,
    queryFn: () => unwrap(api.GET('/api/v1/tiers')),
    enabled,
  });
}

export function useSaveTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: TierIn }) =>
      id
        ? unwrap(api.PATCH('/api/v1/tiers/{tier_id}', { params: { path: { tier_id: id } }, body }))
        : unwrap(api.POST('/api/v1/tiers', { body })),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: tierKeys.all });
      void qc.invalidateQueries({ queryKey: ['clients'] });
    },
  });
}

export function useDeleteTier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/tiers/{tier_id}', { params: { path: { tier_id: id } } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: tierKeys.all }),
  });
}
