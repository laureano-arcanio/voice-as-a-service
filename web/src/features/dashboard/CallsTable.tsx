import { Anchor, Badge, Button, Card, Group, Pagination, Select, Table, Text, Title } from '@mantine/core';
import { Link } from 'react-router';
import type { CallSummary } from '@/api/types';
import { CallStatusBadge, OriginBadge, OutcomeBadge, WorkflowBadge } from '@/components/Badges';
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

function text(v: unknown) {
  const s = formatValue(v);
  return (
    s || (
      <Text span inherit c="dimmed">
        –
      </Text>
    )
  );
}

export function CallsTable({
  items,
  total,
  error,
  loading,
  showClient,
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
          <Title order={4}>Llamadas</Title>
          <Badge variant="default">{total}</Badge>
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
          Todavía no hay conversaciones con estos filtros. Llamá al número del agente, lanzá una llamada
          arriba o usá el modo prueba.
        </EmptyState>
      ) : (
        <Table.ScrollContainer minWidth={1100}>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                {showClient && <Table.Th>Cliente</Table.Th>}
                <Table.Th>Agente</Table.Th>
                <Table.Th>Contacto</Table.Th>
                <Table.Th>Empresa</Table.Th>
                <Table.Th>Origen</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th>Duración</Table.Th>
                <Table.Th>Datos</Table.Th>
                <Table.Th>Workflow</Table.Th>
                <Table.Th>Resultado</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(c.created_at)}</Table.Td>
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
                      <Text span size="xs" c="dimmed">
                        {' '}
                        v{c.agent_version}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>{text(c.contact_name)}</Table.Td>
                  <Table.Td>{text(c.company)}</Table.Td>
                  <Table.Td>
                    <OriginBadge mode={c.mode} phone={c.phone} />
                  </Table.Td>
                  <Table.Td>
                    <CallStatusBadge status={c.status} />
                  </Table.Td>
                  <Table.Td>{formatDuration(c.duration_seconds)}</Table.Td>
                  <Table.Td>
                    {c.captured}/{c.required}
                  </Table.Td>
                  <Table.Td>
                    <WorkflowBadge status={c.workflow_status} />
                  </Table.Td>
                  <Table.Td>
                    <OutcomeBadge label={c.outcome} goal={c.goal} />
                  </Table.Td>
                  <Table.Td>
                    <Button component={Link} to={`/calls/${c.id}`} size="compact-xs" variant="light">
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
