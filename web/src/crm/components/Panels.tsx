import {
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useState } from 'react';
import { Link } from 'react-router';
import { EmptyState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAssignInbound, useCheckEvents, useIgnoreInbound, useLeads, usePatchActivity } from '../api';
import { fmtDate, fmtDateTime, todayIso } from '../format';
import { IntentBadge } from './Analysis';
import { StageBadge } from './Badges';
import { MessageModal } from './MessageModal';
import type { InboundEmail, Message, QueueStatus, ReplyRate, Today } from '../types';

// Tarjetas del Tablero: cola de envio, reply rate, tareas, respuestas y proximas acciones (antes en "Hoy").

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

export function QueueCard({ q }: { q: QueueStatus }) {
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

const pct = (r: ReplyRate) => `${Math.round(100 * r.rate)} %`;
const levelLabel = (step: number) => (step === 0 ? 'Primer mail' : `Seguimiento ${step}`);

export function ReplyRates({ rates }: { rates: ReplyRate[] }) {
  const [campaign, setCampaign] = useState<string | null>(null);
  const campaigns = [...new Set(rates.flatMap((r) => (r.campaign_slug ? [r.campaign_slug] : [])))].sort();
  const rows = rates.filter((r) => r.campaign_slug === campaign);
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Reply rate por nivel</Title>
        <Select
          size="xs"
          placeholder="Todas las campañas"
          aria-label="Campaña"
          data={campaigns}
          value={campaign}
          onChange={setCampaign}
          clearable
          w={220}
        />
      </Group>
      {rows.length === 0 ? (
        <EmptyState>Todavía no hay mails enviados.</EmptyState>
      ) : (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Nivel</Table.Th>
              <Table.Th ta="right">Alcanzados</Table.Th>
              <Table.Th ta="right">Respondieron</Table.Th>
              <Table.Th ta="right">Reply rate</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((r) => (
              <Table.Tr key={r.step}>
                <Table.Td>{levelLabel(r.step)}</Table.Td>
                <Table.Td ta="right" className="mono">
                  {r.reached}
                </Table.Td>
                <Table.Td ta="right" className="mono">
                  {r.replied}
                </Table.Td>
                <Table.Td ta="right" className="mono" fw={600}>
                  {pct(r)}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Text size="xs" c="dimmed" mt="xs">
        Respondió: mensaje entrante o etapa de respuesta en adelante (como en el Resumen). Cuenta para el
        último mail que recibió antes de responder. Los rebotados no cuentan como alcanzados.
      </Text>
    </Card>
  );
}

export function Tasks({ data }: { data: Today }) {
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

export function Replies({ data }: { data: Today }) {
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
                <Group gap={6} wrap="nowrap">
                  <Text size="sm" fw={600} truncate>
                    {m.lead_name}
                  </Text>
                  <IntentBadge m={m} />
                </Group>
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

export function NextActions({ data }: { data: Today }) {
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

/** Un recibido sin lead: se busca el lead y se asigna (se procesa como los automaticos), o se ignora. */
function InboxRow({ ib }: { ib: InboundEmail }) {
  const [search, setSearch] = useState('');
  const [q] = useDebouncedValue(search.trim(), 300);
  const [leadId, setLeadId] = useState<string | null>(null);
  const leads = useLeads({ q: q || undefined, limit: 20 });
  const assign = useAssignInbound();
  const ignore = useIgnoreInbound();
  return (
    <Stack gap={4}>
      <Group justify="space-between" wrap="nowrap">
        <Text size="sm" fw={600} truncate className="mono">
          {ib.from_addr}
        </Text>
        <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
          {fmtDateTime(ib.received_at)}
        </Text>
      </Group>
      <Text size="sm" truncate>
        {ib.subject || '(sin asunto)'}
      </Text>
      <Text size="xs" c="dimmed" lineClamp={2}>
        {ib.text}
      </Text>
      <Group gap="xs" align="flex-end">
        <Select
          size="xs"
          placeholder="Buscar el lead"
          aria-label="Lead"
          searchable
          searchValue={search}
          onSearchChange={setSearch}
          data={(leads.data?.items ?? []).map((l) => ({ value: String(l.id), label: l.name }))}
          value={leadId}
          onChange={setLeadId}
          nothingFoundMessage={q ? 'Ninguno' : 'Escribí para buscar'}
          w={240}
        />
        <Button
          size="compact-sm"
          disabled={!leadId}
          loading={assign.isPending}
          onClick={() =>
            assign.mutate(
              { id: ib.id, lead_id: Number(leadId) },
              { onSuccess: () => notifySuccess('Respuesta asignada.'), onError: (e) => notifyError(e) },
            )
          }
        >
          Asignar
        </Button>
        <Button
          size="compact-sm"
          variant="subtle"
          loading={ignore.isPending}
          onClick={() => ignore.mutate(ib.id, { onError: (e) => notifyError(e) })}
        >
          Ignorar
        </Button>
      </Group>
    </Stack>
  );
}

export function Inbox({ items }: { items: InboundEmail[] }) {
  if (!items.length) return null;
  return (
    <Card withBorder>
      <Title order={4} mb={0}>
        Respuestas sin asignar ({items.length})
      </Title>
      <Text size="xs" c="dimmed" mb="sm">
        Llegaron por mail y no se encontró el lead por el hilo, la dirección ni el dominio.
      </Text>
      <Stack gap="md">
        {items.map((ib) => (
          <InboxRow key={ib.id} ib={ib} />
        ))}
      </Stack>
    </Card>
  );
}
