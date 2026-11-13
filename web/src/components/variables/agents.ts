import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { DeclaredVariable } from './catalog';

// Variables que declaran los agentes del cliente (`definition.variables`), para ofrecerlas donde el catálogo
// no llega: los campos de una herramienta y los mensajes de un área de derivación.

const str = (x: unknown): string => (typeof x === 'string' ? x : x == null ? '' : String(x));

/** Las `variables` de una definición de agente, en su orden y sin las filas sin nombre. */
export function declaredInDefinition(definition: unknown): DeclaredVariable[] {
  const raw = (definition as { variables?: unknown } | null | undefined)?.variables;
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((item) => {
    const v = item as { name?: unknown; description?: unknown } | null;
    const name = str(v?.name).trim();
    return name ? [{ name, description: str(v?.description) }] : [];
  });
}

/**
 * Las variables declaradas por los agentes indicados, sin repetir (gana el primero). Se piden sus
 * definiciones (`GET /agents/{id}`) porque la lista de agentes no las trae.
 */
export function useAgentVariables(agents: { id: string; name: string }[] | undefined): DeclaredVariable[] {
  const refs = agents ?? [];
  const key = refs.map((a) => a.id).sort().join(',');
  const query = useQuery({
    queryKey: ['variables', 'agents', key],
    queryFn: () =>
      Promise.all(
        refs.map(async (a) => {
          const agent = await unwrap(
            api.GET('/api/v1/agents/{agent_id}', { params: { path: { agent_id: a.id } } }),
          );
          return declaredInDefinition(agent.definition).map((v) => ({
            name: v.name,
            kind: 'declared' as const,
            description: [v.description, `del agente ${a.name}`].filter(Boolean).join(' · '),
          }));
        }),
      ),
    enabled: refs.length > 0,
    staleTime: 5 * 60_000,
  });
  return useMemo(() => {
    const out: DeclaredVariable[] = [];
    const seen = new Set<string>();
    for (const v of (query.data ?? []).flat()) {
      if (seen.has(v.name)) continue;
      seen.add(v.name);
      out.push(v);
    }
    return out;
  }, [query.data]);
}
