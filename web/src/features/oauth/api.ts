import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';

/** OAuth del servidor MCP (docs/MCP_PLAN.md, 4.2): consentimiento y agentes conectados. */
export const oauthKeys = {
  authorize: (params: Record<string, string>) => ['oauth', 'authorize', params] as const,
  grants: (clientId: string) => ['oauth', 'grants', clientId] as const,
};

/** El pedido de un agente de IA (la query de /oauth/authorize), validado por la API. */
export function useAuthorizeInfo(params: Record<string, string>) {
  return useQuery({
    queryKey: oauthKeys.authorize(params),
    queryFn: () => unwrap(api.GET('/api/v1/oauth/authorize', { params: { query: params as never } })),
    retry: false,
    staleTime: Infinity,
  });
}

export function useAuthorizeDecision() {
  return useMutation({
    mutationFn: (body: { params: Record<string, string>; approve: boolean; client_id?: string | null }) =>
      unwrap(api.POST('/api/v1/oauth/authorize', { body })),
  });
}

export function useOAuthGrants(clientId: string) {
  return useQuery({
    queryKey: oauthKeys.grants(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/oauth/grants', { params: { query: { client_id: clientId } } })),
  });
}

export function useRevokeGrant(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (grantId: string) =>
      unwrap(api.DELETE('/api/v1/oauth/grants/{grant_id}', { params: { path: { grant_id: grantId } } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: oauthKeys.grants(clientId) }),
  });
}
