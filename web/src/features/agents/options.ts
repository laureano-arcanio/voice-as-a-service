import type { Agent, Client } from '@/api/types';

/** Opciones del select de agentes: para admin, agrupados por cliente. */
export function agentOptions(agents: Agent[], clients: Client[] | undefined, grouped: boolean) {
  const option = (a: Agent) => ({ value: a.id, label: `${a.name} · v${a.version}` });
  if (!grouped) return agents.map(option);
  const names = new Map((clients ?? []).map((c) => [c.id, c.name]));
  const groups = new Map<string, Agent[]>();
  for (const a of agents) {
    const g = names.get(a.client_id) ?? 'Otro cliente';
    groups.set(g, [...(groups.get(g) ?? []), a]);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b, 'es'))
    .map(([group, items]) => ({ group, items: items.map(option) }));
}
