import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { CallLinkIn, CallLinkPatch } from '@/api/types';

// Link publico para llamar al agente desde el navegador (docs/LINK_LLAMADA_PLAN.md).

const key = (agentId: string) => ['agents', 'call-link', agentId] as const;
const path = (agentId: string) => ({ params: { path: { agent_id: agentId } } });

export function useCallLink(agentId: string) {
  return useQuery({
    queryKey: key(agentId),
    queryFn: () => unwrap(api.GET('/api/v1/agents/{agent_id}/call-link', path(agentId))),
  });
}

function useRefresh(agentId: string) {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: key(agentId) });
}

export function useCreateCallLink(agentId: string) {
  const refresh = useRefresh(agentId);
  return useMutation({
    mutationFn: (body: CallLinkIn) =>
      unwrap(api.POST('/api/v1/agents/{agent_id}/call-link', { ...path(agentId), body })),
    onSuccess: refresh,
  });
}

export function useUpdateCallLink(agentId: string) {
  const refresh = useRefresh(agentId);
  return useMutation({
    mutationFn: (body: CallLinkPatch) =>
      unwrap(api.PATCH('/api/v1/agents/{agent_id}/call-link', { ...path(agentId), body })),
    onSuccess: refresh,
  });
}

export function useRotateCallLink(agentId: string) {
  const refresh = useRefresh(agentId);
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/v1/agents/{agent_id}/call-link/rotate', path(agentId))),
    onSuccess: refresh,
  });
}

export function useDeleteCallLink(agentId: string) {
  const refresh = useRefresh(agentId);
  return useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/v1/agents/{agent_id}/call-link', path(agentId))),
    onSuccess: refresh,
  });
}

/** Imagen de arriba de la pagina (PNG, JPG o WebP): el server la recorta y la achica. */
export function useSetCallLinkImage(agentId: string) {
  const refresh = useRefresh(agentId);
  return useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.PUT('/api/v1/agents/{agent_id}/call-link/image', {
          ...path(agentId),
          body: { file: file as unknown as string },
          bodySerializer: (body) => {
            const form = new FormData();
            form.append('file', body.file as unknown as File);
            return form;
          },
        }),
      ),
    onSuccess: refresh,
  });
}

export function useRemoveCallLinkImage(agentId: string) {
  const refresh = useRefresh(agentId);
  return useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/v1/agents/{agent_id}/call-link/image', path(agentId))),
    onSuccess: refresh,
  });
}
