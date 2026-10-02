import { Anchor, Badge, Button, Card, Group, Pagination, Select, Table, Text, Title } from '@mantine/core';
import { Link } from 'react-router';
import type { CallSummary } from '@/api/types';
import { CallStatusBadge, Dash, OriginBadge, OutcomeBadge, WorkflowBadge } from '@/components/Badges';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { formatDateTime, formatDuration, formatValue } from '@/lib/format';
import { CALL_MODE, CALL_STATUS } from '@/lib/labels';

export const PAGE_SIZE = 25;

const STATUS_OPTIONS = [
  { value: '', label: 'Todos los estados' },
  ...Object.entries(CALL_STATUS).map(([value, l]) => ({ value, label: l.label })),
];
const MODE_OPTIONS = [
  { value: '', label: 'Todos los orígenes' },
  ...Object.entries(CALL_MODE).map(([value, l]) => ({ value, label: l.label })),
];

export function CallsTable({
  items,
  total,
  error,
  loading,
  showClient,
  showWorkflow,
  page,
  status,
  mode,
  onPage,
  onStatus,
  onMode,
}: {
  items: CallSummary[];
  total: number;
  error: unknown;
  loading: boolean;
  showClient: boolean;
  /** El estado del workflow es vocabulario interno: solo admin. */
  showWorkflow: boolean;
  page: number;
  status: string | null;
  mode: string | null;
  onPage: (p: number) => void;
  onStatus: (s: string | null) => void;
  onMode: (m: string | null) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <Card>
      <Group justify="space-between" mb="sm" wrap="wrap">
        <Group gap="xs">
          <Title order={4}>Conversaciones</Title>
          <Badge color="gray">{total}</Badge>
        </Group>
        <Group gap="xs">
          <Select
            size="xs"
            data={STATUS_OPTIONS}
            value={status ?? ''}
            onChange={(v) => onStatus(v || null)}
            allowDeselect={false}
            w={170}
            aria-label="Estado"
          />
          <Select
            size="xs"
            data={MODE_OPTIONS}
            value={mode ?? ''}
            onChange={(v) => onMode(v || null)}
            allowDeselect={false}
            w={170}
            aria-label="Origen"
          />
        </Group>
      </Group>
      {error ? (
        <ErrorAlert error={error} />
      ) : !loading && items.length === 0 ? (
        <EmptyState>
          Todavía no hay conversaciones con estos filtros. Llamá o escribí por WhatsApp al número del agente,
          lanzá una llamada arriba o usá el modo prueba.
        </EmptyState>
      ) : (
        <Table.ScrollContainer minWidth={1000}>
          <Table style={{ whiteSpace: 'nowrap' }}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                {showClient && <Table.Th>Cliente</Table.Th>}
                <Table.Th>Agente</Table.Th>
                <Table.Th>Contacto</Table.Th>
                <Table.Th>Origen</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th ta="right">Duración</Table.Th>
                <Table.Th ta="right">Datos</Table.Th>
                {showWorkflow && <Table.Th>Workflow</Table.Th>}
                <Table.Th>Resultado</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td>{formatDateTime(c.created_at)}</Table.Td>
                  {showClient && <Table.Td>{c.client_name ?? '–'}</Table.Td>}
                  <Table.Td>
                    {c.agent_id ? (
                      <Anchor component={Link} to={`/agents/${c.agent_id}`} size="sm">
                        {c.agent_name ?? 'Agente'}
                      </Anchor>
                    ) : (
                      (c.agent_name ?? '–')
                    )}
                    {c.agent_version != null && (
                      <Text span c="dimmed" className="mono">
                        {' '}
                        v{c.agent_version}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {formatValue(c.contact_name) || <Dash />}
                    {formatValue(c.company) && (
                      <Text size="xs" c="dimmed">
                        {formatValue(c.company)}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <OriginBadge mode={c.mode} phone={c.phone} />
                  </Table.Td>
                  <Table.Td>
                    <CallStatusBadge status={c.status} />
                  </Table.Td>
                  <Table.Td ta="right" className="mono">
                    {formatDuration(c.duration_seconds)}
                  </Table.Td>
                  <Table.Td ta="right" className="mono">
                    {c.captured}/{c.required}
                  </Table.Td>
                  {showWorkflow && (
                    <Table.Td>
                      <WorkflowBadge status={c.workflow_status} />
                    </Table.Td>
                  )}
                  <Table.Td>
                    <OutcomeBadge label={c.outcome} goal={c.goal} />
                  </Table.Td>
                  <Table.Td ta="right">
                    <Button component={Link} to={`/calls/${c.id}`} variant="subtle" size="compact-sm">
                      Ver detalle
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
      {pages > 1 && (
        <Group justify="flex-end" mt="sm">
          <Pagination total={pages} value={Math.min(page, pages)} onChange={onPage} size="sm" />
        </Group>
      )}
    </Card>
  );
}
