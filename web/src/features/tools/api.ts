import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type {
  AgentSecretIn,
  AgentSecretPatch,
  CredentialIn,
  CredentialUpdate,
  ToolDraftTestIn,
  ToolIn,
} from '@/api/types';
import { useCurrentUser } from '@/features/auth/api';

export const toolKeys = {
  all: ['tools'] as const,
  list: (clientId: string) => ['tools', clientId] as const,
  detail: (clientId: string, slug: string) => ['tools', clientId, slug] as const,
  template: ['tools-code-template'] as const,
  status: ['tools-status'] as const,
  secrets: (agentId: string) => ['agent-secrets', agentId] as const,
  agentSecrets: ['agent-secrets'] as const,
  clientSecrets: (clientId: string) => ['client-secrets', clientId] as const,
  credentials: (clientId: string) => ['credentials', clientId] as const,
};

/**
 * Lo que cambia al tocar un secreto o una credencial: los del cliente, los de los agentes (heredan del
 * cliente), las credenciales (dicen si su secreto esta) y las herramientas (los secretos que piden).
 */
function useInvalidateSecrets(clientId?: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: toolKeys.agentSecrets });
    if (!clientId) {
      void qc.invalidateQueries({ queryKey: ['client-secrets'] });
      void qc.invalidateQueries({ queryKey: ['credentials'] });
      return;
    }
    void qc.invalidateQueries({ queryKey: toolKeys.clientSecrets(clientId) });
    void qc.invalidateQueries({ queryKey: toolKeys.credentials(clientId) });
    void qc.invalidateQueries({ queryKey: toolKeys.list(clientId) });
  };
}

/** El cliente de la pantalla: el del usuario (o el que el admin eligió al entrar como cliente). */
export function useToolsClient(): string | undefined {
  return useCurrentUser().client_id ?? undefined;
}

/** Link a una pantalla de herramientas. Solo lo usa features/agents/ (ahí `isAdmin` ya no se cumple en el
 * panel del cliente); a borrar cuando esas pantallas pasen a rutas directas. */
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

// ---------- secretos de un agente (pisan a los del cliente) ----------

const SECRETS = '/api/v1/agents/{agent_id}/secrets';

export function useAgentSecrets(agentId: string | undefined) {
  return useQuery({
    queryKey: toolKeys.secrets(agentId ?? ''),
    queryFn: () => unwrap(api.GET(SECRETS, { params: { path: { agent_id: agentId! } } })),
    enabled: !!agentId,
  });
}

export function useCreateSecret(agentId: string) {
  const done = useInvalidateSecrets();
  return useMutation({
    mutationFn: (body: AgentSecretIn) =>
      unwrap(api.POST(SECRETS, { params: { path: { agent_id: agentId } }, body })),
    onSuccess: done,
  });
}

export function useUpdateSecret(agentId: string) {
  const done = useInvalidateSecrets();
  return useMutation({
    mutationFn: ({ name, body }: { name: string; body: AgentSecretPatch }) =>
      unwrap(api.PATCH(`${SECRETS}/{name}`, { params: { path: { agent_id: agentId, name } }, body })),
    onSuccess: done,
  });
}

export function useDeleteSecret(agentId: string) {
  const done = useInvalidateSecrets();
  return useMutation({
    mutationFn: (name: string) =>
      unwrap(api.DELETE(`${SECRETS}/{name}`, { params: { path: { agent_id: agentId, name } } })),
    onSuccess: done,
  });
}

/** Pasa un secreto del agente al cliente (para todos los agentes). */
export function usePromoteSecret(agentId: string) {
  const done = useInvalidateSecrets();
  return useMutation({
    mutationFn: (name: string) =>
      unwrap(api.POST(`${SECRETS}/{name}/promote`, { params: { path: { agent_id: agentId, name } } })),
    onSuccess: done,
  });
}

// ---------- secretos del cliente (para todos sus agentes) ----------

const CLIENT_SECRETS = '/api/v1/clients/{client_id}/secrets';

export function useClientSecrets(clientId: string | undefined) {
  return useQuery({
    queryKey: toolKeys.clientSecrets(clientId ?? ''),
    queryFn: () => unwrap(api.GET(CLIENT_SECRETS, { params: { path: { client_id: clientId! } } })),
    enabled: !!clientId,
  });
}

export function useCreateClientSecret(clientId: string) {
  const done = useInvalidateSecrets(clientId);
  return useMutation({
    mutationFn: (body: AgentSecretIn) =>
      unwrap(api.POST(CLIENT_SECRETS, { params: { path: { client_id: clientId } }, body })),
    onSuccess: done,
  });
}

export function useUpdateClientSecret(clientId: string) {
  const done = useInvalidateSecrets(clientId);
  return useMutation({
    mutationFn: ({ name, body }: { name: string; body: AgentSecretPatch }) =>
      unwrap(
        api.PATCH(`${CLIENT_SECRETS}/{name}`, { params: { path: { client_id: clientId, name } }, body }),
      ),
    onSuccess: done,
  });
}

export function useDeleteClientSecret(clientId: string) {
  const done = useInvalidateSecrets(clientId);
  return useMutation({
    mutationFn: (name: string) =>
      unwrap(api.DELETE(`${CLIENT_SECRETS}/{name}`, { params: { path: { client_id: clientId, name } } })),
    onSuccess: done,
  });
}

// ---------- credenciales ----------

const CREDENTIALS = '/api/v1/clients/{client_id}/credentials';

export function useCredentials(clientId: string | undefined) {
  return useQuery({
    queryKey: toolKeys.credentials(clientId ?? ''),
    queryFn: () => unwrap(api.GET(CREDENTIALS, { params: { path: { client_id: clientId! } } })),
    enabled: !!clientId,
  });
}

export function useCreateCredential(clientId: string) {
  const done = useInvalidateSecrets(clientId);
  return useMutation({
    mutationFn: (body: CredentialIn) =>
      unwrap(api.POST(CREDENTIALS, { params: { path: { client_id: clientId } }, body })),
    onSuccess: done,
  });
}

export function useUpdateCredential(clientId: string) {
  const done = useInvalidateSecrets(clientId);
  return useMutation({
    mutationFn: ({ slug, body }: { slug: string; body: CredentialUpdate }) =>
      unwrap(api.PUT(`${CREDENTIALS}/{slug}`, { params: { path: { client_id: clientId, slug } }, body })),
    onSuccess: done,
  });
}

export function useDeleteCredential(clientId: string) {
  const done = useInvalidateSecrets(clientId);
  return useMutation({
    mutationFn: (slug: string) =>
      unwrap(api.DELETE(`${CREDENTIALS}/{slug}`, { params: { path: { client_id: clientId, slug } } })),
    onSuccess: done,
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
