import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  Pagination,
  Paper,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconClockPause,
  IconDownload,
  IconPencil,
  IconPlayerPause,
  IconPlayerPlay,
  IconUserPlus,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { Campaign, CampaignContact, CampaignStats } from '@/api/types';
import { Dash, LiveBadge } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, ErrorAlert, QueryState } from '@/components/QueryState';
import { TEMPLATE_CATEGORY } from '@/features/whatsapp/labels';
import { formatDateTime, formatDuration, formatNumber } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  CAMPAIGN_CONTACTS_PAGE,
  type CampaignAction,
  type ContactsFilter,
  reportUrl,
  useCampaign,
  useCampaignAction,
  useCampaignContacts,
  useCampaignStats,
  useDeleteCampaign,
} from './api';
import { AddContactsModal } from './CampaignModals';
import { CampaignChannelBadge, CampaignStatusBadge } from './CampaignsPage';
import { EditCampaignModal } from './EditCampaignModal';
import {
  CONTACT_RESULT,
  CONTACT_STATUS,
  contactLabel,
  FOLLOWUP_STATUS,
  formatEta,
  formatWeekdays,
  formatWindow,
  PURPOSE,
  pct,
  recipientError,
  renderTemplate,
} from './labels';

type Tone = 'red' | 'yellow' | undefined;
interface Tile {
  label: string;
  value: number | string;
  sub?: number | null;
  tone?: Tone;
}

const VOICE_RESULT_KEYS = [
  'answered',
  'no_answer',
  'busy',
  'voicemail',
  'invalid',
  'rejected',
  'failed',
] as const;

const sum = (r: Record<string, number>) => Object.values(r).reduce((a, b) => a + b, 0);
const open = (c: Campaign) => c.progress.pending + c.progress.in_progress + c.progress.retry;

/** Las tarjetas de numeros de la campaña: las de WhatsApp (enviado, entregado, leido...) o las de voz. */
function tilesFor(c: Campaign): Tile[] {
  const r = c.results;
  const p = c.progress;
  if (c.channel === 'whatsapp') {
    const sent = r.sent ?? 0;
    const delivered = r.delivered ?? 0;
    return [
      { label: 'Contactos', value: c.total },
      { label: 'Pendientes', value: open(c) },
      { label: 'Enviados', value: sent, sub: pct(sent, sent + p.failed) },
      { label: 'Entregados', value: delivered, sub: pct(delivered, sent) },
      { label: 'Leídos', value: r.read ?? 0, sub: pct(r.read ?? 0, delivered) },
      { label: 'Respondieron', value: r.replied ?? 0, sub: pct(r.replied ?? 0, delivered) },
      { label: 'Fallidos', value: p.failed, tone: p.failed ? 'red' : undefined },
      { label: 'Salteados', value: p.skipped, tone: p.skipped ? 'yellow' : undefined },
    ];
  }
  const reached = sum(r);
  const tiles: Tile[] = [
    { label: 'Contactos', value: c.total },
    { label: 'Pendientes', value: p.pending + p.retry, sub: null },
    { label: 'En curso', value: p.in_progress },
    ...VOICE_RESULT_KEYS.map((k) => ({
      label: CONTACT_RESULT[k].label,
      value: r[k] ?? 0,
      sub: k === 'answered' ? pct(r[k] ?? 0, reached) : undefined,
      tone: (k === 'failed' || k === 'invalid') && (r[k] ?? 0) > 0 ? ('red' as Tone) : undefined,
    })),
    { label: 'Salteados', value: p.skipped, tone: p.skipped ? ('yellow' as Tone) : undefined },
  ];
  if (c.goal != null)
    tiles.push({ label: 'Cumplieron el objetivo', value: c.goal, sub: pct(c.goal, r.answered ?? 0) });
  if (c.minutes_used != null) tiles.push({ label: 'Minutos', value: formatNumber(c.minutes_used, 1) });
  return tiles;
}

function Tiles({ tiles }: { tiles: Tile[] }) {
  return (
    <SimpleGrid cols={{ base: 2, sm: 4, lg: 6 }} spacing="md">
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

/** Barra de avance, ritmo estimado y si ahora se esta dentro del horario. */
function ProgressCard({ c }: { c: Campaign }) {
  const live = c.status === 'running';
  return (
    <Card>
      <Group justify="space-between" mb="sm" gap="sm">
        <Title order={4}>Avance</Title>
        {live && (
          <Group gap={6}>
            <LiveBadge>{c.in_window ? 'Dentro del horario' : 'Fuera de horario'}</LiveBadge>
          </Group>
        )}
      </Group>
      <Progress
        value={c.percent}
        size="lg"
        aria-label={`${Math.round(c.percent)} % procesado`}
        color={c.status === 'done' ? 'green' : 'blue'}
      />
      <Group justify="space-between" mt="xs" gap="sm">
        <Text size="sm">
          <Text span className="mono" fw={600}>
            {formatNumber(c.percent, 0)} %
          </Text>{' '}
          <Text span c="dimmed">
            · {c.progress.done + c.progress.failed + c.progress.skipped} de {c.total} contactos procesados
          </Text>
        </Text>
        {c.eta_minutes != null && c.status === 'running' && (
          <Text size="sm" c="dimmed">
            Faltan {formatEta(c.eta_minutes)} al ritmo actual
          </Text>
        )}
      </Group>
      {live && !c.in_window && (
        <Text size="xs" c="dimmed" mt="xs">
          Está en curso pero fuera del horario permitido ({formatWindow(c.window_start, c.window_end)},{' '}
          {formatWeekdays(c.weekdays).toLowerCase()}, feriados excluidos): sigue sola cuando vuelva a entrar.
        </Text>
      )}
    </Card>
  );
}

/** Indicadores de una campaña de voz: tasas, duracion y atendidas por hora. */
function StatsCard({ stats }: { stats: CampaignStats }) {
  if (stats.attempts === 0) return null;
  const max = Math.max(1, ...stats.by_hour.map((h) => h.attempts));
  const hours = stats.by_hour.filter((h) => h.attempts > 0);
  return (
    <Card>
      <Title order={4} mb="md">
        Indicadores
      </Title>
      <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md" mb="md">
        <Datum label="Llamadas marcadas">{formatNumber(stats.attempts, 0)}</Datum>
        <Datum label="Tasa de contacto">
          {formatNumber(stats.contact_rate, 0)} %{' '}
          <Text span size="xs" c="dimmed" fw={400}>
            ({stats.reached} atendidas)
          </Text>
        </Datum>
        <Datum label="Tasa de objetivo">{formatNumber(stats.goal_rate, 0)} % de las atendidas</Datum>
        <Datum label="Duración media">{formatDuration(stats.avg_duration_seconds)}</Datum>
      </SimpleGrid>
      <Text className="label" mb={6}>
        Atendidas por hora del día
      </Text>
      <Group gap={6} align="flex-end" wrap="nowrap" style={{ overflowX: 'auto' }} role="list">
        {hours.map((h) => (
          <Stack
            key={h.hour}
            gap={2}
            align="center"
            role="listitem"
            aria-label={`${h.hour} h: ${h.reached} de ${h.attempts} atendidas`}
          >
            <Text size="xs" className="mono">
              {h.reached}/{h.attempts}
            </Text>
            <div
              style={{
                height: 56,
                width: 20,
                display: 'flex',
                alignItems: 'flex-end',
                background: 'var(--app-surface-2)',
                borderRadius: 4,
              }}
            >
              <div
                style={{
                  width: '100%',
                  height: `${(h.reached / max) * 100}%`,
                  background: 'var(--mantine-color-blue-6)',
                  borderRadius: 4,
                }}
              />
            </div>
            <Text size="xs" c="dimmed" className="mono">
              {h.hour}
            </Text>
          </Stack>
        ))}
      </Group>
      <Text size="xs" c="dimmed" mt="xs">
        Hora de Argentina. La barra azul son las atendidas sobre las llamadas marcadas en esa hora.
      </Text>
    </Card>
  );
}

function FollowupCard({ c }: { c: Campaign }) {
  const f = (c.followup ?? {}) as Record<string, number>;
  const cfg = c.followup_config as { template_name?: string; after?: string[] } | null | undefined;
  return (
    <Card>
      <Title order={4} mb="xs">
        Seguimiento por WhatsApp
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        Plantilla <span className="mono">{cfg?.template_name}</span> para quien terminó en{' '}
        {(cfg?.after ?? []).map((r) => CONTACT_RESULT[r]?.label.toLowerCase() ?? r).join(', ')}.
      </Text>
      <SimpleGrid cols={{ base: 2, sm: 5 }} spacing="md">
        {Object.entries(FOLLOWUP_STATUS).map(([k, label]) => (
          <Datum key={k} label={label}>
            {f[k] ?? 0}
          </Datum>
        ))}
      </SimpleGrid>
    </Card>
  );
}

/** Filtros de la tabla de contactos, segun el canal. */
function contactFilters(channel: Campaign['channel']): (ContactsFilter & { label: string })[] {
  const status = (key: NonNullable<ContactsFilter['status']>) => ({
    key,
    status: key,
    label: CONTACT_STATUS[key].label,
  });
  const result = (key: string) => ({ key, result: key, label: CONTACT_RESULT[key].label });
  return channel === 'whatsapp'
    ? [
        status('pending'),
        result('sent'),
        result('delivered'),
        result('read'),
        result('replied'),
        result('failed'),
        status('skipped'),
      ]
    : [
        status('pending'),
        status('in_progress'),
        status('retry'),
        ...VOICE_RESULT_KEYS.map(result),
        status('skipped'),
      ];
}

function ContactsCard({ campaign }: { campaign: Campaign }) {
  const [key, setKey] = useState('');
  const [page, setPage] = useState(1);
  const filters = contactFilters(campaign.channel);
  const filter = filters.find((f) => f.key === key) ?? null;
  const contacts = useCampaignContacts(
    campaign.id,
    filter,
    (page - 1) * CAMPAIGN_CONTACTS_PAGE,
    campaign.status === 'running' || campaign.status === 'scheduled',
  );
  const total = contacts.data?.total ?? 0;
  const voice = campaign.channel === 'voice';

  return (
    <Card>
      <Group justify="space-between" mb="md" gap="sm">
        <Title order={4}>Contactos</Title>
        <Select
          data={[{ value: '', label: 'Todos' }, ...filters.map((f) => ({ value: f.key, label: f.label }))]}
          value={key}
          onChange={(v) => {
            setKey(v ?? '');
            setPage(1);
          }}
          allowDeselect={false}
          w={200}
          aria-label="Filtrar por estado"
        />
      </Group>
      <QueryState query={contacts}>
        {(data) =>
          data.items.length === 0 ? (
            <EmptyState>
              {filter ? 'No hay contactos en ese estado.' : 'La campaña no tiene contactos.'}
            </EmptyState>
          ) : (
            <>
              <Table.ScrollContainer minWidth={voice ? 860 : 820}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Teléfono</Table.Th>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>{voice ? 'Intentos' : 'Mensaje'}</Table.Th>
                      <Table.Th>Resultado</Table.Th>
                      <Table.Th>{voice ? 'Último intento' : 'Enviado'}</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {data.items.map((r) => (
                      <ContactRow key={r.id} r={r} campaign={campaign} />
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
              {total > CAMPAIGN_CONTACTS_PAGE && (
                <Group justify="flex-end" mt="md">
                  <Pagination
                    total={Math.ceil(total / CAMPAIGN_CONTACTS_PAGE)}
                    value={page}
                    onChange={setPage}
                  />
                </Group>
              )}
            </>
          )
        }
      </QueryState>
    </Card>
  );
}

function ContactRow({ r, campaign }: { r: CampaignContact; campaign: Campaign }) {
  const voice = campaign.channel === 'voice';
  const l = contactLabel(r);
  const error = recipientError(r.error);
  const bad = r.status === 'failed' || r.result === 'failed' || r.result === 'invalid';
  const params = Array.isArray(r.vars?.params) ? (r.vars.params as string[]) : [];
  const when = voice ? r.last_attempt_at : r.sent_at;
  return (
    <Table.Tr>
      <Table.Td className="mono">{r.phone}</Table.Td>
      <Table.Td>{r.name ?? <Dash />}</Table.Td>
      <Table.Td>
        {voice ? (
          <Text size="sm" className="mono">
            {r.attempts}
            {campaign.max_attempts ? ` / ${campaign.max_attempts}` : ''}
          </Text>
        ) : (
          <Text size="sm" lineClamp={2} maw={320}>
            {campaign.template_body ? renderTemplate(campaign.template_body, params) : <Dash />}
          </Text>
        )}
      </Table.Td>
      <Table.Td>
        <Badge color={l.color}>{l.label}</Badge>
        {r.status === 'retry' && r.next_attempt_at && (
          <Text size="xs" c="dimmed" mt={2}>
            Reintenta {formatDateTime(r.next_attempt_at)}
          </Text>
        )}
        {error && (
          <Text size="xs" c={bad ? 'red' : 'dimmed'} mt={2} maw={260}>
            {error}
          </Text>
        )}
      </Table.Td>
      <Table.Td style={{ whiteSpace: 'nowrap' }}>{when ? formatDateTime(when) : <Dash />}</Table.Td>
      <Table.Td>
        {r.conversation_id && (
          <Anchor component={Link} to={`/calls/${r.conversation_id}`} size="sm">
            Ver conversación
          </Anchor>
        )}
      </Table.Td>
    </Table.Tr>
  );
}

/** Una campaña comercial se inicia con la confirmacion del Registro No Llame (Ley 26.951). */
function RegistryModal({
  campaign,
  onConfirm,
  onClose,
  loading,
}: {
  campaign: Campaign;
  onConfirm: () => void;
  onClose: () => void;
  loading: boolean;
}) {
  const [checked, setChecked] = useState(false);
  return (
    <Modal opened onClose={onClose} title={`Iniciar ${campaign.name}`}>
      <Stack>
        <Text size="sm">
          Es una campaña comercial. Las llamadas de publicidad a quienes están en el Registro No Llame están
          prohibidas (Ley 26.951), y la lista es responsabilidad del cliente.
        </Text>
        <Checkbox
          label="Confirmo que filtré la lista contra el Registro No Llame"
          checked={checked}
          onChange={(e) => setChecked(e.currentTarget.checked)}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={!checked} loading={loading} onClick={onConfirm}>
            {campaign.status === 'paused' ? 'Retomar campaña' : 'Iniciar campaña'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function CampaignDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const query = useCampaign(id);
  const stats = useCampaignStats(id, query.data?.status === 'running' && query.data.channel === 'voice');
  const action = useCampaignAction(id);
  const remove = useDeleteCampaign();
  const [dialog, setDialog] = useState<'edit' | 'add' | 'registry' | null>(null);

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

  const run = (kind: CampaignAction, done: string, registryChecked = false) =>
    action.mutate(
      { action: kind, registryChecked },
      {
        onSuccess: () => {
          notifySuccess(done);
          setDialog(null);
        },
        onError: (e) => notifyError(e, 'No se pudo completar'),
      },
    );

  const doCancel = async (c: Campaign) => {
    const ok = await confirmAction({
      title: `Cancelar la campaña ${c.name}`,
      message:
        c.channel === 'voice'
          ? `Los ${open(c)} contactos pendientes no se llaman. Las llamadas en curso terminan solas.`
          : `Los ${open(c)} contactos pendientes no reciben el mensaje. Las respuestas de los que ya lo recibieron siguen llegando al agente.`,
      confirmLabel: 'Cancelar campaña',
      danger: true,
    });
    if (ok) run('cancel', 'Campaña cancelada.');
  };

  const doDelete = async (c: Campaign) => {
    const ok = await confirmAction({
      title: `Borrar la campaña ${c.name}`,
      message: 'Se borran la campaña y sus contactos. Todavía no se hizo nada con ellos.',
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

  /** Iniciar (borrador) o retomar (pausada). Una comercial sin confirmar pide el Registro No Llame. */
  const launch = (c: Campaign) => {
    const kind: CampaignAction = c.status === 'paused' ? 'resume' : 'start';
    if (c.purpose === 'comercial' && !c.registry_confirmed) setDialog('registry');
    else
      run(
        kind,
        kind === 'resume'
          ? 'Campaña retomada.'
          : c.starts_at && new Date(c.starts_at) > new Date()
            ? 'Campaña programada.'
            : 'Campaña iniciada.',
      );
  };

  return (
    <QueryState query={query}>
      {(c) => {
        const voice = c.channel === 'voice';
        const editable = c.status === 'draft' || c.status === 'paused';
        const finished = c.status === 'done' || c.status === 'cancelled';
        const live = c.status === 'running' || c.status === 'scheduled';
        const startLabel = c.status === 'paused' ? 'Retomar' : voice ? 'Iniciar campaña' : 'Iniciar envío';
        return (
          <Stack gap="md">
            <PageHeader
              above={back}
              docTitle={c.name}
              title={
                <Group gap="sm" component="span">
                  {c.name}
                  <CampaignStatusBadge campaign={c} />
                  <CampaignChannelBadge channel={c.channel} />
                </Group>
              }
              description={
                voice
                  ? `Llamadas del agente ${c.agent_name ?? '–'}`
                  : `Plantilla ${c.template_name} por ${c.display_phone_number ?? 'WhatsApp'}`
              }
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
                  {c.total > 0 && c.status !== 'draft' && (
                    <Button
                      component="a"
                      href={reportUrl(c.id)}
                      download
                      variant="default"
                      leftSection={<IconDownload size={18} />}
                    >
                      Descargar reporte
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
                        disabled={c.total === 0}
                        onClick={() => launch(c)}
                      >
                        {startLabel}
                      </Button>
                    </>
                  )}
                  {live && (
                    <Button
                      variant="default"
                      leftSection={<IconPlayerPause size={18} />}
                      loading={action.isPending}
                      onClick={() => run('pause', voice ? 'Campaña pausada.' : 'Envío pausado.')}
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
            {c.status === 'scheduled' && (
              <Alert color="blue" icon={<IconClockPause size={18} />}>
                {c.starts_at
                  ? `Arranca sola el ${formatDateTime(c.starts_at)}.`
                  : 'Arranca sola dentro del horario permitido.'}
              </Alert>
            )}
            {c.status === 'draft' && c.total === 0 && (
              <Alert color="gray">
                Todavía no tiene contactos: usá "Agregar contactos" para poder iniciarla.
              </Alert>
            )}
            <ProgressCard c={c} />
            <Tiles tiles={tilesFor(c)} />
            {voice && stats.data && <StatsCard stats={stats.data} />}
            {voice && c.followup_config && <FollowupCard c={c} />}
            <Card>
              <Title order={4} mb="md">
                {voice ? 'Configuración' : 'Mensaje'}
              </Title>
              {!voice && (
                <Paper p="sm" bg="var(--app-surface-2)" mb="md">
                  <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
                    {c.template_body}
                  </Text>
                </Paper>
              )}
              <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} spacing="md">
                <Datum label={voice ? 'Llama' : 'Responde'}>{c.agent_name ?? <Dash />}</Datum>
                <Datum label="Horario">
                  {formatWindow(c.window_start, c.window_end)}
                  <Text span size="xs" c="dimmed" fw={400} display="block">
                    {formatWeekdays(c.weekdays)}
                  </Text>
                </Datum>
                <Datum label="Ritmo">
                  {c.rate_per_minute} {voice ? 'llamadas' : ''} por minuto
                </Datum>
                {voice ? (
                  <>
                    <Datum label="Modo">
                      {(c.concurrency ?? 1) > 1 ? `En paralelo (${c.concurrency} a la vez)` : 'De a una'}
                    </Datum>
                    <Datum label="Reintentos">
                      {c.max_attempts} {c.max_attempts === 1 ? 'intento' : 'intentos'}, cada {c.retry_minutes}{' '}
                      min
                      <Text span size="xs" c="dimmed" fw={400} display="block">
                        si{' '}
                        {(c.retry_on ?? [])
                          .map((r) => CONTACT_RESULT[r]?.label.toLowerCase() ?? r)
                          .join(', ') || '–'}
                      </Text>
                    </Datum>
                    <Datum label="Voz">{c.voice ?? 'La del agente'}</Datum>
                  </>
                ) : (
                  <Datum label="Categoría">
                    {(c.template_category && TEMPLATE_CATEGORY[c.template_category]) ??
                      c.template_category ?? <Dash />}
                  </Datum>
                )}
                <Datum label="Inicio programado">
                  {c.starts_at ? formatDateTime(c.starts_at) : <Dash />}
                </Datum>
                <Datum label="Termina como máximo">{c.ends_at ? formatDateTime(c.ends_at) : <Dash />}</Datum>
                <Datum label="Inicio">{c.started_at ? formatDateTime(c.started_at) : <Dash />}</Datum>
                <Datum label="Fin">{c.finished_at ? formatDateTime(c.finished_at) : <Dash />}</Datum>
                <Datum label="Finalidad">
                  {c.purpose ? (PURPOSE[c.purpose] ?? c.purpose) : <Dash />}
                  {c.purpose === 'comercial' && (
                    <Text span size="xs" c="dimmed" fw={400} display="block">
                      {c.registry_confirmed
                        ? 'Registro No Llame confirmado'
                        : 'Falta confirmar el Registro No Llame'}
                    </Text>
                  )}
                </Datum>
                {c.callback_url && (
                  <Datum label="Webhook">
                    <Text span className="mono" size="xs" style={{ wordBreak: 'break-all' }}>
                      {c.callback_url}
                    </Text>
                  </Datum>
                )}
              </SimpleGrid>
              <Text size="xs" c="dimmed" mt="md">
                {voice
                  ? 'Llama solo dentro del horario (hora de Argentina). Cada llamada aparece en Conversaciones.'
                  : 'Se envía solo dentro del horario (hora de Argentina). Cuando un contacto responde, la conversación aparece en Conversaciones y la atiende el agente.'}
              </Text>
            </Card>
            <ContactsCard campaign={c} />
            {dialog === 'edit' && <EditCampaignModal campaign={c} onClose={() => setDialog(null)} />}
            {dialog === 'add' && <AddContactsModal campaign={c} onClose={() => setDialog(null)} />}
            {dialog === 'registry' && (
              <RegistryModal
                campaign={c}
                loading={action.isPending}
                onClose={() => setDialog(null)}
                onConfirm={() =>
                  run(
                    c.status === 'paused' ? 'resume' : 'start',
                    c.status === 'paused' ? 'Campaña retomada.' : 'Campaña iniciada.',
                    true,
                  )
                }
              />
            )}
          </Stack>
        );
      }}
    </QueryState>
  );
}
