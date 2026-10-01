import { ActionIcon, Anchor, Badge, Button, Card, Group, Menu, Select, Table, Text } from '@mantine/core';
import { IconDots, IconPencil, IconPlayerPause, IconPlayerPlay, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { WaAccount } from '@/api/types';
import { ActiveBadge } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useClients } from '@/features/clients/api';
import { formatDate } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { EditWaAccountModal, NewWaAccountModal } from './AccountModal';
import { useDeactivateWaAccount, useUpdateWaAccount, useWaAccounts } from './api';

type Dialog = { kind: 'new' } | { kind: 'edit'; account: WaAccount } | null;

function dash() {
  return (
    <Text span inherit c="dimmed">
      –
    </Text>
  );
}

export function WhatsAppPage() {
  const [params, setParams] = useSearchParams();
  const clientId = params.get('client') ?? undefined;
  const accounts = useWaAccounts(clientId);
  const clients = useClients();
  const deactivate = useDeactivateWaAccount();
  const update = useUpdateWaAccount();
  const [dialog, setDialog] = useState<Dialog>(null);

  const setClient = (v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set('client', v);
        else next.delete('client');
        return next;
      },
      { replace: true },
    );

  const doDeactivate = async (a: WaAccount) => {
    const ok = await confirmAction({
      title: `Desactivar ${a.display_phone_number}`,
      message:
        'Los mensajes que lleguen a este número dejan de responderse (quedan registrados como ignorados). Las conversaciones anteriores se conservan.',
      confirmLabel: 'Desactivar',
      danger: true,
    });
    if (ok) {
      deactivate.mutate(a.id, {
        onSuccess: () => notifySuccess(`${a.display_phone_number} desactivado.`),
        onError: (e) => notifyError(e),
      });
    }
  };

  const doActivate = (a: WaAccount) =>
    update.mutate(
      { id: a.id, body: { active: true } },
      {
        onSuccess: () => notifySuccess(`${a.display_phone_number} vuelve a responder.`),
        onError: (e) => notifyError(e),
      },
    );

  return (
    <>
      <PageHeader
        title="WhatsApp"
        description="Números de WhatsApp Business conectados por la Cloud API de Meta. Cada uno lo atiende un agente del cliente; por ahora solo texto."
        actions={
          <Button leftSection={<IconPlus size={18} />} onClick={() => setDialog({ kind: 'new' })}>
            Conectar número
          </Button>
        }
      />
      <Card>
        <Group mb="md" gap="sm">
          <Select
            placeholder="Todos los clientes"
            data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            value={clientId ?? null}
            onChange={setClient}
            clearable
            searchable
            w={220}
            aria-label="Cliente"
          />
        </Group>
        <QueryState query={accounts}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState>
                {clientId
                  ? 'Este cliente no tiene números de WhatsApp.'
                  : 'No hay números de WhatsApp conectados. Usá "Conectar número" con los IDs de Meta.'}
              </EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={980}>
                <Table striped>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Número</Table.Th>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>Cliente</Table.Th>
                      <Table.Th>Agente</Table.Th>
                      <Table.Th>Token</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Alta</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((a) => (
                      <Table.Tr key={a.id}>
                        <Table.Td>
                          <Text size="sm" className="mono">
                            {a.display_phone_number}
                          </Text>
                          <Text size="xs" c="dimmed" className="mono">
                            ID {a.phone_number_id}
                          </Text>
                        </Table.Td>
                        <Table.Td>{a.name || dash()}</Table.Td>
                        <Table.Td>
                          <Anchor component={Link} to={`/clients/${a.client_id}`} size="sm">
                            {a.client_name ?? 'Cliente'}
                          </Anchor>
                        </Table.Td>
                        <Table.Td>
                          <Anchor component={Link} to={`/agents/${a.agent_id}`} size="sm">
                            {a.agent_name ?? 'Agente'}
                          </Anchor>
                        </Table.Td>
                        <Table.Td>
                          {a.has_token ? (
                            <Badge color="navy">Propio</Badge>
                          ) : (
                            <Badge color="gray">Global</Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <ActiveBadge active={a.active} />
                        </Table.Td>
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDate(a.created_at)}</Table.Td>
                        <Table.Td>
                          <Group justify="flex-end" wrap="nowrap">
                            <Menu position="bottom-end" withinPortal>
                              <Menu.Target>
                                <ActionIcon
                                  variant="subtle"
                                  aria-label={`Acciones de ${a.display_phone_number}`}
                                >
                                  <IconDots size={16} />
                                </ActionIcon>
                              </Menu.Target>
                              <Menu.Dropdown>
                                <Menu.Item
                                  leftSection={<IconPencil size={16} />}
                                  onClick={() => setDialog({ kind: 'edit', account: a })}
                                >
                                  Editar
                                </Menu.Item>
                                {a.active ? (
                                  <Menu.Item
                                    color="red"
                                    leftSection={<IconPlayerPause size={16} />}
                                    onClick={() => void doDeactivate(a)}
                                  >
                                    Desactivar
                                  </Menu.Item>
                                ) : (
                                  <Menu.Item
                                    leftSection={<IconPlayerPlay size={16} />}
                                    onClick={() => doActivate(a)}
                                  >
                                    Activar
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
            )
          }
        </QueryState>
      </Card>
      {dialog?.kind === 'new' && <NewWaAccountModal onClose={() => setDialog(null)} />}
      {dialog?.kind === 'edit' && (
        <EditWaAccountModal account={dialog.account} onClose={() => setDialog(null)} />
      )}
    </>
  );
}
