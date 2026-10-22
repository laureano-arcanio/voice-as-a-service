import { Anchor, Badge, Card, Group, Pagination, Select, Table, Text } from '@mantine/core';
import { useState } from 'react';
import { Link } from 'react-router';
import { EmptyState, QueryState } from '@/components/QueryState';
import { MESSAGES_PAGE, useCampaigns, useMessages } from '../api';
import { MESSAGE_KIND_OPTIONS, MESSAGE_STATUS_OPTIONS, fmtDateTime, messageLabel } from '../format';
import type { Message } from '../types';
import { MessageStatusBadge } from './Badges';
import { MessageModal } from './MessageModal';

/** Mensajes con filtros por estado, direccion, tipo y (si no viene fija) campaña. */
export function MessagesTable({ campaignId }: { campaignId?: number }) {
  const [status, setStatus] = useState<string | null>(null);
  const [direction, setDirection] = useState<string | null>(null);
  const [kind, setKind] = useState<string | null>(null);
  const [campaign, setCampaign] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<Message | null>(null);
  const campaigns = useCampaigns();
  const msgs = useMessages({
    status,
    direction,
    kind,
    campaign_id: campaignId ?? (campaign ? Number(campaign) : null),
    limit: MESSAGES_PAGE,
    offset: (page - 1) * MESSAGES_PAGE,
  });
  const reset = (set: (v: string | null) => void) => (v: string | null) => {
    set(v);
    setPage(1);
  };
  const total = msgs.data?.total ?? 0;

  return (
    <>
      <Group gap="sm" mb="sm" align="flex-end">
        <Select
          label="Estado"
          data={MESSAGE_STATUS_OPTIONS}
          value={status}
          onChange={reset(setStatus)}
          clearable
          w={150}
          placeholder="Todos"
        />
        <Select
          label="Dirección"
          data={[
            { value: 'out', label: 'Enviados' },
            { value: 'in', label: 'Recibidos' },
          ]}
          value={direction}
          onChange={reset(setDirection)}
          clearable
          w={140}
          placeholder="Todos"
        />
        <Select
          label="Tipo"
          data={MESSAGE_KIND_OPTIONS}
          value={kind}
          onChange={reset(setKind)}
          clearable
          w={150}
          placeholder="Todos"
        />
        {campaignId === undefined && (
          <Select
            label="Campaña"
            data={(campaigns.data ?? []).map((c) => ({ value: String(c.id), label: c.slug }))}
            value={campaign}
            onChange={reset(setCampaign)}
            clearable
            searchable
            w={180}
            placeholder="Todas"
          />
        )}
        {msgs.data && (
          <Text size="sm" c="dimmed" ml="auto">
            {total} mensajes
          </Text>
        )}
      </Group>
      <Card withBorder p={0}>
        <QueryState query={msgs}>
          {(data) =>
            data.items.length === 0 ? (
              <EmptyState>No hay mensajes con estos filtros.</EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={900}>
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th pl="md">Fecha</Table.Th>
                      <Table.Th>Lead</Table.Th>
                      <Table.Th>Tipo</Table.Th>
                      <Table.Th>Dirección</Table.Th>
                      <Table.Th>Asunto</Table.Th>
                      <Table.Th>Campaña</Table.Th>
                      <Table.Th>Estado</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.items.map((m) => (
                      <Table.Tr key={m.id} style={{ cursor: 'pointer' }} onClick={() => setOpen(m)}>
                        <Table.Td pl="md" style={{ whiteSpace: 'nowrap' }}>
                          {fmtDateTime(m.sent_at ?? m.queued_at ?? m.created_at)}
                        </Table.Td>
                        <Table.Td onClick={(e) => e.stopPropagation()}>
                          <Anchor component={Link} to={`/leads/${m.lead_id}`} size="sm">
                            {m.lead_name ?? `#${m.lead_id}`}
                          </Anchor>
                        </Table.Td>
                        <Table.Td>
                          <Badge color="gray">{messageLabel(m)}</Badge>
                        </Table.Td>
                        <Table.Td className="mono">
                          {m.direction === 'in' ? `de ${m.from_addr}` : `a ${m.to_addr}`}
                        </Table.Td>
                        <Table.Td maw={320}>
                          <Text size="sm" lineClamp={1}>
                            {m.subject}
                          </Text>
                        </Table.Td>
                        <Table.Td className="mono">{m.campaign_slug ?? '–'}</Table.Td>
                        <Table.Td>
                          <MessageStatusBadge status={m.status} error={m.error} />
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      {total > MESSAGES_PAGE && (
        <Group justify="center" mt="md">
          <Pagination total={Math.ceil(total / MESSAGES_PAGE)} value={page} onChange={setPage} />
        </Group>
      )}
      <MessageModal message={open} onClose={() => setOpen(null)} />
    </>
  );
}
