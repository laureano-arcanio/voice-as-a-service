import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { AgentSecretIn, AgentSecretPatch, ToolDraftTestIn, ToolIn } from '@/api/types';
import { useCurrentUser } from '@/features/auth/api';

export const toolKeys = {
  all: ['tools'] as const,
  list: (clientId: string) => ['tools', clientId] as const,
  detail: (clientId: string, slug: string) => ['tools', clientId, slug] as const,
  template: ['tools-code-template'] as const,
  status: ['tools-status'] as const,
  secrets: (agentId: string) => ['agent-secrets', agentId] as const,
};

/** El cliente de la pantalla: el del usuario, o el elegido por el admin (?client=). */
export function useToolsClient(): string | undefined {
  const me = useCurrentUser();
  const [params] = useSearchParams();
  return me.role === 'admin' ? (params.get('client') ?? undefined) : (me.client_id ?? undefined);
}

/** Link a una pantalla de herramientas, con el cliente elegido por el admin. */
export function toolsHref(path: string, clientId: string | undefined, isAdmin: boolean): string {
  if (!isAdmin || !clientId) return path;
  return `${path}${path.includes('?') ? '&' : '?'}client=${encodeURIComponent(clientId)}`;
}

const BASE = '/api/v1/clients/{client_id}/tools';

export function useTools(clientId: string | undefined) {
  return useQuery({
    queryKey: toolKeys.list(clientId ?? ''),
    queryFn: () => unwrap(api.GET(BASE, { params: { path: { client_id: clientId! } } })),
    enabled: !!clientId,
  });
}

export function useTool(clientId: string | undefined, slug: string | undefined) {
  return useQuery({
    queryKey: toolKeys.detail(clientId ?? '', slug ?? ''),
    queryFn: () =>
      unwrap(api.GET(`${BASE}/{slug}`, { params: { path: { client_id: clientId!, slug: slug! } } })),
    enabled: !!clientId && !!slug,
  });
}

/** La funcion de ejemplo con la que arranca una herramienta de codigo. */
export function useCodeTemplate(enabled = true) {
  return useQuery({
    queryKey: toolKeys.template,
    queryFn: () => unwrap(api.GET('/api/v1/tools/code-template')),
    staleTime: Infinity,
    enabled,
  });
}

/** Si el sandbox de codigo esta configurado en el servidor. */
export function useToolsStatus() {
  return useQuery({
    queryKey: toolKeys.status,
    queryFn: () => unwrap(api.GET('/api/v1/tools/status')),
    staleTime: 5 * 60_000,
  });
}

export function useCreateTool(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ToolIn) => unwrap(api.POST(BASE, { params: { path: { client_id: clientId } }, body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: toolKeys.list(clientId) }),
  });
}

export function useUpdateTool(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, body }: { slug: string; body: Omit<ToolIn, 'slug'> }) =>
      unwrap(api.PUT(`${BASE}/{slug}`, { params: { path: { client_id: clientId, slug } }, body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: toolKeys.list(clientId) }),
  });
}

export function useDeleteTool(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) =>
      unwrap(api.DELETE(`${BASE}/{slug}`, { params: { path: { client_id: clientId, slug } } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: toolKeys.list(clientId) }),
  });
}

/** Prueba de verdad (llama a la API o corre el codigo) con una definicion sin guardar. */
export function useTestToolDraft(clientId: string) {
  return useMutation({
    mutationFn: (body: ToolDraftTestIn) =>
      unwrap(api.POST(`${BASE}/test`, { params: { path: { client_id: clientId } }, body })),
  });
}

// ---------- secretos de un agente ----------

const SECRETS = '/api/v1/agents/{agent_id}/secrets';

export function useAgentSecrets(agentId: string | undefined) {
  return useQuery({
    queryKey: toolKeys.secrets(agentId ?? ''),
    queryFn: () => unwrap(api.GET(SECRETS, { params: { path: { agent_id: agentId! } } })),
    enabled: !!agentId,
  });
}

export function useCreateSecret(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentSecretIn) =>
      unwrap(api.POST(SECRETS, { params: { path: { agent_id: agentId } }, body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: toolKeys.secrets(agentId) }),
  });
}

export function useUpdateSecret(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, body }: { name: string; body: AgentSecretPatch }) =>
      unwrap(api.PATCH(`${SECRETS}/{name}`, { params: { path: { agent_id: agentId, name } }, body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: toolKeys.secrets(agentId) }),
  });
}

export function useDeleteSecret(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      unwrap(api.DELETE(`${SECRETS}/{name}`, { params: { path: { agent_id: agentId, name } } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: toolKeys.secrets(agentId) }),
  });
}

/** Historial: cada revision con su definicion, la mas nueva primero. */
export function useToolVersions(clientId: string | undefined, slug: string | undefined, enabled = true) {
  return useQuery({
    queryKey: [...toolKeys.detail(clientId ?? '', slug ?? ''), 'versions'],
    queryFn: () =>
      unwrap(api.GET(`${BASE}/{slug}/versions`, { params: { path: { client_id: clientId!, slug: slug! } } })),
    enabled: enabled && !!clientId && !!slug,
  });
}
