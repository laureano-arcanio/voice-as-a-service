import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Pagination,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconPencil,
  IconPlayerPause,
  IconPlayerPlay,
  IconUserPlus,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { WaCampaign } from '@/api/types';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, ErrorAlert, QueryState } from '@/components/QueryState';
import { useAgents } from '@/features/agents/api';
import { useIsAdmin } from '@/features/auth/api';
import { useReadOnly } from '@/features/auth/readOnly';
import { TEMPLATE_CATEGORY } from '@/features/whatsapp/labels';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  RECIPIENTS_PAGE,
  useCampaign,
  useCampaignAction,
  useDeleteCampaign,
  useRecipients,
  useUpdateCampaign,
} from './api';
import { AddRecipientsModal } from './CampaignModals';
import { CampaignStatusBadge } from './CampaignsPage';
import { formatWindow, pct, RECIPIENT_STATUS, recipientError, renderTemplate } from './labels';

const FILTERS = [
  { value: '', label: 'Todos' },
  ...['pending', 'sent', 'delivered', 'read', 'replied', 'failed', 'skipped'].map((s) => ({
    value: s,
    label: RECIPIENT_STATUS[s].label,
  })),
];

function Tiles({ c }: { c: WaCampaign }) {
  const s = c.stats;
  const tiles = [
    { label: 'Contactos', value: s.total },
    { label: 'Pendientes', value: s.pending },
    { label: 'Enviados', value: s.sent, sub: pct(s.sent, s.total - s.pending - s.skipped) },
    { label: 'Entregados', value: s.delivered, sub: pct(s.delivered, s.sent) },
    { label: 'Leídos', value: s.read, sub: pct(s.read, s.delivered) },
    { label: 'Respondieron', value: s.replied, sub: pct(s.replied, s.delivered) },
    { label: 'Fallidos', value: s.failed, tone: s.failed ? 'red' : undefined },
    { label: 'Bajas', value: s.opted_out, tone: s.opted_out ? 'yellow' : undefined },
  ];
  return (
    <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
      {tiles.map((t) => (
        <Card key={t.label} padding="md">
          <Stack gap={6}>
            <Text className="label">{t.label}</Text>
            <Text className="metric" c={t.tone}>
              {t.value}
              {t.sub !== undefined && t.sub !== null && (
                <Text span size="sm" fw={500} c="dimmed" ff="text" ml={8} style={{ letterSpacing: 0 }}>
                  {t.sub} %
                </Text>
              )}
            </Text>
          </Stack>
        </Card>
      ))}
    </SimpleGrid>
  );
}

function Datum({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600} component="div">
        {children}
      </Text>
    </Stack>
  );
}

function EditCampaignModal({ campaign, onClose }: { campaign: WaCampaign; onClose: () => void }) {
  const update = useUpdateCampaign(campaign.id);
  const agents = useAgents(campaign.client_id, false);
  const form = useForm({
    initialValues: {
      name: campaign.name,
      agent_id: campaign.agent_id ?? '',
      window_start: campaign.window_start,
      window_end: campaign.window_end,
      rate_per_minute: campaign.rate_per_minute,
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Requerido'),
      window_end: (v, values) => (v > values.window_start ? null : 'Tiene que ser después del inicio'),
    },
  });
  return (
    <Modal opened onClose={onClose} title="Editar campaña">
      <form
        onSubmit={form.onSubmit((v) =>
          update.mutate(
            { ...v, name: v.name.trim(), agent_id: v.agent_id || null },
            {
              onSuccess: () => {
                notifySuccess('Campaña guardada.');
                onClose();
              },
              onError: (e) => notifyError(e, 'No se pudo guardar'),
            },
          ),
        )}
      >
        <Stack>
          <TextInput label="Nombre" {...form.getInputProps('name')} />
          <Select
            label="Agente que responde"
            placeholder="El del número"
            data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
            clearable
            searchable
            {...form.getInputProps('agent_id')}
            onChange={(v) => form.setFieldValue('agent_id', v ?? '')}
          />
          <Group grow align="flex-start">
            <NumberInput label="Desde (hora)" min={0} max={23} {...form.getInputProps('window_start')} />
            <NumberInput label="Hasta (hora)" min={1} max={24} {...form.getInputProps('window_end')} />
            <NumberInput
              label="Mensajes por minuto"
              min={1}
              max={600}
              {...form.getInputProps('rate_per_minute')}
            />
          </Group>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={update.isPending}>
              Guardar cambios
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function RecipientsCard({ campaign }: { campaign: WaCampaign }) {
  const isAdmin = useIsAdmin();
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const recipients = useRecipients(
    campaign.id,
    status || null,
    (page - 1) * RECIPIENTS_PAGE,
    campaign.status === 'running',
  );
  const total = recipients.data?.total ?? 0;

  return (
    <Card>
      <Group justify="space-between" mb="md" gap="sm">
        <Title order={4}>Contactos</Title>
        <Select
          data={FILTERS}
          value={status}
          onChange={(v) => {
            setStatus(v ?? '');
            setPage(1);
          }}
          allowDeselect={false}
          w={180}
          aria-label="Filtrar por estado"
        />
      </Group>
      <QueryState query={recipients}>
        {(data) =>
          data.items.length === 0 ? (
            <EmptyState>
              {status ? 'No hay contactos en ese estado.' : 'La campaña no tiene contactos.'}
            </EmptyState>
          ) : (
            <>
              <Table.ScrollContainer minWidth={820}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Teléfono</Table.Th>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>Mensaje</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Enviado</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.items.map((r) => {
                      const l = RECIPIENT_STATUS[r.status] ?? { label: r.status, color: 'gray' };
                      const error = recipientError(r.error);
                      return (
                        <Table.Tr key={r.id}>
                          <Table.Td className="mono">{r.wa_id}</Table.Td>
                          <Table.Td>{r.name ?? <Dash />}</Table.Td>
                          <Table.Td>
                            <Text size="sm" lineClamp={2} maw={320}>
                              {renderTemplate(campaign.template_body, r.params)}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Badge color={l.color}>{l.label}</Badge>
                            {error && (
                              <Text size="xs" c={r.status === 'failed' ? 'red' : 'dimmed'} mt={2} maw={260}>
                                {error}
                                {isAdmin && r.error?.code ? (
                                  <Text span className="mono" inherit>
                                    {' '}
                                    ({String(r.error.code)})
                                  </Text>
                                ) : null}
                              </Text>
                            )}
                          </Table.Td>
                          <Table.Td style={{ whiteSpace: 'nowrap' }}>
                            {r.sent_at ? formatDateTime(r.sent_at) : <Dash />}
                          </Table.Td>
                          <Table.Td>
                            {r.conversation_id && (
                              <Anchor component={Link} to={`/calls/${r.conversation_id}`} size="sm">
                                Ver conversación
                              </Anchor>
                            )}
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
              {total > RECIPIENTS_PAGE && (
                <Group justify="flex-end" mt="md">
                  <Pagination total={Math.ceil(total / RECIPIENTS_PAGE)} value={page} onChange={setPage} />
                </Group>
              )}
            </>
          )
        }
      </QueryState>
    </Card>
  );
}

export function CampaignDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const query = useCampaign(id);
  const action = useCampaignAction(id);
  const remove = useDeleteCampaign();
  // Solo lectura: enviar consume (mensajes de Meta y respuestas del agente).
  const readOnly = useReadOnly();
  const [dialog, setDialog] = useState<'edit' | 'add' | null>(null);

  const back = (
    <Button
      component={Link}
      to="/campaigns"
      variant="subtle"
      size="compact-sm"
      leftSection={<IconArrowLeft size={16} />}
      w="fit-content"
    >
      Campañas
    </Button>
  );

  if (query.isError) {
    const gone = query.error instanceof ApiError && query.error.status === 404;
    return (
      <>
        <PageHeader title="Campaña" above={back} />
        <ErrorAlert error={gone ? new Error('La campaña no existe o no tenés acceso.') : query.error} />
      </>
    );
  }

  const run = (kind: 'start' | 'pause' | 'cancel', done: string) =>
    action.mutate(kind, {
      onSuccess: () => notifySuccess(done),
      onError: (e) => notifyError(e, 'No se pudo completar'),
    });

  const doCancel = async (c: WaCampaign) => {
    const ok = await confirmAction({
      title: `Cancelar la campaña ${c.name}`,
      message: `Los ${c.stats.pending} contactos pendientes no reciben el mensaje. Las respuestas de los que ya lo recibieron siguen llegando al agente.`,
      confirmLabel: 'Cancelar campaña',
      danger: true,
    });
    if (ok) run('cancel', 'Campaña cancelada.');
  };

  const doDelete = async (c: WaCampaign) => {
    const ok = await confirmAction({
      title: `Borrar la campaña ${c.name}`,
      message: 'Se borran la campaña y sus contactos. Todavía no se mandó nada.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      remove.mutate(c.id, {
        onSuccess: () => {
          notifySuccess('Campaña borrada.');
          navigate('/campaigns');
        },
        onError: (e) => notifyError(e),
      });
  };

  return (
    <QueryState query={query}>
      {(c) => {
        const editable = c.status === 'draft' || c.status === 'paused';
        const finished = c.status === 'done' || c.status === 'cancelled';
        return (
          <Stack gap="md">
            <PageHeader
              above={back}
              docTitle={c.name}
              title={
                <Group gap="sm" component="span">
                  {c.name}
                  <CampaignStatusBadge campaign={c} />
                </Group>
              }
              description={`Plantilla ${c.template_name} por ${c.display_phone_number ?? 'WhatsApp'}`}
              actions={
                <>
                  {c.status === 'draft' && (
                    <Button variant="subtle" color="red" onClick={() => void doDelete(c)}>
                      Borrar
                    </Button>
                  )}
                  {!finished && c.status !== 'draft' && (
                    <Button variant="subtle" color="red" onClick={() => void doCancel(c)}>
                      Cancelar campaña
                    </Button>
                  )}
                  {editable && (
                    <>
                      <Button
                        variant="default"
                        leftSection={<IconPencil size={18} />}
                        onClick={() => setDialog('edit')}
                      >
                        Editar
                      </Button>
                      <Button
                        variant="default"
                        leftSection={<IconUserPlus size={18} />}
                        onClick={() => setDialog('add')}
                      >
                        Agregar contactos
                      </Button>
                      <Button
                        leftSection={<IconPlayerPlay size={18} />}
                        loading={action.isPending}
                        disabled={c.stats.pending === 0 || readOnly}
                        onClick={() => run('start', 'Envío iniciado.')}
                      >
                        {c.status === 'paused' ? 'Retomar envío' : 'Iniciar envío'}
                      </Button>
                    </>
                  )}
                  {c.status === 'running' && (
                    <Button
                      variant="default"
                      leftSection={<IconPlayerPause size={18} />}
                      loading={action.isPending}
                      onClick={() => run('pause', 'Envío pausado.')}
                    >
                      Pausar
                    </Button>
                  )}
                </>
              }
            />
            {c.status === 'paused' && c.status_reason && (
              <Alert color="yellow" icon={<IconAlertTriangle size={18} />} title="Pausada automáticamente">
                {c.status_reason}
              </Alert>
            )}
            <Tiles c={c} />
            <Card>
              <Title order={4} mb="md">
                Mensaje
              </Title>
              <Paper p="sm" bg="var(--app-surface-2)" mb="md">
                <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
                  {c.template_body}
                </Text>
              </Paper>
              <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} spacing="md">
                <Datum label="Responde">{c.agent_name ?? <Dash />}</Datum>
                <Datum label="Horario">{formatWindow(c.window_start, c.window_end)}</Datum>
                <Datum label="Ritmo">{c.rate_per_minute} por minuto</Datum>
                <Datum label="Categoría">
                  {TEMPLATE_CATEGORY[c.template_category] ?? c.template_category}
                </Datum>
                <Datum label="Inicio">{c.started_at ? formatDateTime(c.started_at) : <Dash />}</Datum>
                <Datum label="Fin">{c.finished_at ? formatDateTime(c.finished_at) : <Dash />}</Datum>
              </SimpleGrid>
              <Text size="xs" c="dimmed" mt="md">
                Se envía solo dentro del horario (hora de Argentina). Cuando un contacto responde, la
                conversación aparece en Conversaciones y la atiende el agente.
              </Text>
            </Card>
            <RecipientsCard campaign={c} />
            {dialog === 'edit' && <EditCampaignModal campaign={c} onClose={() => setDialog(null)} />}
            {dialog === 'add' && (
              <AddRecipientsModal
                campaignId={c.id}
                vars={c.template_params}
                onClose={() => setDialog(null)}
              />
            )}
          </Stack>
        );
      }}
    </QueryState>
  );
}
