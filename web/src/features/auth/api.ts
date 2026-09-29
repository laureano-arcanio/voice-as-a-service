import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { toApiError } from '@/api/errors';
import { unwrap } from '@/api/request';
import type { Me } from '@/api/types';

export const meKey = ['me'] as const;

/** Usuario de la sesion, o null si no hay (401). */
async function fetchMe(): Promise<Me | null> {
  const { data, error, response } = await api.GET('/api/v1/auth/me');
  if (response.status === 401) return null;
  if (!response.ok) throw toApiError(error, response.status);
  return data ?? null;
}

export function useMe() {
  return useQuery({ queryKey: meKey, queryFn: fetchMe, staleTime: 60_000, retry: false });
}

/** Usuario de la sesion ya cargado (dentro de las rutas protegidas). */
export function useCurrentUser(): Me {
  const { data } = useMe();
  if (!data) throw new Error('useCurrentUser fuera de una ruta autenticada');
  return data;
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      unwrap(api.POST('/api/v1/auth/login', { body })),
    onSuccess: (me) => {
      qc.clear();
      qc.setQueryData(meKey, me);
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/v1/auth/logout')),
    onSettled: () => {
      qc.clear();
      qc.setQueryData(meKey, null);
    },
  });
}

export function useIsAdmin(): boolean {
  const { data } = useMe();
  return data?.role === 'admin';
}
