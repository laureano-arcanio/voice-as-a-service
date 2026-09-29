import { Select } from '@mantine/core';
import type { PhoneNumber } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateNumber } from './api';
import { numberErrorTitle } from './errors';

/** Agente que atiende las entrantes a un numero asignado, editable en la fila. */
export function NumberAgentSelect({ number, disabled = false }: { number: PhoneNumber; disabled?: boolean }) {
  const agents = useAgents(number.client_id ?? undefined, false, !!number.client_id);
  const update = useUpdateNumber();
  const data = (agents.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  // El agente actual puede estar archivado: se sigue mostrando.
  if (number.agent_id && !data.some((o) => o.value === number.agent_id)) {
    data.push({ value: number.agent_id, label: `${number.agent_name ?? 'Agente'} (archivado)` });
  }
  return (
    <Select
      size="xs"
      w={220}
      data={data}
      value={number.agent_id}
      placeholder="Ninguno (no atiende)"
      clearable
      searchable
      disabled={disabled || !number.client_id || update.isPending}
      aria-label={`Agente de ${number.e164}`}
      onChange={(agentId) =>
        agentId !== number.agent_id &&
        update.mutate(
          { id: number.id, body: { agent_id: agentId } },
          {
            onSuccess: (n) =>
              notifySuccess(
                n.agent_name ? `${n.e164} lo atiende ${n.agent_name}.` : `${n.e164} quedó sin agente.`,
              ),
            onError: (e) => notifyError(e, numberErrorTitle(e)),
          },
        )
      }
    />
  );
}
