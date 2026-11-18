import { Badge, Group, SegmentedControl, Stack, Text, Tooltip } from '@mantine/core';
import { useState } from 'react';
import type { PhoneNumber } from '@/api/types';
import { Dash } from '@/components/Badges';
import { useFeatureLock } from '@/features/billing/features';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateNumber } from './api';
import { NumberAgentSelect } from './AgentSelect';
import {
  type AnswerMode,
  numberMembers,
  RING_FIRST_OPTIONS,
  retrySummary,
  teamWithoutPeople,
} from './answering';
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
  const [startInSplit, setStartInSplit] = useState(false);
  if (!n.client_id) return <Dash />;
  const choice = n.answer_mode === 'agent' ? 'agent' : n.agent_percent > 0 ? 'split' : 'team';

  // Con el plan sin llamadas directas no se puede elegir el equipo (si ya lo tenía, se puede pasar al agente).
  const teamLocked = lock.locked && n.answer_mode !== 'team';

  const change = (next: string) => {
    if (next === choice) return;
    if (next === 'split') {
      // El agente, el porcentaje y el tope se eligen en el editor.
      setStartInSplit(true);
      return;
    }
    if (next === 'team' && numberMembers(n).length === 0) {
      setChoosingTeam(true);
      return;
    }
    // Pasar a Equipo apaga un reparto que ya estaba andando.
    const body =
      next === 'team' && n.agent_percent > 0
        ? { answer_mode: 'team' as AnswerMode, agent_percent: 0 }
        : { answer_mode: next as AnswerMode };
    update.mutate(
      { id: n.id, body },
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
        value={choice}
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
          {
            value: 'split',
            label: teamLocked ? (
              <Tooltip label="Tu plan no incluye que atienda el equipo">
                <span>Agente y equipo</span>
              </Tooltip>
            ) : (
              'Agente y equipo'
            ),
            disabled: teamLocked,
          },
        ]}
      />
      {n.answer_mode === 'agent' ? <NumberAgentSelect number={n} /> : <TeamSummary number={n} />}
      {n.record_full_call && (
        <Text size="xs" c="dimmed">
          Graba la llamada completa
        </Text>
      )}
      {choosingTeam && (
        <EditNumberModal key={n.id} number={n} startInTeam onClose={() => setChoosingTeam(false)} />
      )}
      {startInSplit && (
        <EditNumberModal key={`${n.id}-split`} number={n} startInSplit onClose={() => setStartInSplit(false)} />
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
      {n.agent_percent > 0 && (
        <Text size="xs">
          {n.agent_percent} % al agente
          {n.split_max_agent_calls ? ` · tope ${n.split_max_agent_calls} a la vez` : ''}
        </Text>
      )}
      <Text size="xs" c="dimmed">
        Suena primero {first}
        {n.strategy === 'round_robin' ? ' · rotativa' : ''}
        {n.team_connect_on_answer ? ' · conecta al atender' : ''}
        {n.team_hold_music ? '' : ' · sin música'}
        {retrySummary(n)}
        {n.schedule ? ' · con horario' : ''}
      </Text>
    </Stack>
  );
}
