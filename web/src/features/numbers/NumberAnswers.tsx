import { Badge, Group, SegmentedControl, Stack, Text, Tooltip } from '@mantine/core';
import { useState } from 'react';
import type { PhoneNumber } from '@/api/types';
import { Dash } from '@/components/Badges';
import { useFeatureLock } from '@/features/billing/features';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateNumber } from './api';
import { NumberAgentSelect } from './AgentSelect';
import { numberMembers, RING_FIRST_OPTIONS, teamWithoutPeople, type AnswerMode } from './answering';
import { EditNumberModal } from './EditNumberModal';
import { numberErrorTitle } from './errors';

/**
 * Quién atiende las entrantes de un número, con un toggle Agente / Equipo en la fila. Con Agente, el
 * desplegable con los agentes del cliente; con Equipo, sus personas. Pasar a Equipo sin personas abre el editor
 * para elegirlas (la API pide al menos una). Un número del equipo sin personas dice qué pasa con las llamadas:
 * las atiende el agente o nadie.
 */
export function NumberAnswers({ number: n }: { number: PhoneNumber }) {
  const update = useUpdateNumber();
  const lock = useFeatureLock('direct_calls');
  const [choosingTeam, setChoosingTeam] = useState(false);
  if (!n.client_id) return <Dash />;

  // Con el plan sin llamadas directas no se puede elegir el equipo (si ya lo tenía, se puede pasar al agente).
  const teamLocked = lock.locked && n.answer_mode !== 'team';

  const change = (mode: string) => {
    if (mode === n.answer_mode) return;
    if (mode === 'team' && numberMembers(n).length === 0) {
      setChoosingTeam(true);
      return;
    }
    update.mutate(
      { id: n.id, body: { answer_mode: mode as AnswerMode } },
      {
        onSuccess: (u) =>
          notifySuccess(
            u.answer_mode === 'team' ? `${u.e164} lo atiende el equipo.` : `${u.e164} lo atiende un agente.`,
          ),
        onError: (e) => notifyError(e, numberErrorTitle(e)),
      },
    );
  };

  return (
    <Stack gap={6} align="flex-start">
      <SegmentedControl
        size="xs"
        value={n.answer_mode}
        onChange={change}
        disabled={update.isPending}
        aria-label={`Quién atiende ${n.e164}`}
        data={[
          { value: 'agent', label: 'Agente' },
          {
            value: 'team',
            label: teamLocked ? (
              <Tooltip label="Tu plan no incluye que atienda el equipo">
                <span>Equipo</span>
              </Tooltip>
            ) : (
              'Equipo'
            ),
            disabled: teamLocked,
          },
        ]}
      />
      {n.answer_mode === 'agent' ? <NumberAgentSelect number={n} /> : <TeamSummary number={n} />}
      {choosingTeam && (
        <EditNumberModal key={n.id} number={n} startInTeam onClose={() => setChoosingTeam(false)} />
      )}
    </Stack>
  );
}

function TeamSummary({ number: n }: { number: PhoneNumber }) {
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
      <Text size="sm" lineClamp={2}>
        {names.join(', ')}
      </Text>
      <Text size="xs" c="dimmed">
        Suena primero {first}
        {n.schedule ? ' · con horario' : ''}
      </Text>
    </Stack>
  );
}
