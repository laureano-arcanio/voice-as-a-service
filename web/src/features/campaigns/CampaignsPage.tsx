import {
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Menu,
  Progress,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Text,
  Tooltip,
} from '@mantine/core';
import { IconBrandWhatsapp, IconChevronDown, IconPhoneCall, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { Campaign, CampaignChannel } from '@/api/types';
import { Dash, LiveBadge } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useCurrentUser } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { OptoutsCard } from '@/features/contacts/OptoutsCard';
import { useWaAccounts } from '@/features/whatsapp/api';
import { formatDate } from '@/lib/format';
import { useCampaigns, usePlan } from './api';
import { NewCampaignModal } from './CampaignModals';
import { CHANNEL, pct, statusLabel } from './labels';
import { VoiceCampaignModal } from './VoiceCampaignModal';

export function CampaignStatusBadge({
  campaign,
}: {
  campaign: Pick<Campaign, 'status' | 'channel' | 'status_reason'>;
}) {
  const l = statusLabel(campaign);
  if (campaign.status === 'running') return <LiveBadge>{l.label}</LiveBadge>;
  return (
    <Tooltip label={campaign.status_reason} multiline w={280} withArrow disabled={!campaign.status_reason}>
      <Badge color={l.color}>{l.label}</Badge>
    </Tooltip>
  );
}

export function CampaignChannelBadge({ channel }: { channel: CampaignChannel }) {
  const Icon = channel === 'whatsapp' ? IconBrandWhatsapp : IconPhoneCall;
  return (
    <Badge color="gray" leftSection={<Icon size={12} aria-hidden />}>
      {CHANNEL[channel]}
    </Badge>
  );
}

/** Procesados (enviados, llamados o salteados) sobre el total, con la barra. */
function ProgressCell({ c }: { c: Campaign }) {
  const done = c.progress.done + c.progress.failed + c.progress.skipped;
  const p = Math.round(c.percent);
  return (
    <Stack gap={4} w={140}>
      <Text size="sm" className="mono">
        {done} / {c.total}
      </Text>
      <Progress value={c.percent} size="sm" aria-label={`${p} % procesado`} />
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

/** Alcanzados: entregados (WhatsApp) o atendidas (llamadas), sobre lo enviado o llamado. */
function reached(c: Campaign): { value: number; of: number } {
  if (c.channel === 'whatsapp') return { value: c.results.delivered ?? 0, of: c.results.sent ?? 0 };
  return { value: c.results.answered ?? 0, of: Object.values(c.results).reduce((a, b) => a + b, 0) };
}

type ChannelFilter = 'all' | CampaignChannel;

export function CampaignsPage() {
  const me = useCurrentUser();
  const isAdmin = me.role === 'admin';
  const [params, setParams] = useSearchParams();
  const clientId = isAdmin ? (params.get('client') ?? undefined) : undefined;
  const channel = (
    ['whatsapp', 'voice'].includes(params.get('channel') ?? '') ? params.get('channel') : 'all'
  ) as ChannelFilter;
  const campaigns = useCampaigns(clientId, channel === 'all' ? undefined : channel);
  const accounts = useWaAccounts(clientId);
  const clients = useClients(isAdmin);
  const plan = usePlan(clientId, !isAdmin || !!clientId);
  const [creating, setCreating] = useState<CampaignChannel | null>(null);

  // Mandan campañas los numeros conectados que el cliente administra (token propio); el admin, todos.
  const senders = (accounts.data ?? []).filter(
    (a) => a.active && a.status === 'connected' && (isAdmin || a.has_token),
  );
  const noSender = accounts.isSuccess && senders.length === 0;

  // Por que un canal no se puede usar (null = se puede). Sin plan cargado (admin sin cliente), se deja pasar.
  const channels = plan.data?.channels;
  const blocked: Record<CampaignChannel, string | null> = {
    whatsapp:
      channels && !channels.includes('whatsapp')
        ? `Tu plan (${plan.data?.tier_name}) no incluye campañas por WhatsApp`
        : noSender
          ? 'Hace falta un número de WhatsApp conectado con su propia cuenta (Conectar WhatsApp)'
          : null,
    voice:
      channels && !channels.includes('voice')
        ? `Tu plan (${plan.data?.tier_name}) no incluye campañas por llamadas`
        : null,
  };
  const allBlocked = blocked.whatsapp && blocked.voice;
  const blockedText = [blocked.whatsapp, blocked.voice].filter(Boolean).join('. ');

  const setParam = (key: string, v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set(key, v);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );

  const item = (ch: CampaignChannel, label: string, icon: React.ReactNode) => (
    <Menu.Item leftSection={icon} disabled={!!blocked[ch]} onClick={() => setCreating(ch)}>
      <Text size="sm">{label}</Text>
      {blocked[ch] && (
        <Text size="xs" c="dimmed" maw={260} style={{ whiteSpace: 'normal' }}>
          {blocked[ch]}
        </Text>
      )}
    </Menu.Item>
  );

  return (
    <Stack gap="md">
      <PageHeader
        title="Campañas"
        description="Mensajes de WhatsApp con una plantilla aprobada por Meta, o llamadas del agente, a una lista de contactos. Las respuestas y las llamadas las atiende el agente."
        actions={
          allBlocked ? (
            <Tooltip label={blockedText} multiline w={300} withArrow>
              <Button leftSection={<IconPlus size={18} />} data-disabled onClick={(e) => e.preventDefault()}>
                Nueva campaña
              </Button>
            </Tooltip>
          ) : (
            <Menu position="bottom-end" withinPortal>
              <Menu.Target>
                <Button leftSection={<IconPlus size={18} />} rightSection={<IconChevronDown size={16} />}>
                  Nueva campaña
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                {item('whatsapp', 'Por WhatsApp', <IconBrandWhatsapp size={16} />)}
                {item('voice', 'Por llamadas', <IconPhoneCall size={16} />)}
              </Menu.Dropdown>
            </Menu>
          )
        }
      />
      <Card>
        <Group mb="md" gap="sm">
          {isAdmin && (
            <Select
              placeholder="Todos los clientes"
              data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
              value={clientId ?? null}
              onChange={(v) => setParam('client', v)}
              clearable
              searchable
              w={220}
              aria-label="Cliente"
            />
          )}
          <SegmentedControl
            aria-label="Canal"
            value={channel}
            onChange={(v) => setParam('channel', v === 'all' ? null : v)}
            data={[
              { value: 'all', label: 'Todas' },
              { value: 'whatsapp', label: 'WhatsApp' },
              { value: 'voice', label: 'Llamadas' },
            ]}
          />
        </Group>
        <QueryState query={campaigns}>
          {(rows) =>
            rows.length === 0 ? (
              <EmptyState>
                {channel !== 'all'
                  ? `No hay campañas por ${CHANNEL[channel].toLowerCase()}.`
                  : allBlocked
                    ? blockedText
                    : 'No hay campañas. Usá "Nueva campaña" para mandar una plantilla o llamar a una lista de contactos.'}
              </EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={isAdmin ? 1160 : 1040}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Campaña</Table.Th>
                      {isAdmin && <Table.Th>Cliente</Table.Th>}
                      <Table.Th>Canal</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Avance</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Alcanzados</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Respondieron</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Fallidos</Table.Th>
                      <Table.Th>Creada</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {rows.map((c) => {
                      const r = reached(c);
                      return (
                        <Table.Tr key={c.id}>
                          <Table.Td>
                            <Anchor component={Link} to={`/campaigns/${c.id}`} size="sm" fw={600}>
                              {c.name}
                            </Anchor>
                            <Text
                              size="xs"
                              c="dimmed"
                              className={c.channel === 'whatsapp' ? 'mono' : undefined}
                            >
                              {c.channel === 'whatsapp' ? c.template_name : `Agente ${c.agent_name ?? '–'}`}
                            </Text>
                          </Table.Td>
                          {isAdmin && <Table.Td>{c.client_name ?? <Dash />}</Table.Td>}
                          <Table.Td>
                            <CampaignChannelBadge channel={c.channel} />
                          </Table.Td>
                          <Table.Td>
                            <CampaignStatusBadge campaign={c} />
                          </Table.Td>
                          <Table.Td>
                            <ProgressCell c={c} />
                          </Table.Td>
                          <Table.Td>
                            <Rate value={r.value} of={r.of} />
                          </Table.Td>
                          <Table.Td>
                            {c.channel === 'whatsapp' ? (
                              <Rate value={c.results.replied ?? 0} of={c.results.delivered ?? 0} />
                            ) : (
                              <Text ta="right">
                                <Dash />
                              </Text>
                            )}
                          </Table.Td>
                          <Table.Td>
                            <Text
                              size="sm"
                              className="mono"
                              ta="right"
                              c={c.progress.failed ? 'red' : undefined}
                            >
                              {c.progress.failed}
                            </Text>
                          </Table.Td>
                          <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDate(c.created_at)}</Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      <OptoutsCard clientId={clientId} isAdmin={isAdmin} />
      {creating === 'whatsapp' && <NewCampaignModal accounts={senders} onClose={() => setCreating(null)} />}
      {creating === 'voice' && <VoiceCampaignModal clientId={clientId} onClose={() => setCreating(null)} />}
    </Stack>
  );
}
