import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { AgentCreate, AgentUpdate, Definition } from '@/api/types';

export const agentKeys = {
  all: ['agents'] as const,
  list: (clientId?: string, includeArchived = false) =>
    ['agents', 'list', clientId ?? 'all', includeArchived] as const,
  detail: (id: string) => ['agents', 'detail', id] as const,
  versions: (id: string) => ['agents', 'versions', id] as const,
  version: (id: string, v: number) => ['agents', 'versions', id, v] as const,
  templates: ['agent-templates'] as const,
};

export function useAgents(clientId?: string, includeArchived = false, enabled = true) {
  return useQuery({
    enabled,
    queryKey: agentKeys.list(clientId, includeArchived),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/agents', {
          params: { query: { client_id: clientId, include_archived: includeArchived } },
        }),
      ),
  });
}

export function useAgent(id: string | undefined) {
  return useQuery({
    queryKey: agentKeys.detail(id ?? ''),
    queryFn: () => unwrap(api.GET('/api/v1/agents/{agent_id}', { params: { path: { agent_id: id! } } })),
    enabled: !!id,
  });
}

export function useAgentVersions(id: string) {
  return useQuery({
    queryKey: agentKeys.versions(id),
    queryFn: () =>
      unwrap(api.GET('/api/v1/agents/{agent_id}/versions', { params: { path: { agent_id: id } } })),
  });
}

export function fetchAgentVersion(id: string, version: number) {
  return unwrap(
    api.GET('/api/v1/agents/{agent_id}/versions/{version}', { params: { path: { agent_id: id, version } } }),
  );
}

export function useAgentVersion(id: string, version: number | null) {
  return useQuery({
    queryKey: agentKeys.version(id, version ?? 0),
    queryFn: () => fetchAgentVersion(id, version!),
    enabled: version != null,
    staleTime: Infinity, // las versiones son inmutables
  });
}

export function useAgentTemplates(enabled = true) {
  return useQuery({
    queryKey: agentKeys.templates,
    queryFn: () => unwrap(api.GET('/api/v1/agent-templates')),
    staleTime: 10 * 60_000,
    enabled,
  });
}

function useInvalidateAgents() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: agentKeys.all });
    void qc.invalidateQueries({ queryKey: ['clients'] });
    void qc.invalidateQueries({ queryKey: ['phone-numbers'] });
  };
}

export function useCreateAgent() {
  const invalidate = useInvalidateAgents();
  return useMutation({
    mutationFn: (body: AgentCreate) => unwrap(api.POST('/api/v1/agents', { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateAgent(id: string) {
  const invalidate = useInvalidateAgents();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentUpdate) =>
      unwrap(api.PATCH('/api/v1/agents/{agent_id}', { params: { path: { agent_id: id } }, body })),
    onSuccess: (agent) => {
      qc.setQueryData(agentKeys.detail(id), agent);
      invalidate();
    },
  });
}

export function useSaveDefinition(id: string) {
  const invalidate = useInvalidateAgents();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (definition: Definition) =>
      unwrap(
        api.PUT('/api/v1/agents/{agent_id}/definition', {
          params: { path: { agent_id: id } },
          body: { definition },
        }),
      ),
    onSuccess: (agent) => {
      qc.setQueryData(agentKeys.detail(id), agent);
      invalidate();
    },
  });
}

export function useDeleteAgent() {
  const invalidate = useInvalidateAgents();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/agents/{agent_id}', { params: { path: { agent_id: id } } })),
    onSuccess: (_, id) => {
      qc.removeQueries({ queryKey: agentKeys.detail(id) });
      invalidate();
    },
  });
}

export function validateDefinition(definition: Definition, signal?: AbortSignal) {
  return unwrap(api.POST('/api/v1/agents/validate', { body: { definition }, signal }));
}
