import { Badge, Group, Stack, Text } from '@mantine/core';
import type { PhoneNumber } from '@/api/types';
import { Dash } from '@/components/Badges';
import { NumberAgentSelect } from './AgentSelect';
import { numberMembers, RING_FIRST_OPTIONS, teamWithoutPeople } from './answering';

/**
 * Quién atiende las entrantes de un número: el agente (editable en la fila) o el equipo, con sus personas.
 * Un número del equipo sin personas dice qué pasa con las llamadas: las atiende el agente o nadie.
 */
export function NumberAnswers({ number: n }: { number: PhoneNumber }) {
  if (!n.client_id) return <Dash />;
  if (n.answer_mode === 'agent') return <NumberAgentSelect number={n} />;

  if (teamWithoutPeople(n)) {
    return (
      <Stack gap={2}>
        <Group gap={6} wrap="nowrap">
          <Badge color="yellow">Equipo sin personas</Badge>
        </Group>
        <Text size="xs" c="dimmed">
          {n.agent_id
            ? `Sin personas: atiende el agente ${n.agent_name ?? ''}`.trim()
            : 'Sin personas: no atiende nadie'}
        </Text>
      </Stack>
    );
  }

  const names = numberMembers(n).map((m) => m.name);
  const first = RING_FIRST_OPTIONS.find((o) => o.value === n.ring_first)?.label.toLowerCase();
  return (
    <Stack gap={2}>
      <Group gap={6} wrap="nowrap">
        <Badge color="blue">Equipo</Badge>
        <Text size="sm" lineClamp={2}>
          {names.join(', ')}
        </Text>
      </Group>
      <Text size="xs" c="dimmed">
        Suena primero {first}
        {n.schedule ? ' · con horario' : ''}
      </Text>
    </Stack>
  );
}
