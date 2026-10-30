import {
  Anchor,
  Avatar,
  Box,
  Button,
  Card,
  Group,
  List,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
  UnstyledButton,
} from '@mantine/core';
import {
  IconCircleCheckFilled,
  IconCircleDashed,
  IconMessages,
  IconMicrophone,
  IconPencil,
  IconPhoneCall,
  IconPlus,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import type { Agent, Onboarding } from '@/api/types';
import { OriginBadge, OutcomeBadge } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useAgents } from '@/features/agents/api';
import { useMe } from '@/features/auth/api';
import { useCalls } from '@/features/calls/api';
import { voiceName } from '@/features/voices/names';
import { formatDateTime, formatDuration } from '@/lib/format';
import { useOnboarding } from './api';
import { CallMeModal } from './CallMeModal';
import { portrait } from './catalog';
import { VoiceCallModal } from './VoiceCallModal';

type Action = { kind: 'talk' | 'call'; agent: Agent } | null;

function AgentCard({
  agent,
  fresh,
  status,
  onAction,
}: {
  agent: Agent;
  fresh: boolean;
  status: Onboarding | undefined;
  onAction: (a: Action) => void;
}) {
  const image = portrait(agent.voice);
  const name = voiceName(agent.voice ?? 'sofia');
  return (
    <Card className="onb-agent" data-fresh={fresh || undefined}>
      <Stack gap="md" h="100%">
        <Group wrap="nowrap" gap="md" align="center">
          <Avatar src={image} size={84} radius={999} color="blue" className="onb-agent-avatar">
            {name.charAt(0)}
          </Avatar>
          <Stack gap={2} style={{ minWidth: 0 }}>
            <Text fw={700} size="lg" truncate>
              {agent.name}
            </Text>
            <Text size="sm" c="dimmed">
              Voz de {name}
            </Text>
          </Stack>
        </Group>
        {agent.objective && (
          <Text size="sm" c="dimmed" lineClamp={3} style={{ flex: 1 }}>
            {agent.objective}
          </Text>
        )}
        <Stack gap="xs">
          <Button leftSection={<IconMicrophone size={18} />} onClick={() => onAction({ kind: 'talk', agent })}>
            Hablarle ahora
          </Button>
          <Group grow gap="xs">
            <Button
              variant="default"
              leftSection={<IconPhoneCall size={16} />}
              disabled={!status || agent.own_agent}
              onClick={() => onAction({ kind: 'call', agent })}
            >
              Llamame
            </Button>
            <Button
              variant="default"
              leftSection={<IconPencil size={16} />}
              component={Link}
              to={`/agents/${agent.id}?tab=conversacion`}
            >
              Editar
            </Button>
          </Group>
        </Stack>
      </Stack>
    </Card>
  );
}

function Step({ done, children }: { done: boolean; children: React.ReactNode }) {
  return (
    <List.Item
      icon={
        done ? (
          <IconCircleCheckFilled size={20} color="var(--mantine-color-green-6)" />
        ) : (
          <IconCircleDashed size={20} color="var(--mantine-color-gray-5)" />
        )
      }
    >
      <Text size="sm" td={done ? 'line-through' : undefined} c={done ? 'dimmed' : undefined}>
        {children}
      </Text>
    </List.Item>
  );
}

/**
 * Inicio del panel del cliente (docs/features/PRIMERA_VEZ.md): sus agentes con acceso directo a hablarles por
 * el navegador o que lo llamen al celular, los próximos pasos y las últimas conversaciones.
 */
export function HomePage() {
  const { data: me } = useMe();
  const [params] = useSearchParams();
  const fresh = params.get('nuevo');
  const navigate = useNavigate();
  const agents = useAgents(undefined, false);
  const status = useOnboarding(!me?.support).data;
  const calls = useCalls({ limit: 5, offset: 0 });
  const [action, setAction] = useState<Action>(null);
  const first = (me?.name || '').split(' ')[0];
  const callList = calls.data?.items ?? [];
  const tested = callList.some((c) => ['prueba', 'celular', 'web', 'entrante'].includes(c.mode));
  const edited = (agents.data ?? []).some((a) => a.version > 1);
  const shared = (agents.data ?? []).some((a) => a.call_link_url);
  const steps = [
    { done: (agents.data?.length ?? 0) > 0, text: 'Crear tu agente' },
    { done: tested, text: 'Hablarle por primera vez' },
    { done: edited, text: 'Cargarle la información de tu negocio (horarios, precios, preguntas frecuentes)' },
    { done: shared, text: 'Compartir su link para que te llamen desde la web' },
  ];
  const pending = steps.filter((s) => !s.done).length;

  return (
    <>
      <PageHeader
        title={first ? `Hola, ${first}` : 'Inicio'}
        docTitle="Inicio"
        description="Tus agentes, listos para probar. Hablales como si fueras un cliente."
      />
      <Stack gap="md">
        {fresh && (
          <Box className="onb-hero">
            <Text fw={700} size="lg">
              ¡Tu agente ya está listo!
            </Text>
            <Text size="sm">
              Hablale desde el navegador o pedile que te llame al celular. Después ajustás lo que dice con la
              información de tu negocio.
            </Text>
          </Box>
        )}
        <QueryState query={agents}>
          {(list) =>
            list.length === 0 ? (
              <Card>
                <EmptyState>Todavía no tenés agentes.</EmptyState>
              </Card>
            ) : (
              <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
                {list.map((a) => (
                  <AgentCard key={a.id} agent={a} fresh={a.id === fresh} status={status} onAction={setAction} />
                ))}
                <UnstyledButton className="onb-new-agent" onClick={() => void navigate('/agents?nuevo=1')}>
                  <Stack align="center" gap="xs">
                    <ThemeIcon size={48} radius="xl" variant="light">
                      <IconPlus size={24} />
                    </ThemeIcon>
                    <Text fw={600}>Crear otro agente</Text>
                    <Text size="sm" c="dimmed" ta="center">
                      Para otro rubro, otra línea o una campaña.
                    </Text>
                  </Stack>
                </UnstyledButton>
              </SimpleGrid>
            )
          }
        </QueryState>
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Card>
            <Group justify="space-between" mb="sm">
              <Title order={4}>Próximos pasos</Title>
              <Text size="sm" c="dimmed">
                {pending === 0 ? 'Todo listo' : `Te ${pending === 1 ? 'falta 1' : `faltan ${pending}`}`}
              </Text>
            </Group>
            <List spacing="sm" center>
              {steps.map((s) => (
                <Step key={s.text} done={s.done}>
                  {s.text}
                </Step>
              ))}
            </List>
          </Card>
          <Card>
            <Group justify="space-between" mb="sm">
              <Title order={4}>Últimas conversaciones</Title>
              <Anchor component={Link} to="/calls" size="sm">
                Ver todas
              </Anchor>
            </Group>
            {callList.length === 0 ? (
              <Group gap="xs" c="dimmed">
                <IconMessages size={18} />
                <Text size="sm">Cuando le hables a tu agente, la conversación aparece acá.</Text>
              </Group>
            ) : (
              <Stack gap={0}>
                {callList.map((c) => (
                  <UnstyledButton key={c.id} className="onb-call-row" component={Link} to={`/calls/${c.id}`}>
                    <Group justify="space-between" wrap="nowrap" gap="sm">
                      <Stack gap={2} style={{ minWidth: 0 }}>
                        <Text size="sm" fw={600} truncate>
                          {c.agent_name ?? 'Agente'}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {formatDateTime(c.created_at)} · {formatDuration(c.duration_seconds)}
                        </Text>
                      </Stack>
                      <Group gap={6} wrap="nowrap">
                        <OriginBadge mode={c.mode} />
                        {c.outcome && <OutcomeBadge label={c.outcome} goal={c.goal} />}
                      </Group>
                    </Group>
                  </UnstyledButton>
                ))}
              </Stack>
            )}
          </Card>
        </SimpleGrid>
      </Stack>
      {action?.kind === 'talk' && <VoiceCallModal agent={action.agent} opened onClose={() => setAction(null)} />}
      {action?.kind === 'call' && status && (
        <CallMeModal agent={action.agent} status={status} opened onClose={() => setAction(null)} />
      )}
    </>
  );
}
