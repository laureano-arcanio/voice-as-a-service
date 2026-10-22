import {
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { Link } from 'react-router';
import { Dash } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useApprove, useCheckEvents, usePatchActivity, useToday } from '../api';
import { fmtAgo, fmtDate, fmtDateTime, messageLabel, todayIso } from '../format';
import { BulkDraftsModal } from '../components/BulkDraftsModal';
import { StageBadge } from '../components/Badges';
import { MessageModal } from '../components/MessageModal';
import type { Message, QueueStatus, Today } from '../types';

function toggleIn(set: Set<number>, id: number): Set<number> {
  const next = new Set(set);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}

function EventsButton({ q }: { q: QueueStatus }) {
  const check = useCheckEvents();
  const last = q.events_last;
  return (
    <Group gap="xs" wrap="nowrap">
      <Text size="xs" c="dimmed" visibleFrom="sm">
        {q.events_running
          ? 'Revisando en Resend…'
          : last.at
            ? `Entregas revisadas ${fmtDateTime(last.at)}${last.changed ? ` (${last.changed} cambios)` : ''}`
            : ''}
      </Text>
      <Button
        size="compact-sm"
        variant="default"
        loading={check.isPending || q.events_running}
        onClick={() =>
          check.mutate(undefined, {
            onSuccess: () => notifySuccess('Revisando entregas y rebotes en Resend.'),
            onError: (e) => notifyError(e),
          })
        }
      >
        Revisar entregas y rebotes
      </Button>
    </Group>
  );
}

function QueueCard({ q }: { q: QueueStatus }) {
  const next = q.next_at ? new Date(q.next_at) : null;
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Group gap="xs">
          <Title order={4}>Cola de envío</Title>
          {q.enabled ? (
            <Badge color={q.in_hours ? 'green' : 'gray'}>
              {q.in_hours ? 'En horario' : 'Fuera de horario'}
            </Badge>
          ) : (
            <Badge color="yellow">Apagada</Badge>
          )}
        </Group>
        <EventsButton q={q} />
      </Group>
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <Stack gap={0}>
          <Text className="label">En cola</Text>
          <Text className="metric">{q.queued}</Text>
        </Stack>
        <Stack gap={0}>
          <Text className="label">Enviados hoy</Text>
          <Text className="metric">
            {q.sent_today}
            <Text span c="dimmed" size="sm">
              {' '}
              / {q.daily_max}
            </Text>
          </Text>
        </Stack>
        <Stack gap={0}>
          <Text className="label">Horario</Text>
          <Text size="sm" fw={600}>
            {q.hours} h, lun a vie
          </Text>
          <Text size="xs" c="dimmed">
            uno cada ~{Math.round(q.window_seconds / 60)} min
          </Text>
        </Stack>
        <Stack gap={0}>
          <Text className="label">Próximo envío</Text>
          <Text size="sm" fw={600}>
            {q.queued && next && next > new Date()
              ? next.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
              : q.queued
                ? 'en cuanto toque'
                : '–'}
          </Text>
        </Stack>
      </SimpleGrid>
    </Card>
  );
}

function FollowUps({ data }: { data: Today }) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [open, setOpen] = useState(false);
  const due = data.follow_ups_due;
  const all = due.length > 0 && due.every((d) => selected.has(d.lead.id));
  const names = Object.fromEntries(due.map((d) => [d.lead.id, d.lead.name]));

  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Seguimientos que vencen ({due.length})</Title>
        <Button size="compact-sm" disabled={selected.size === 0} onClick={() => setOpen(true)}>
          Armar seguimientos ({selected.size})
        </Button>
      </Group>
      {due.length === 0 ? (
        <EmptyState>Nadie espera seguimiento hoy.</EmptyState>
      ) : (
        <Table.ScrollContainer minWidth={640}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={36}>
                  <Checkbox
                    aria-label="Todos"
                    checked={all}
                    indeterminate={selected.size > 0 && !all}
                    onChange={() => setSelected(all ? new Set() : new Set(due.map((d) => d.lead.id)))}
                  />
                </Table.Th>
                <Table.Th>Lead</Table.Th>
                <Table.Th>Campaña</Table.Th>
                <Table.Th>Toca</Table.Th>
                <Table.Th>Último mail</Table.Th>
                <Table.Th ta="right">Días hábiles</Table.Th>
                <Table.Th ta="right">Clics</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {due.map((d) => (
                <Table.Tr key={d.lead.id}>
                  <Table.Td>
                    <Checkbox
                      aria-label={`Elegir ${d.lead.name}`}
                      checked={selected.has(d.lead.id)}
                      onChange={() => setSelected((s) => toggleIn(s, d.lead.id))}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Anchor component={Link} to={`/leads/${d.lead.id}`} size="sm">
                      {d.lead.name}
                    </Anchor>
                    <Text size="xs" c="dimmed" className="mono">
                      {d.lead.primary_email ?? '–'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" className="mono">
                      {d.campaign_slug ?? '–'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">Seguimiento {d.step}</Text>
                    <Text size="xs" c="dimmed">
                      {d.template_id ? 'con plantilla' : 'elegir plantilla'}
                    </Text>
                  </Table.Td>
                  <Table.Td>{fmtDate(d.sent_at)}</Table.Td>
                  <Table.Td ta="right" className="mono">
                    {d.business_days}
                  </Table.Td>
                  <Table.Td ta="right" className="mono">
                    {d.lead.ga_users || <Dash />}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
      <BulkDraftsModal
        opened={open}
        onClose={(done) => {
          setOpen(false);
          if (done) setSelected(new Set());
        }}
        leadIds={[...selected]}
        followUps
        names={names}
      />
    </Card>
  );
}

function Drafts({ drafts }: { drafts: Message[] }) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [open, setOpen] = useState<Message | null>(null);
  const approve = useApprove();
  const all = drafts.length > 0 && drafts.every((m) => selected.has(m.id));

  const approveSelected = () =>
    approve.mutate([...selected], {
      onSuccess: (r) => {
        notifySuccess(`${r.length} aprobados: salen por la cola.`);
        setSelected(new Set());
      },
      onError: (e) => notifyError(e, 'No se pudo aprobar'),
    });

  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Borradores para aprobar ({drafts.length})</Title>
        <Button
          size="compact-sm"
          disabled={selected.size === 0}
          loading={approve.isPending}
          onClick={approveSelected}
        >
          Aprobar ({selected.size})
        </Button>
      </Group>
      {drafts.length === 0 ? (
        <EmptyState>No hay borradores.</EmptyState>
      ) : (
        <Table.ScrollContainer minWidth={640}>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={36}>
                  <Checkbox
                    aria-label="Todos"
                    checked={all}
                    indeterminate={selected.size > 0 && !all}
                    onChange={() => setSelected(all ? new Set() : new Set(drafts.map((m) => m.id)))}
                  />
                </Table.Th>
                <Table.Th>Lead</Table.Th>
                <Table.Th>Tipo</Table.Th>
                <Table.Th>Para</Table.Th>
                <Table.Th>Asunto</Table.Th>
                <Table.Th>Creado</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {drafts.map((m) => (
                <Table.Tr key={m.id} style={{ cursor: 'pointer' }} onClick={() => setOpen(m)}>
                  <Table.Td onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      aria-label={`Elegir ${m.lead_name ?? m.id}`}
                      checked={selected.has(m.id)}
                      onChange={() => setSelected((s) => toggleIn(s, m.id))}
                    />
                  </Table.Td>
                  <Table.Td>{m.lead_name}</Table.Td>
                  <Table.Td>
                    <Badge color="gray">{messageLabel(m)}</Badge>
                  </Table.Td>
                  <Table.Td className="mono">{m.to_addr}</Table.Td>
                  <Table.Td>
                    <Text size="sm" lineClamp={1}>
                      {m.subject}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {fmtAgo(m.created_at)} · {m.created_by}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
      <MessageModal message={open} onClose={() => setOpen(null)} />
    </Card>
  );
}

function Tasks({ data }: { data: Today }) {
  const patch = usePatchActivity();
  const today = todayIso();
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Tareas ({data.tasks.length})
      </Title>
      {data.tasks.length === 0 ? (
        <EmptyState>Sin tareas abiertas.</EmptyState>
      ) : (
        <Stack gap="xs">
          {data.tasks.map((t) => (
            <Group key={t.id} justify="space-between" wrap="nowrap" align="flex-start">
              <Checkbox
                label={
                  <Text size="sm">
                    <Anchor component={Link} to={`/leads/${t.lead_id}`} size="sm">
                      #{t.lead_id}
                    </Anchor>{' '}
                    {t.text}
                  </Text>
                }
                checked={false}
                onChange={() =>
                  patch.mutate(
                    { id: t.id, done: true },
                    { onSuccess: () => notifySuccess('Tarea hecha.'), onError: (e) => notifyError(e) },
                  )
                }
              />
              <Text
                size="xs"
                c={t.due_at && t.due_at < today ? 'red' : 'dimmed'}
                style={{ whiteSpace: 'nowrap' }}
              >
                {fmtDate(t.due_at)}
              </Text>
            </Group>
          ))}
        </Stack>
      )}
    </Card>
  );
}

function Replies({ data }: { data: Today }) {
  const [open, setOpen] = useState<Message | null>(null);
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Respuestas de la semana ({data.replies.length})
      </Title>
      {data.replies.length === 0 ? (
        <EmptyState>Ninguna respuesta en los últimos 7 días.</EmptyState>
      ) : (
        <Stack gap="xs">
          {data.replies.map((m) => (
            <Group
              key={m.id}
              justify="space-between"
              wrap="nowrap"
              style={{ cursor: 'pointer' }}
              onClick={() => setOpen(m)}
            >
              <Stack gap={0} style={{ minWidth: 0 }}>
                <Text size="sm" fw={600} truncate>
                  {m.lead_name}
                </Text>
                <Text size="xs" c="dimmed" truncate>
                  {m.subject}
                </Text>
              </Stack>
              <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                {fmtDateTime(m.sent_at)}
              </Text>
            </Group>
          ))}
        </Stack>
      )}
      <MessageModal message={open} onClose={() => setOpen(null)} />
    </Card>
  );
}

function NextActions({ data }: { data: Today }) {
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Próximas acciones vencidas ({data.next_actions.length})
      </Title>
      {data.next_actions.length === 0 ? (
        <EmptyState>Nada vencido.</EmptyState>
      ) : (
        <Stack gap="xs">
          {data.next_actions.map((l) => (
            <Group key={l.id} justify="space-between" wrap="nowrap" align="flex-start">
              <Stack gap={0} style={{ minWidth: 0 }}>
                <Group gap={6} wrap="nowrap">
                  <Anchor component={Link} to={`/leads/${l.id}`} size="sm" fw={600}>
                    {l.name}
                  </Anchor>
                  <StageBadge stage={l.stage} />
                </Group>
                <Text size="xs" c="dimmed" lineClamp={2}>
                  {l.next_action}
                </Text>
              </Stack>
              <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                {fmtDate(l.next_action_at)}
              </Text>
            </Group>
          ))}
        </Stack>
      )}
    </Card>
  );
}

export function TodayPage() {
  const today = useToday();
  return (
    <>
      <PageHeader
        title="Hoy"
        description="Seguimientos que vencen, borradores para aprobar, tareas y respuestas."
      />
      <QueryState query={today}>
        {(data) => (
          <Stack gap="md">
            <QueueCard q={data.queue} />
            <FollowUps data={data} />
            <Drafts drafts={data.drafts} />
            <SimpleGrid cols={{ base: 1, md: 3 }}>
              <Tasks data={data} />
              <Replies data={data} />
              <NextActions data={data} />
            </SimpleGrid>
          </Stack>
        )}
      </QueryState>
    </>
  );
}
