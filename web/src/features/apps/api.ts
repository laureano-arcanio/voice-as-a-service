import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { AppLinkIn } from '@/api/types';

export const appKeys = {
  all: ['apps'] as const,
  list: (clientId?: string) => ['apps', 'list', clientId ?? 'all'] as const,
  links: (appId: string) => ['apps', 'links', appId] as const,
};

/** Apps de los clientes (docs/APPS_PLAN.md): el admin ve todas; el cliente, las suyas. */
export function useApps(clientId?: string, enabled = true) {
  return useQuery({
    queryKey: appKeys.list(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/apps', { params: { query: { client_id: clientId } } })),
    enabled,
  });
}

export function useAppLinks(appId: string | undefined) {
  return useQuery({
    queryKey: appKeys.links(appId ?? ''),
    queryFn: () =>
      unwrap(api.GET('/api/v1/apps/{app_id}/links', { params: { path: { app_id: appId ?? '' } } })),
    enabled: !!appId,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: appKeys.all });
}

const appPath = (id: string) => ({ params: { path: { app_id: id } } });

export function useAssignApp() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, clientId }: { id: string; clientId: string }) =>
      unwrap(api.POST('/api/v1/apps/{app_id}/assign', { ...appPath(id), body: { client_id: clientId } })),
    onSuccess: invalidate,
  });
}

export function useReleaseApp() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.POST('/api/v1/apps/{app_id}/release', appPath(id))),
    onSuccess: invalidate,
  });
}

export function useRefreshApp() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.POST('/api/v1/apps/{app_id}/refresh', appPath(id))),
    onSuccess: invalidate,
  });
}

export function useDeleteApp() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.DELETE('/api/v1/apps/{app_id}', appPath(id))),
    onSuccess: invalidate,
  });
}

/** Link a una vista: la URL solo viene en esta respuesta (el token no se guarda). */
export function useCreateAppLink() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: AppLinkIn }) =>
      unwrap(api.POST('/api/v1/apps/{app_id}/links', { ...appPath(id), body })),
    onSuccess: invalidate,
  });
}

export function useRevokeAppLink() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, linkId }: { id: string; linkId: string }) =>
      unwrap(
        api.DELETE('/api/v1/apps/{app_id}/links/{link_id}', {
          params: { path: { app_id: id, link_id: linkId } },
        }),
      ),
    onSuccess: invalidate,
  });
}
