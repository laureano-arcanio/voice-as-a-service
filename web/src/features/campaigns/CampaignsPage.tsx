import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Progress,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { WaCampaign } from '@/api/types';
import { Dash, LiveBadge } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useCurrentUser } from '@/features/auth/api';
import { READ_ONLY_REASON, useReadOnly } from '@/features/auth/readOnly';
import { useClients } from '@/features/clients/api';
import { useWaAccounts } from '@/features/whatsapp/api';
import { formatDate, formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAddOptout, useCampaigns, useOptouts, useRemoveOptout } from './api';
import { NewCampaignModal } from './CampaignModals';
import { CAMPAIGN_STATUS, OPTOUT_SOURCE, pct } from './labels';

export function CampaignStatusBadge({ campaign }: { campaign: WaCampaign }) {
  if (campaign.status === 'running') return <LiveBadge>{CAMPAIGN_STATUS.running.label}</LiveBadge>;
  const l = CAMPAIGN_STATUS[campaign.status] ?? { label: campaign.status, color: 'gray' };
  return (
    <Tooltip label={campaign.status_reason} multiline w={280} withArrow disabled={!campaign.status_reason}>
      <Badge color={l.color}>{l.label}</Badge>
    </Tooltip>
  );
}

/** Enviados (o procesados) sobre el total, con la barra. */
function ProgressCell({ c }: { c: WaCampaign }) {
  const done = c.stats.total - c.stats.pending;
  const p = pct(done, c.stats.total) ?? 0;
  return (
    <Stack gap={4} w={140}>
      <Text size="sm" className="mono">
        {done} / {c.stats.total}
      </Text>
      <Progress value={p} size="sm" aria-label={`${p} % procesado`} />
    </Stack>
  );
}

function Rate({ value, of }: { value: number; of: number }) {
  const p = pct(value, of);
  return (
    <Text size="sm" className="mono" ta="right">
      {value}
      {p !== null && (
        <Text span size="xs" c="dimmed">
          {' '}
          {p} %
        </Text>
      )}
    </Text>
  );
}

/** Numeros que pidieron no recibir campañas (por WhatsApp o cargados a mano). */
function OptoutsCard({ clientId, isAdmin }: { clientId?: string; isAdmin: boolean }) {
  const optouts = useOptouts(clientId);
  const add = useAddOptout();
  const remove = useRemoveOptout();
  const [phone, setPhone] = useState('');
  const canAdd = !isAdmin || !!clientId;

  const doRemove = async (waId: string, cid: string) => {
    const ok = await confirmAction({
      title: `Sacar ${waId} de las bajas`,
      message: 'Las próximas campañas le van a volver a escribir. Hacelo solo si pidió que le escriban.',
      confirmLabel: 'Sacar',
      danger: true,
    });
    if (ok)
      remove.mutate(
        { waId, clientId: cid },
        { onSuccess: () => notifySuccess('Número sacado de las bajas.'), onError: (e) => notifyError(e) },
      );
  };

  return (
    <Card>
      <Group justify="space-between" mb="sm" gap="sm">
        <Title order={4}>Bajas</Title>
        <Tooltip label="Elegí un cliente para cargar bajas" disabled={canAdd} withArrow>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              add.mutate(
                { phone, client_id: clientId ?? null },
                {
                  onSuccess: (o) => {
                    notifySuccess(`${o.wa_id} no va a recibir campañas.`);
                    setPhone('');
                  },
                  onError: (err) => notifyError(err, 'No se pudo cargar la baja'),
                },
              );
            }}
          >
            <Group gap="xs">
              <TextInput
                placeholder="351 555-1234"
                aria-label="Teléfono a dar de baja"
                value={phone}
                onChange={(e) => setPhone(e.currentTarget.value)}
                disabled={!canAdd}
                w={180}
              />
              <Button
                type="submit"
                variant="default"
                disabled={!canAdd || !phone.trim()}
                loading={add.isPending}
              >
                Dar de baja
              </Button>
            </Group>
          </form>
        </Tooltip>
      </Group>
      <Text size="sm" c="dimmed" mb="sm">
        Ninguna campaña les escribe. Se suman solos cuando un contacto responde a una campaña con "No me
        interesa" o "Baja".
      </Text>
      <QueryState query={optouts}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>Nadie pidió la baja.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={480} mah={320}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Teléfono</Table.Th>
                    <Table.Th>Origen</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((o) => (
                    <Table.Tr key={`${o.client_id}-${o.wa_id}`}>
                      <Table.Td className="mono">{o.wa_id}</Table.Td>
                      <Table.Td>{OPTOUT_SOURCE[o.source] ?? o.source}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(o.created_at)}</Table.Td>
                      <Table.Td>
                        <Group justify="flex-end">
                          <Tooltip label="Sacar de las bajas" withArrow>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              aria-label={`Sacar ${o.wa_id} de las bajas`}
                              onClick={() => void doRemove(o.wa_id, o.client_id)}
                            >
                              <IconTrash size={16} />
                            </ActionIcon>
                          </Tooltip>
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
  );
}

export function CampaignsPage() {
  const me = useCurrentUser();
  const isAdmin = me.role === 'admin';
  const [params, setParams] = useSearchParams();
  const clientId = isAdmin ? (params.get('client') ?? undefined) : undefined;
  const campaigns = useCampaigns(clientId);
  const accounts = useWaAccounts(clientId);
  const clients = useClients(isAdmin);
  const [creating, setCreating] = useState(false);

  // Mandan campañas los numeros conectados que el cliente administra (token propio); el admin, todos.
  const senders = (accounts.data ?? []).filter(
    (a) => a.active && a.status === 'connected' && (isAdmin || a.has_token),
  );
  const noSender = accounts.isSuccess && senders.length === 0;
  const readOnly = useReadOnly();
  const blocked = noSender || readOnly;

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

  return (
    <Stack gap="md">
      <PageHeader
        title="Campañas"
        description="Mensajes de WhatsApp que inicia el negocio, con una plantilla aprobada por Meta. Las respuestas las atiende el agente."
        actions={
          <Tooltip
            label={
              readOnly
                ? READ_ONLY_REASON
                : 'Hace falta un número de WhatsApp conectado con su propia cuenta (Conectar WhatsApp)'
            }
            multiline
            w={260}
            withArrow
            disabled={!blocked}
          >
            <Button
              leftSection={<IconPlus size={18} />}
              data-disabled={blocked || undefined}
              onClick={(e) => (blocked ? e.preventDefault() : setCreating(true))}
            >
              Nueva campaña
            </Button>
          </Tooltip>
        }
      />
      <Card>
        {isAdmin && (
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
        )}
        <QueryState query={campaigns}>
          {(rows) =>
            rows.length === 0 ? (
              <EmptyState>
                {noSender
                  ? 'Para mandar campañas, primero conectá un número en WhatsApp y creá una plantilla.'
                  : 'No hay campañas. Usá "Nueva campaña" para mandar una plantilla a una lista de contactos.'}
              </EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={isAdmin ? 1080 : 960}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Campaña</Table.Th>
                      {isAdmin && <Table.Th>Cliente</Table.Th>}
                      <Table.Th>Número</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Enviados</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Entregados</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Respondieron</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Fallidos</Table.Th>
                      <Table.Th>Creada</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {rows.map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td>
                          <Anchor component={Link} to={`/campaigns/${c.id}`} size="sm" fw={600}>
                            {c.name}
                          </Anchor>
                          <Text size="xs" c="dimmed" className="mono">
                            {c.template_name}
                          </Text>
                        </Table.Td>
                        {isAdmin && <Table.Td>{c.client_name ?? <Dash />}</Table.Td>}
                        <Table.Td className="mono">{c.display_phone_number ?? <Dash />}</Table.Td>
                        <Table.Td>
                          <CampaignStatusBadge campaign={c} />
                        </Table.Td>
                        <Table.Td>
                          <ProgressCell c={c} />
                        </Table.Td>
                        <Table.Td>
                          <Rate value={c.stats.delivered} of={c.stats.sent} />
                        </Table.Td>
                        <Table.Td>
                          <Rate value={c.stats.replied} of={c.stats.delivered} />
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" className="mono" ta="right" c={c.stats.failed ? 'red' : undefined}>
                            {c.stats.failed}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDate(c.created_at)}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      <OptoutsCard clientId={clientId} isAdmin={isAdmin} />
      {creating && <NewCampaignModal accounts={senders} onClose={() => setCreating(false)} />}
    </Stack>
  );
}
