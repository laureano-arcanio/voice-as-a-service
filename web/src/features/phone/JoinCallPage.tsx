import { Alert, Anchor, Button, Card, Group, Stack, Text, Tooltip } from '@mantine/core';
import { IconPhone } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { Dash } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { useCallDetail } from '@/features/calls/api';
import { isLiveStatus } from '@/lib/labels';
import { type JoinOutcome, useDirectCall } from './context';

// Errores que no se arreglan reintentando.
const FINAL = ['not_your_call', 'call_not_active', 'not_found', 'support_read_only'];

/**
 * Entra a una llamada directa creada por la API o el MCP (`join_url`): pide el token (/join) y la llamada
 * sigue en la barra de abajo. Entra con un clic, así el navegador deja usar el micrófono y el audio.
 */
export function JoinCallPage() {
  const { id = '' } = useParams();
  const c = useDirectCall();
  const detail = useCallDetail(id);
  const [joining, setJoining] = useState(false);
  const [outcome, setOutcome] = useState<JoinOutcome | null>(null);

  const info = detail.data?.call;
  const inThisCall = c.busy && c.conversationId === id;
  const ended = (info && !isLiveStatus(info.status)) || outcome?.code === 'call_not_active';
  const problem = outcome && !outcome.ok ? outcome.problem : null;

  const enter = async () => {
    setJoining(true);
    setOutcome(await c.join(id));
    setJoining(false);
  };

  return (
    <Stack gap="md">
      <PageHeader
        title="Llamada"
        description="Una llamada que pediste desde la API o tu agente de IA: entrás y hablás desde el navegador."
        above={
          <Anchor component={Link} to="/telefono" size="sm">
            ← Teléfono del equipo
          </Anchor>
        }
      />
      <PlanGate feature="direct_calls" what="llamadas directas">
        <Card maw={720}>
          <Stack gap="md">
            <Group gap="xl">
              <Stack gap={2}>
                <Text size="xs" c="dimmed">
                  A
                </Text>
                <Text size="sm" fw={600} className="mono">
                  {info?.phone ?? <Dash />}
                </Text>
              </Stack>
              <Stack gap={2}>
                <Text size="xs" c="dimmed">
                  Desde
                </Text>
                <Text size="sm" fw={600} className="mono">
                  {info?.client_number ?? <Dash />}
                </Text>
              </Stack>
            </Group>
            {inThisCall ? (
              <Alert color="blue" p="xs">
                <Text size="sm">Estás en la llamada: la seguís en la barra de abajo.</Text>
              </Alert>
            ) : ended ? (
              <Alert color="gray" title="La llamada terminó">
                <Text size="sm">
                  La conversación queda en el{' '}
                  <Anchor component={Link} to={`/calls/${id}`} inherit>
                    detalle de la llamada
                  </Anchor>
                  .
                </Text>
              </Alert>
            ) : (
              <>
                {problem && (
                  <Alert color="red" title={problem.title}>
                    <Text size="sm">{problem.message}</Text>
                  </Alert>
                )}
                {!(problem?.code && FINAL.includes(problem.code)) && (
                  <Stack gap={6} align="flex-start">
                    <Tooltip
                      label={c.disabledReason ?? 'Ya estás en otra llamada: cortala para entrar a esta.'}
                      disabled={!c.disabledReason && !c.busy}
                      withArrow
                    >
                      <Button
                        leftSection={<IconPhone size={18} />}
                        loading={joining}
                        data-disabled={!!c.disabledReason || c.busy || undefined}
                        onClick={(e) => {
                          if (c.disabledReason || c.busy) return e.preventDefault();
                          void enter();
                        }}
                      >
                        {problem ? 'Volver a intentar' : 'Entrar a la llamada'}
                      </Button>
                    </Tooltip>
                    <Text size="xs" c="dimmed">
                      El navegador te va a pedir el micrófono. Usá auriculares: así no vuelve tu voz como eco.
                    </Text>
                  </Stack>
                )}
              </>
            )}
          </Stack>
        </Card>
      </PlanGate>
    </Stack>
  );
}
