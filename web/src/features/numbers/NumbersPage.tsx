import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Menu,
  SegmentedControl,
  Select,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import {
  IconDots,
  IconPencil,
  IconPlus,
  IconSearch,
  IconTrash,
  IconUnlink,
  IconUserPlus,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { PhoneNumber } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useClients } from '@/features/clients/api';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { NumberAgentSelect } from './AgentSelect';
import { useDeleteNumber, usePhoneNumbers, useReleaseNumber, type NumberStatus } from './api';
import { numberErrorTitle } from './errors';
import { AssignNumberModal, BulkLoadModal, EditNumberModal } from './NumberModals';
import { matchesNumber, plural } from './parse';
import { SipNotice } from './SipNotice';

type Dialog = { kind: 'bulk' } | { kind: 'assign' | 'edit'; number: PhoneNumber } | null;

export function NumbersPage() {
  const [params, setParams] = useSearchParams();
  const status = (
    ['free', 'assigned'].includes(params.get('status') ?? '') ? params.get('status') : undefined
  ) as NumberStatus | undefined;
  const clientId = params.get('client') ?? undefined;
  const [q, setQ] = useState('');
  const numbers = usePhoneNumbers({ status, clientId });
  const clients = useClients();
  const release = useReleaseNumber();
  const del = useDeleteNumber();
  const [dialog, setDialog] = useState<Dialog>(null);

  const set = (k: string, v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set(k, v);
        else next.delete(k);
        return next;
      },
      { replace: true },
    );

  const doRelease = async (n: PhoneNumber) => {
    const ok = await confirmAction({
      title: `Liberar ${n.e164}`,
      message: `Vuelve al inventario sin cliente ni agente: las llamadas a este número dejan de atenderse${n.client_name ? ` para ${n.client_name}` : ''}.`,
      confirmLabel: 'Liberar',
      danger: true,
    });
    if (ok) {
      release.mutate(n.id, {
        onSuccess: () => notifySuccess(`${n.e164} volvió al inventario.`),
        onError: (e) => notifyError(e, numberErrorTitle(e)),
      });
    }
  };

  const doDelete = async (n: PhoneNumber) => {
    const ok = await confirmAction({
      title: `Borrar ${n.e164}`,
      message: 'Se quita del inventario. Después corré make livekit-sip en el server.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok) {
      del.mutate(n.id, {
        onSuccess: () => notifySuccess(`${n.e164} borrado.`),
        onError: (e) =>
          notifyError(
            e,
            e instanceof ApiError && e.status === 409 ? 'Está asignado: liberalo antes' : undefined,
          ),
      });
    }
  };

  return (
    <>
      <PageHeader
        title="Números"
        description="Inventario de números: se cargan libres, se asignan a un cliente y se rutean a uno de sus agentes."
        actions={
          <Button leftSection={<IconPlus size={18} />} onClick={() => setDialog({ kind: 'bulk' })}>
            Cargar números
          </Button>
        }
      />
      <SipNotice />
      <Card>
        <Group mb="md" gap="sm" align="flex-end" wrap="wrap">
          <SegmentedControl
            value={status ?? 'all'}
            onChange={(v) => set('status', v === 'all' ? null : v)}
            data={[
              { value: 'all', label: 'Todos' },
              { value: 'free', label: 'Libres' },
              { value: 'assigned', label: 'Asignados' },
            ]}
          />
          <Select
            placeholder="Todos los clientes"
            data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            value={clientId ?? null}
            onChange={(v) => set('client', v)}
            clearable
            searchable
            w={220}
            aria-label="Cliente"
          />
          <TextInput
            placeholder="Buscar número o etiqueta"
            leftSection={<IconSearch size={16} />}
            value={q}
            onChange={(e) => setQ(e.currentTarget.value)}
            w={240}
            aria-label="Buscar"
          />
        </Group>
        <QueryState query={numbers}>
          {(all) => {
            const list = all.filter((n) => matchesNumber(n, q));
            return list.length === 0 ? (
              <EmptyState>
                {all.length ? 'Ningún número coincide.' : 'No hay números. Cargalos con "Cargar números".'}
              </EmptyState>
            ) : (
              <>
                <Text size="xs" c="dimmed" mb="xs">
                  {plural(list.length, 'número', 'números')} ·{' '}
                  {plural(list.filter((n) => !n.client_id).length, 'libre', 'libres')}
                </Text>
                <Table.ScrollContainer minWidth={980}>
                  <Table>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Número</Table.Th>
                        <Table.Th>Etiqueta</Table.Th>
                        <Table.Th>Proveedor</Table.Th>
                        <Table.Th>Cliente</Table.Th>
                        <Table.Th>Agente</Table.Th>
                        <Table.Th>Asignado el</Table.Th>
                        <Table.Th />
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {list.map((n) => (
                        <Table.Tr key={n.id}>
                          <Table.Td className="mono">{n.e164}</Table.Td>
                          <Table.Td>
                            {n.label || (
                              <Text span inherit c="dimmed">
                                –
                              </Text>
                            )}
                          </Table.Td>
                          <Table.Td>{n.provider}</Table.Td>
                          <Table.Td>
                            {n.client_id ? (
                              <Anchor component={Link} to={`/clients/${n.client_id}?tab=numeros`} size="sm">
                                {n.client_name ?? 'Cliente'}
                              </Anchor>
                            ) : (
                              <Badge color="gray">Libre</Badge>
                            )}
                          </Table.Td>
                          <Table.Td>
                            {n.client_id ? (
                              <NumberAgentSelect number={n} />
                            ) : (
                              <Text span inherit c="dimmed">
                                –
                              </Text>
                            )}
                          </Table.Td>
                          <Table.Td style={{ whiteSpace: 'nowrap' }}>
                            {n.assigned_at ? formatDateTime(n.assigned_at) : '–'}
                          </Table.Td>
                          <Table.Td>
                            <Group gap={4} justify="flex-end" wrap="nowrap">
                              {!n.client_id && (
                                <Button
                                  size="compact-sm"
                                  variant="subtle"
                                  leftSection={<IconUserPlus size={16} />}
                                  onClick={() => setDialog({ kind: 'assign', number: n })}
                                >
                                  Asignar
                                </Button>
                              )}
                              <Menu position="bottom-end" withinPortal>
                                <Menu.Target>
                                  <ActionIcon
                                    variant="subtle"
                                    color="gray"
                                    aria-label={`Acciones de ${n.e164}`}
                                  >
                                    <IconDots size={16} />
                                  </ActionIcon>
                                </Menu.Target>
                                <Menu.Dropdown>
                                  <Menu.Item
                                    leftSection={<IconPencil size={16} />}
                                    onClick={() => setDialog({ kind: 'edit', number: n })}
                                  >
                                    Editar etiqueta{n.client_id ? ' y agente' : ''}
                                  </Menu.Item>
                                  {n.client_id ? (
                                    <Menu.Item
                                      color="red"
                                      leftSection={<IconUnlink size={16} />}
                                      onClick={() => void doRelease(n)}
                                    >
                                      Liberar
                                    </Menu.Item>
                                  ) : (
                                    <Menu.Item
                                      color="red"
                                      leftSection={<IconTrash size={16} />}
                                      onClick={() => void doDelete(n)}
                                    >
                                      Borrar
                                    </Menu.Item>
                                  )}
                                </Menu.Dropdown>
                              </Menu>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              </>
            );
          }}
        </QueryState>
      </Card>
      {dialog?.kind === 'bulk' && <BulkLoadModal onClose={() => setDialog(null)} />}
      {dialog?.kind === 'assign' && (
        <AssignNumberModal number={dialog.number} onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === 'edit' && <EditNumberModal number={dialog.number} onClose={() => setDialog(null)} />}
    </>
  );
}
