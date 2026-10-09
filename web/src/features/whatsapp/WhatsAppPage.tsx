import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Menu,
  Select,
  Stack,
  Table,
  Text,
  Tooltip,
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconBrandWhatsapp,
  IconDots,
  IconPencil,
  IconPlayerPause,
  IconPlayerPlay,
  IconPlus,
  IconRefresh,
  IconRepeat,
  IconTemplate,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { WaAccount } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useAgents } from '@/features/agents/api';
import { useCurrentUser } from '@/features/auth/api';
import { READ_ONLY_REASON, useReadOnly } from '@/features/auth/readOnly';
import { useClients } from '@/features/clients/api';
import { formatDate } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { EditWaAccountModal, NewWaAccountModal } from './AccountModal';
import {
  useDeactivateWaAccount,
  useRefreshWaAccount,
  useUpdateWaAccount,
  useWaAccounts,
  useWaConfig,
} from './api';
import { WA_MANAGER_URL, WA_QUALITY, WA_SOURCE, WA_STATUS, WA_STATUS_HELP } from './labels';
import { RegisterModal } from './RegisterModal';
import { SignupModal } from './SignupModal';
import { TemplatesCard } from './Templates';

type Dialog =
  | { kind: 'signup' }
  | { kind: 'manual' }
  | { kind: 'edit'; account: WaAccount }
  | { kind: 'register'; account: WaAccount }
  | null;

function dash() {
  return (
    <Text span inherit c="dimmed">
      –
    </Text>
  );
}

function StatusCell({ account }: { account: WaAccount }) {
  const st = WA_STATUS[account.status] ?? { label: account.status, color: 'gray' };
  const help = [account.status_reason, WA_STATUS_HELP[account.status]].filter(Boolean).join(' · ');
  return (
    <Group gap={4} wrap="nowrap">
      <Tooltip label={help} multiline w={280} withArrow disabled={!help}>
        <Badge color={st.color}>{st.label}</Badge>
      </Tooltip>
      {!account.active && <Badge color="gray">Inactivo</Badge>}
    </Group>
  );
}

function QualityCell({ account }: { account: WaAccount }) {
  const q = account.quality_rating ? WA_QUALITY[account.quality_rating] : undefined;
  if (!q && !account.messaging_limit) return dash();
  return (
    <Stack gap={2}>
      {q && <Badge color={q.color}>{q.label}</Badge>}
      {account.messaging_limit && (
        <Text size="xs" c="dimmed" className="mono">
          {account.messaging_limit}
        </Text>
      )}
    </Stack>
  );
}

/** Agente que atiende el numero, editable en la fila (admin o dueño). */
function WaAgentSelect({ account }: { account: WaAccount }) {
  const agents = useAgents(account.client_id, false);
  const update = useUpdateWaAccount();
  const data = (agents.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  // El agente actual puede estar archivado: se sigue mostrando.
  if (!data.some((o) => o.value === account.agent_id)) {
    data.push({ value: account.agent_id, label: `${account.agent_name ?? 'Agente'} (archivado)` });
  }
  return (
    <Select
      size="xs"
      w={200}
      data={data}
      value={account.agent_id}
      searchable
      allowDeselect={false}
      disabled={update.isPending}
      aria-label={`Agente de ${account.display_phone_number}`}
      onChange={(agentId) =>
        agentId &&
        agentId !== account.agent_id &&
        update.mutate(
          { id: account.id, body: { agent_id: agentId } },
          {
            onSuccess: (a) =>
              notifySuccess(`${a.display_phone_number} lo atiende ${a.agent_name ?? 'el agente'}.`),
            onError: (e) => notifyError(e),
          },
        )
      }
    />
  );
}

export function WhatsAppPage() {
  const me = useCurrentUser();
  const isAdmin = me.role === 'admin';
  const [params, setParams] = useSearchParams();
  const clientId = isAdmin ? (params.get('client') ?? undefined) : undefined;
  const accounts = useWaAccounts(clientId);
  const clients = useClients(isAdmin);
  const config = useWaConfig();
  const deactivate = useDeactivateWaAccount();
  const update = useUpdateWaAccount();
  const refresh = useRefreshWaAccount();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [templatesFor, setTemplatesFor] = useState<string | null>(null);

  const list = accounts.data ?? [];
  // Registro, datos de Meta y plantillas: un cliente solo en numeros con su propio token. Los de
  // alta manual usan el token de nuestro portafolio (la API da 403).
  const canManage = (a: WaAccount) => isAdmin || a.has_token;
  const manageable = list.filter(canManage);
  // Sin elegir, las plantillas son las del primer numero.
  const templatesAccount =
    templatesFor && manageable.some((a) => a.id === templatesFor)
      ? templatesFor
      : (manageable[0]?.id ?? null);
  // Solo lectura (cliente inactivo): no se conectan ni registran numeros.
  const readOnly = useReadOnly();
  const signupEnabled = !!config.data?.enabled && !readOnly;
  const signupReason = readOnly
    ? READ_ONLY_REASON
    : config.isError
      ? 'No se pudo leer la configuración de WhatsApp.'
      : (config.data?.reason ?? 'Cargando…');

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

  const doRefresh = (a: WaAccount) =>
    refresh.mutate(a.id, {
      onSuccess: (r) => notifySuccess(`${r.display_phone_number}: datos actualizados desde Meta.`),
      onError: (e) => notifyError(e, 'Meta no respondió'),
    });

  const showTemplates = (a: WaAccount) => {
    setTemplatesFor(a.id);
    document.getElementById('wa-templates')?.scrollIntoView({ behavior: 'smooth' });
  };

  const connectButton = (
    <Tooltip label={signupReason} multiline w={260} withArrow disabled={signupEnabled}>
      <Button
        leftSection={<IconBrandWhatsapp size={18} />}
        // Deshabilitado con data-disabled: un boton disabled no dispara el tooltip con el motivo.
        data-disabled={!signupEnabled || undefined}
        onClick={(e) => (signupEnabled ? setDialog({ kind: 'signup' }) : e.preventDefault())}
      >
        Conectar WhatsApp
      </Button>
    </Tooltip>
  );

  return (
    <>
      <PageHeader
        title="WhatsApp"
        description="Números de WhatsApp Business conectados por la Cloud API de Meta. Cada uno lo atiende un agente; responde texto y notas de voz."
        actions={
          <>
            {isAdmin && (
              <Button
                variant="default"
                leftSection={<IconPlus size={18} />}
                onClick={() => setDialog({ kind: 'manual' })}
              >
                Alta manual
              </Button>
            )}
            {connectButton}
          </>
        }
      />
      {config.data && !config.data.enabled && (
        <Alert color="gray" icon={<IconAlertTriangle size={18} />} mb="md">
          La conexión de números propios no está disponible: {config.data.reason}
          {isAdmin ? '' : '. Avisanos y la habilitamos.'}
        </Alert>
      )}
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
        <QueryState query={accounts}>
          {(rows) =>
            rows.length === 0 ? (
              <EmptyState>
                {clientId
                  ? 'Este cliente no tiene números de WhatsApp.'
                  : 'No hay números de WhatsApp. Usá "Conectar WhatsApp" para conectar uno propio.'}
              </EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={isAdmin ? 1180 : 960}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Número</Table.Th>
                      {isAdmin && <Table.Th>Cliente</Table.Th>}
                      <Table.Th>Agente</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Calidad</Table.Th>
                      {isAdmin && <Table.Th>Token</Table.Th>}
                      <Table.Th>Alta</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {rows.map((a) => (
                      <Table.Tr key={a.id}>
                        <Table.Td>
                          <Text size="sm" className="mono">
                            {a.display_phone_number}
                          </Text>
                          {a.name && <Text size="xs">{a.name}</Text>}
                          {isAdmin && (
                            <Text size="xs" c="dimmed" className="mono">
                              ID {a.phone_number_id}
                            </Text>
                          )}
                        </Table.Td>
                        {isAdmin && (
                          <Table.Td>
                            <Anchor component={Link} to={`/clients/${a.client_id}`} size="sm">
                              {a.client_name ?? 'Cliente'}
                            </Anchor>
                          </Table.Td>
                        )}
                        <Table.Td>
                          <WaAgentSelect account={a} />
                        </Table.Td>
                        <Table.Td>
                          <StatusCell account={a} />
                          <Text size="xs" c="dimmed" mt={2}>
                            {WA_SOURCE[a.source ?? 'manual'] ?? a.source}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <QualityCell account={a} />
                        </Table.Td>
                        {isAdmin && (
                          <Table.Td>
                            <Badge color="gray">{a.has_token ? 'Propio' : 'Global'}</Badge>
                          </Table.Td>
                        )}
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDate(a.created_at)}</Table.Td>
                        <Table.Td>
                          <Group justify="flex-end" wrap="nowrap">
                            <Menu position="bottom-end" withinPortal>
                              <Menu.Target>
                                <ActionIcon
                                  variant="subtle"
                                  color="gray"
                                  aria-label={`Acciones de ${a.display_phone_number}`}
                                >
                                  <IconDots size={16} />
                                </ActionIcon>
                              </Menu.Target>
                              <Menu.Dropdown>
                                {canManage(a) && (
                                  <>
                                    <Menu.Item
                                      leftSection={<IconTemplate size={16} />}
                                      onClick={() => showTemplates(a)}
                                    >
                                      Plantillas
                                    </Menu.Item>
                                    <Menu.Item
                                      leftSection={<IconRepeat size={16} />}
                                      disabled={a.status === 'disconnected' || readOnly}
                                      onClick={() => setDialog({ kind: 'register', account: a })}
                                    >
                                      Reintentar registro
                                    </Menu.Item>
                                    <Menu.Item
                                      leftSection={<IconRefresh size={16} />}
                                      disabled={a.status === 'disconnected'}
                                      onClick={() => doRefresh(a)}
                                    >
                                      Releer datos de Meta
                                    </Menu.Item>
                                  </>
                                )}
                                {isAdmin && (
                                  <Menu.Item
                                    leftSection={<IconPencil size={16} />}
                                    onClick={() => setDialog({ kind: 'edit', account: a })}
                                  >
                                    Editar
                                  </Menu.Item>
                                )}
                                {canManage(a) && <Menu.Divider />}
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
        <Text size="xs" c="dimmed" mt="md">
          Meta le cobra los mensajes a la cuenta de WhatsApp Business del número: el medio de pago se carga en{' '}
          <Anchor href={WA_MANAGER_URL} target="_blank" rel="noopener noreferrer" inherit>
            WhatsApp Manager
          </Anchor>
          .
        </Text>
      </Card>
      {manageable.length > 0 && (
        <TemplatesCard accounts={manageable} accountId={templatesAccount} onSelect={setTemplatesFor} />
      )}
      {dialog?.kind === 'signup' && config.data && (
        <SignupModal config={config.data} onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === 'manual' && <NewWaAccountModal onClose={() => setDialog(null)} />}
      {dialog?.kind === 'edit' && (
        <EditWaAccountModal account={dialog.account} onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === 'register' && (
        <RegisterModal account={dialog.account} onClose={() => setDialog(null)} />
      )}
    </>
  );
}
