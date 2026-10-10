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

/** Datos del link del mail de alta (email, nombre y cliente), o ApiError si venció o ya se usó. */
export function usePasswordSetupInfo(token: string) {
  return useQuery({
    queryKey: ['password-setup', token],
    queryFn: () => unwrap(api.POST('/api/v1/auth/password-setup/check', { body: { token } })),
    enabled: !!token,
    retry: false,
    staleTime: Infinity,
  });
}

/** Guarda la clave del link y deja la sesion abierta. */
export function usePasswordSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { token: string; password: string }) =>
      unwrap(api.POST('/api/v1/auth/password-setup', { body })),
    onSuccess: (me) => {
      qc.clear();
      qc.setQueryData(meKey, me);
    },
  });
}

/** Olvidé mi clave: siempre 202 (no revela si el email tiene cuenta). Devuelve el email pedido. */
export function usePasswordReset() {
  return useMutation({
    mutationFn: async (email: string) => {
      await unwrap(api.POST('/api/v1/auth/password-reset', { body: { email } }));
      return email;
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
