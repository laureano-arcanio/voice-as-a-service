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
import { IconLogin2, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { CallSummary } from '@/api/types';
import { Dash, LiveBadge, StatusDot } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { RowLink } from '@/components/RowLink';
import { useRowLink } from '@/components/useRowLink';
import { useIsAdmin } from '@/features/auth/api';
import { useIsClientAdmin } from '@/features/auth/useIsClientAdmin';
import { useFeatureLock } from '@/features/billing/features';
import { useDeleteConversations } from '@/features/calls/api';
import { useTeamPresence } from '@/features/phone/api';
import { useSupportSwitch } from '@/features/support/api';
import { useAreaPath } from '@/features/support/paths';
import { formatDateTime, formatDuration, formatValue } from '@/lib/format';
import { ANSWERED_BY, CALL_MODE, CALL_STATUS, callPerson, isLiveStatus } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { ReanalyzeButton } from './ReanalyzeButton';

export const PAGE_SIZE = 25;

const STATUS_OPTIONS = [
  { value: '', label: 'Todos los estados' },
  ...Object.entries(CALL_STATUS).map(([value, l]) => ({ value, label: l.label })),
];

function modeOptions(modes: string[]) {
  return [
    { value: '', label: 'Todos los orígenes' },
    ...modes.map((value) => ({ value, label: CALL_MODE[value]?.label ?? value })),
  ];
}

const ANSWERED_OPTIONS = [
  { value: '', label: 'Atendió: todas' },
  ...Object.entries(ANSWERED_BY).map(([value, label]) => ({ value, label: `Atendió: ${label}` })),
];

/** Sin agente: quién habló, "Llamó: Ana", "Atendió: Ana", "Atendió: el equipo" o "Nadie atendió". */
function PersonText({ c }: { c: CallSummary }) {
  const who = callPerson(c);
  if (!who) return '–';
  return who.verb ? `${who.verb}: ${who.name}` : who.name;
}

/** Datos extraídos del análisis: `captured/total` y un punto verde (todos), amarillo (algunos) o rojo (ninguno). */
function ExtractionStatus({ captured, total }: { captured: number; total: number }) {
  const color = captured === total ? 'green' : captured === 0 ? 'red' : 'yellow';
  const label =
    color === 'green'
      ? 'Todos los datos extraídos'
      : color === 'red'
        ? 'No se extrajo ningún dato'
        : 'Faltan datos por extraer';
  return (
    <Group gap={6} wrap="nowrap">
      <Text span className="mono">
        {captured}/{total}
      </Text>
      <Text span c="dimmed">
        datos
      </Text>
      <StatusDot color={color} label={label} />
    </Group>
  );
}

export function CallsTable({
  title = 'Conversaciones',
  modes = Object.keys(CALL_MODE),
  items,
  total,
  error,
  loading,
  showClient,
  page,
  status,
  mode,
  answered = null,
  userId = null,
  clientId = null,
  onPage,
  onStatus,
  onMode,
  onAnswered,
  onUser,
  selectable = false,
}: {
  title?: string;
  /** Los orígenes que puede elegir el filtro; con uno solo, el filtro no aparece. */
  modes?: string[];
  items: CallSummary[];
  total: number;
  error: unknown;
  loading: boolean;
  showClient: boolean;
  page: number;
  status: string | null;
  mode: string | null;
  /** Quién atendió la entrante (llamadas directas): solo con `onAnswered`. */
  answered?: 'agent' | 'team' | null;
  /** Usuario que llamó o atendió (llamadas directas): solo con `onUser`. */
  userId?: string | null;
  /** El admin elige un cliente para listar sus usuarios. */
  clientId?: string | null;
  onPage: (p: number) => void;
  onStatus: (s: string | null) => void;
  onMode: (m: string | null) => void;
  onAnswered?: (a: 'agent' | 'team' | null) => void;
  onUser?: (u: string | null) => void;
  /** Seleccion en bulk y borrado (estilo Gmail): solo admin. */
  selectable?: boolean;
}) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const del = useDeleteConversations();
  const isAdmin = useIsAdmin();
  const isClientAdmin = useIsClientAdmin();
  // Las acciones de la fila: borrar y ver como el cliente son del admin de la plataforma; volver a correr
  // el análisis, del Admin del cliente (que también lo es el admin entrando como él).
  const showActions = isAdmin || isClientAdmin;
  // Ancho mínimo: las columnas de todos, más las que solo ve el admin (Cliente sin filtro, Empresa y acciones).
  const minWidth = 900 + (showClient ? 130 : 0) + (showActions ? 130 : 0);
  const areaPath = useAreaPath();
  const rowLink = useRowLink();
  const { enter, pending: entering } = useSupportSwitch();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // Los filtros de llamadas directas solo tienen sentido si el plan las incluye (el admin ve todo).
  const direct = !useFeatureLock('direct_calls').locked;
  const showAnswered = direct && !!onAnswered;
  const showUser = direct && !!onUser && (!isAdmin || !!clientId);
  const people = useTeamPresence(clientId ?? undefined, showUser);

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
          <Title order={4}>{title}</Title>
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
          {modes.length > 1 && (
            <Select
              size="xs"
              data={modeOptions(modes)}
              value={mode ?? ''}
              onChange={(v) => onMode(v || null)}
              allowDeselect={false}
              w={170}
              aria-label="Origen"
            />
          )}
          {showAnswered && (
            <Select
              size="xs"
              data={ANSWERED_OPTIONS}
              value={answered ?? ''}
              onChange={(v) => onAnswered(v ? (v as 'agent' | 'team') : null)}
              allowDeselect={false}
              w={170}
              aria-label="Atendió"
            />
          )}
          {showUser && (
            <Select
              size="xs"
              data={[
                { value: '', label: 'Todos los usuarios' },
                ...(people.data ?? []).map((u) => ({ value: u.user_id, label: u.name })),
              ]}
              value={userId ?? ''}
              onChange={(v) => onUser(v || null)}
              allowDeselect={false}
              searchable
              w={190}
              aria-label="Usuario"
            />
          )}
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
        // Cada conversación ocupa una fila de una línea y las acciones quedan fijas a la derecha: así están a la
        // vista aunque la tabla tenga scroll.
        <Table.ScrollContainer minWidth={minWidth}>
          <Table highlightOnHover style={{ whiteSpace: 'nowrap' }}>
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
                <Table.Th>Atendió</Table.Th>
                <Table.Th>Contacto</Table.Th>
                {isAdmin && <Table.Th>Empresa</Table.Th>}
                <Table.Th>Número</Table.Th>
                <Table.Th>Duración</Table.Th>
                <Table.Th>Estado</Table.Th>
                {showActions && <Table.Th className="row-actions" />}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((c) => (
                <Table.Tr key={c.id} {...rowLink(areaPath(`/calls/${c.id}`))}>
                  {selectable && (
                    // Un click al lado del checkbox no abre la conversación.
                    <Table.Td onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        aria-label={`Seleccionar conversación del ${formatDateTime(c.created_at)}`}
                        checked={selected.has(c.id)}
                        onChange={(e) => toggle(c.id, e.currentTarget.checked)}
                      />
                    </Table.Td>
                  )}
                  <Table.Td>
                    <RowLink
                      to={areaPath(`/calls/${c.id}`)}
                      label={`Ver conversación del ${formatDateTime(c.created_at)}`}
                    >
                      {formatDateTime(c.created_at)}
                    </RowLink>
                  </Table.Td>
                  {showClient && (
                    <Table.Td>{formatValue(c.client_name) || <Dash />}</Table.Td>
                  )}
                  <Table.Td>
                    {c.agent_id && isAdmin && c.client_id ? (
                      // El editor del agente es del panel del cliente: el admin entra como el cliente.
                      <Anchor
                        component="button"
                        type="button"
                        onClick={() => void enter(c.client_id!, `/agents/${c.agent_id}`)}
                        size="sm"
                      >
                        {c.agent_name ?? 'Agente'}
                      </Anchor>
                    ) : c.agent_id && !isAdmin ? (
                      <Anchor component={Link} to={`/agents/${c.agent_id}`} size="sm">
                        {c.agent_name ?? 'Agente'}
                      </Anchor>
                    ) : (
                      (c.agent_name ?? <PersonText c={c} />)
                    )}
                    {c.agent_version != null && (
                      <Text span c="dimmed" className="mono">
                        {' '}
                        v{c.agent_version}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>{formatValue(c.contact_name) || <Dash />}</Table.Td>
                  {isAdmin && <Table.Td>{formatValue(c.company) || <Dash />}</Table.Td>}
                  <Table.Td>
                    {c.phone ? (
                      <Text span className="mono">
                        {c.phone}
                      </Text>
                    ) : (
                      <Dash />
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Group gap={6} wrap="nowrap">
                      {c.duration_seconds ? (
                        <Text span className="mono">
                          {formatDuration(c.duration_seconds)}
                        </Text>
                      ) : (
                        !isLiveStatus(c.status) && <Dash />
                      )}
                      {isLiveStatus(c.status) && <LiveBadge>En vivo</LiveBadge>}
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    {c.analysis_status === 'pending' || c.analysis_status === 'running' ? (
                      <Text size="sm" c="dimmed">
                        Analizando…
                      </Text>
                    ) : c.total > 0 ? (
                      <ExtractionStatus captured={c.captured} total={c.total} />
                    ) : (
                      <Dash />
                    )}
                  </Table.Td>
                  {showActions && (
                    <Table.Td ta="right" className="row-actions" onClick={(e) => e.stopPropagation()}>
                      <Group gap={4} justify="flex-end" wrap="nowrap">
                        {isAdmin && c.client_id && (
                          <Tooltip label="Ver como el cliente">
                            <ActionIcon
                              variant="subtle"
                              loading={entering}
                              onClick={() => void enter(c.client_id!, `/calls/${c.id}`)}
                              aria-label="Ver como el cliente"
                            >
                              <IconLogin2 size={16} />
                            </ActionIcon>
                          </Tooltip>
                        )}
                        <ReanalyzeButton
                          conversationId={c.id}
                          agentVersion={c.agent_version}
                          hasAnalysis={c.has_analysis}
                          callStatus={c.status}
                          analysisStatus={c.analysis_status}
                          compact
                        />
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
                  )}
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
