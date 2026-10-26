import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { BrandingIn } from '@/api/types';
import { clientKeys } from './api';

/** Marca blanca de un cliente, para el admin (docs/MARCA_BLANCA_PLAN.md). */

const key = (clientId: string) => [...clientKeys.detail(clientId), 'branding'] as const;
const path = (clientId: string) => ({ params: { path: { client_id: clientId } } });

export function useClientBranding(clientId: string) {
  return useQuery({
    queryKey: key(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/clients/{client_id}/branding', path(clientId))),
  });
}

export function useUpdateBranding(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BrandingIn) =>
      unwrap(api.PUT('/api/v1/clients/{client_id}/branding', { ...path(clientId), body })),
    onSuccess: (data) => qc.setQueryData(key(clientId), data),
  });
}

export function useSetBrandingLogo(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.PUT('/api/v1/clients/{client_id}/branding/logo', {
          ...path(clientId),
          body: { file: file as unknown as string },
          bodySerializer: (body) => {
            const form = new FormData();
            form.append('file', body.file as unknown as File);
            return form;
          },
        }),
      ),
    onSuccess: (data) => qc.setQueryData(key(clientId), data),
  });
}

export function useRemoveBrandingLogo(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/v1/clients/{client_id}/branding/logo', path(clientId))),
    onSuccess: (data) => qc.setQueryData(key(clientId), data),
  });
}
