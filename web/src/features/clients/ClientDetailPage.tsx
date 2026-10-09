import {
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Select,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconArrowLeft, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { Client } from '@/api/types';
import { ActiveBadge } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useAgents } from '@/features/agents/api';
import { NewAgentModal } from '@/features/agents/NewAgentModal';
import { numberErrorTitle } from '@/features/numbers/errors';
import { useTiers } from '@/features/tiers/api';
import { UsersTable } from '@/features/users/UsersTable';
import { formatDate, formatDateTime, formatLimit, recentMonths } from '@/lib/format';
import { ENGINE } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useClient, useDeleteClient, useUpdateClient } from './api';
import { ApiAccess } from '@/features/developers/ApiAccess';
import { ClientUsage } from './ClientUsage';
import { LimitAdjustmentsCard } from './LimitAdjustmentsCard';
import { NumbersSection } from './NumbersSection';

function ClientDataCard({ client }: { client: Client }) {
  const tiers = useTiers();
  const update = useUpdateClient(client.id);
  const del = useDeleteClient();
  const navigate = useNavigate();
  const [name, setName] = useState(client.name);
  const tier = tiers.data?.find((t) => t.id === client.tier.id);

  const patch = (body: Parameters<typeof update.mutate>[0], ok: string) =>
    update.mutate(body, {
      onSuccess: () => notifySuccess(ok),
      onError: (e) => notifyError(e, numberErrorTitle(e)),
    });

  const setActive = async (active: boolean) => {
    if (
      !active &&
      !(await confirmAction({
        title: 'Desactivar cliente',
        message: `${client.name} no podrá hacer ni recibir llamadas hasta que lo actives de nuevo.`,
        confirmLabel: 'Desactivar',
        danger: true,
      }))
    ) {
      return;
    }
    patch({ active }, active ? 'Cliente activado.' : 'Cliente desactivado.');
  };

  const remove = async () => {
    if (
      !(await confirmAction({
        title: 'Borrar cliente',
        message: `Se borra ${client.name} con sus números, agentes, usuarios y API keys. Solo se puede si no tiene conversaciones.`,
        confirmLabel: 'Borrar',
        danger: true,
      }))
    ) {
      return;
    }
    del.mutate(client.id, {
      onSuccess: () => {
        notifySuccess('Cliente borrado.');
        void navigate('/clients', { replace: true });
      },
      onError: (e) =>
        notifyError(
          e,
          e instanceof ApiError && e.status === 409
            ? 'Tiene conversaciones: desactivalo en vez de borrarlo'
            : undefined,
        ),
    });
  };

  return (
    <Card>
      <Title order={4} mb="md">
        Datos
      </Title>
      <Stack gap="md">
        <Group align="flex-end" gap="xs">
          <TextInput
            label="Nombre"
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            maxLength={128}
            style={{ flex: 1 }}
          />
          <Button
            variant="default"
            disabled={!name.trim() || name.trim() === client.name}
            loading={update.isPending && update.variables?.name != null}
            onClick={() => patch({ name: name.trim() }, 'Nombre actualizado.')}
          >
            Guardar
          </Button>
        </Group>
        <TextInput label="Slug" value={client.slug} readOnly disabled description="No se cambia." />
        <Select
          label="Tier"
          data={(tiers.data ?? []).map((t) => ({ value: t.id, label: t.name }))}
          value={client.tier.id}
          onChange={(v) => v && v !== client.tier.id && patch({ tier_id: v }, 'Tier actualizado.')}
          allowDeselect={false}
          description={
            tier
              ? `${formatLimit(tier.max_concurrent_calls)} simultáneas · ${formatLimit(tier.inbound_minutes, ' min')} entrantes · ${formatLimit(tier.outbound_minutes, ' min')} salientes por mes · ${formatLimit(tier.max_phone_numbers)} números`
              : undefined
          }
        />
        <Switch
          label="Activo"
          description="Inactivo: no puede hacer ni recibir llamadas."
          checked={client.active}
          onChange={(e) => void setActive(e.currentTarget.checked)}
        />
        <Text size="xs" c="dimmed">
          Alta: {formatDate(client.created_at)}
        </Text>
        <Group justify="flex-end">
          <Button
            variant="subtle"
            color="red"
            leftSection={<IconTrash size={16} />}
            onClick={() => void remove()}
            loading={del.isPending}
          >
            Borrar cliente
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

function ClientAgentsCard({ clientId }: { clientId: string }) {
  const agents = useAgents(clientId, true);
  const [creating, create] = useDisclosure(false);
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Agentes</Title>
        <Button size="xs" leftSection={<IconPlus size={16} />} onClick={create.open}>
          Nuevo agente
        </Button>
      </Group>
      <QueryState query={agents}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>Sin agentes.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={520}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Motor</Table.Th>
                    <Table.Th>Voz</Table.Th>
                    <Table.Th>Versión</Table.Th>
                    <Table.Th>Actualizado</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((a) => (
                    <Table.Tr key={a.id} style={a.archived ? { opacity: 0.6 } : undefined}>
                      <Table.Td>
                        <Anchor component={Link} to={`/agents/${a.id}`} size="sm" fw={600}>
                          {a.name}
                        </Anchor>
                        {a.archived && (
                          <Badge color="gray" ml={6}>
                            Archivado
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>{ENGINE[a.engine] ?? a.engine}</Table.Td>
                      <Table.Td>{a.voice ?? '–'}</Table.Td>
                      <Table.Td className="mono">v{a.version}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(a.updated_at)}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      <NewAgentModal
        key={String(creating)}
        opened={creating}
        onClose={create.close}
        clientId={clientId}
        lockClient
      />
    </Card>
  );
}

const TABS = ['resumen', 'numeros', 'agentes', 'usuarios', 'api-keys'] as const;
type Tab = (typeof TABS)[number];

function ClientView({ client }: { client: Client }) {
  const [params, setParams] = useSearchParams();
  const tab: Tab = TABS.includes(params.get('tab') as Tab) ? (params.get('tab') as Tab) : 'resumen';
  const month = params.get('month') ?? recentMonths(1)[0];
  const setParam = (k: string, v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set(k, v);
        else next.delete(k);
        return next;
      },
      { replace: true },
    );

  return (
    <>
      <PageHeader
        above={
          <Button
            component={Link}
            to="/clients"
            variant="subtle"
            size="compact-sm"
            leftSection={<IconArrowLeft size={16} />}
            w="fit-content"
          >
            Clientes
          </Button>
        }
        docTitle={client.name}
        title={
          <Group gap="sm" component="span">
            {client.name}
            <ActiveBadge active={client.active} />
          </Group>
        }
        description={
          <>
            <Text span className="mono">
              {client.slug}
            </Text>
            {` · tier ${client.tier.name}${client.adjustments_count ? ` (+${client.adjustments_count} ajustes)` : ''} · ${client.agents_count ?? 0} agentes · ${client.numbers_count ?? 0} números`}
          </>
        }
      />
      <Tabs value={tab} onChange={(v) => setParam('tab', v === 'resumen' ? null : v)}>
        <Tabs.List mb="md">
          <Tabs.Tab value="resumen">Consumo y datos</Tabs.Tab>
          <Tabs.Tab value="numeros">Números</Tabs.Tab>
          <Tabs.Tab value="agentes">Agentes</Tabs.Tab>
          <Tabs.Tab value="usuarios">Usuarios</Tabs.Tab>
          <Tabs.Tab value="api-keys">API keys</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="resumen">
          <Grid gutter="md">
            <Grid.Col span={{ base: 12, lg: 7 }}>
              <ClientUsage clientId={client.id} month={month} onMonth={(m) => setParam('month', m)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, lg: 5 }}>
              <Stack gap="md">
                <ClientDataCard key={client.id} client={client} />
                <LimitAdjustmentsCard clientId={client.id} />
              </Stack>
            </Grid.Col>
          </Grid>
        </Tabs.Panel>
        <Tabs.Panel value="numeros">
          <NumbersSection clientId={client.id} canAssign />
        </Tabs.Panel>
        <Tabs.Panel value="agentes">
          <ClientAgentsCard clientId={client.id} />
        </Tabs.Panel>
        <Tabs.Panel value="usuarios">
          <Card>
            <UsersTable
              clientId={client.id}
              header={(add) => (
                <Group justify="space-between" mb="sm">
                  <Title order={4}>Usuarios</Title>
                  {add}
                </Group>
              )}
            />
          </Card>
        </Tabs.Panel>
        <Tabs.Panel value="api-keys">
          <ApiAccess clientId={client.id} showUsage={false} />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}

export function ClientDetailPage() {
  const { id } = useParams();
  const query = useClient(id);
  return <QueryState query={query}>{(c) => <ClientView key={c.id} client={c} />}</QueryState>;
}
