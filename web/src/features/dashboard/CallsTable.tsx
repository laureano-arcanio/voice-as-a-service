import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Pagination,
  Select,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { CallSummary } from '@/api/types';
import { CallStatusBadge, Dash, OriginBadge, OutcomeBadge, WorkflowBadge } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { useDeleteConversations } from '@/features/calls/api';
import { formatDateTime, formatDuration, formatValue } from '@/lib/format';
import { CALL_MODE, CALL_STATUS, isLiveStatus } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';

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
  selectable = false,
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
  /** Seleccion en bulk y borrado (estilo Gmail): solo admin. */
  selectable?: boolean;
}) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const del = useDeleteConversations();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const pageIds = items.map((c) => c.id);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id));
  const somePageSelected = !allPageSelected && pageIds.some((id) => selected.has(id));

  const toggle = (id: string, checked: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });

  const togglePage = (checked: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      for (const id of pageIds) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });

  const remove = async (ids: string[]) => {
    const ok = await confirmAction({
      title: ids.length === 1 ? 'Borrar conversación' : 'Borrar conversaciones',
      message:
        ids.length === 1
          ? 'Se borra la conversación con sus mensajes, grabaciones y el consumo del mes. No se puede deshacer.'
          : `Se borran ${ids.length} conversaciones con sus mensajes, grabaciones y el consumo del mes. No se puede deshacer.`,
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (!ok) return;
    del.mutate(ids, {
      onSuccess: (r) => {
        setSelected(new Set());
        notifySuccess(r.deleted === 1 ? 'Conversación borrada.' : `${r.deleted} conversaciones borradas.`);
      },
      onError: (e) => notifyError(e),
    });
  };

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
      {selectable && selected.size > 0 && (
        <Group justify="space-between" mb="sm" wrap="wrap">
          <Text size="sm" fw={600}>
            {selected.size === 1 ? '1 seleccionada' : `${selected.size} seleccionadas`}
          </Text>
          <Group gap="xs">
            <Button variant="subtle" color="gray" size="xs" onClick={() => setSelected(new Set())}>
              Limpiar selección
            </Button>
            <Button
              variant="subtle"
              color="red"
              size="xs"
              leftSection={<IconTrash size={16} />}
              loading={del.isPending}
              onClick={() => void remove([...selected])}
            >
              Borrar seleccionadas
            </Button>
          </Group>
        </Group>
      )}
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
                {selectable && (
                  <Table.Th w={40}>
                    <Checkbox
                      aria-label="Seleccionar todas"
                      checked={allPageSelected}
                      indeterminate={somePageSelected}
                      onChange={(e) => togglePage(e.currentTarget.checked)}
                    />
                  </Table.Th>
                )}
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
                  {selectable && (
                    <Table.Td>
                      <Checkbox
                        aria-label={`Seleccionar conversación del ${formatDateTime(c.created_at)}`}
                        checked={selected.has(c.id)}
                        onChange={(e) => toggle(c.id, e.currentTarget.checked)}
                      />
                    </Table.Td>
                  )}
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
                    <Group gap={4} justify="flex-end" wrap="nowrap">
                      <Button component={Link} to={`/calls/${c.id}`} variant="subtle" size="compact-sm">
                        Ver detalle
                      </Button>
                      {selectable && (
                        <Tooltip
                          label={isLiveStatus(c.status) ? 'La llamada está en curso' : 'Borrar conversación'}
                        >
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            disabled={isLiveStatus(c.status)}
                            loading={del.isPending && del.variables?.includes(c.id)}
                            onClick={() => void remove([c.id])}
                            aria-label="Borrar conversación"
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </Group>
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
