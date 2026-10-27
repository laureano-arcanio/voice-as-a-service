import type { Agent } from '@/api/types';

/** Opciones del select de agentes. */
export function agentOptions(agents: Agent[]) {
  return agents.map((a) => ({ value: a.id, label: `${a.name} · v${a.version}` }));
}
