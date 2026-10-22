import {
  Badge,
  Card,
  Group,
  Pagination,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useSearchParams } from 'react-router';
import type { ApiRequest, ApiRequestPage } from '@/api/types';
import { Dash } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { useCurrentUser, useIsAdmin } from '@/features/auth/api';
import { useApiKeys, useClients } from '@/features/clients/api';
import { formatDate, formatDateTimeLong, formatMs, formatNumber, lastDays, toIsoDate } from '@/lib/format';
import { API_KIND, API_REQUEST_STATUS } from '@/lib/labels';
import { useApiRequests, type ApiKind, type ApiRequestStatus } from './api';

export const PAGE_SIZE = 50;

const RANGES = [
  { value: '1', label: 'Hoy' },
  { value: '7', label: 'Última semana' },
  { value: '30', label: 'Último mes' },
  { value: 'custom', label: 'Rango de fechas' },
];

const MODES = [
  { value: '', label: 'Todos' },
  { value: 'true', label: 'Con streaming' },
  { value: 'false', label: 'Sin streaming' },
];

const options = (labels: Record<string, { label: string }>, all: string) => [
  { value: '', label: all },
  ...Object.entries(labels).map(([value, l]) => ({ value, label: l.label })),
];

/** Filtros en la URL (se pueden compartir y sobreviven al refresco). */
function useFilters() {
  const [params, setParams] = useSearchParams();
  const range = RANGES.some((r) => r.value === params.get('range')) ? params.get('range')! : '7';
  const filters = {
    client: params.get('client'),
    key: params.get('key'),
    kind: params.get('kind') as ApiKind | null,
    status: params.get('status') as ApiRequestStatus | null,
    stream: params.get('stream'),
    range,
    from: params.get('from'),
    to: params.get('to'),
    page: Math.max(1, Number(params.get('page')) || 1),
  };
  type Filters = typeof filters;
  const update = (patch: Partial<Filters>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(patch)) {
          if (v == null || v === '' || (k === 'range' && v === '7') || (k === 'page' && v === 1))
            next.delete(k);
          else next.set(k, String(v));
        }
        if (!('page' in patch)) next.delete('page');
        return next;
      },
      { replace: true },
    );
  const dates =
    range === 'custom'
      ? filters.from && filters.to
        ? { from: filters.from, to: filters.to }
        : lastDays(7)
      : lastDays(Number(range));
  return { filters, update, dates };
}

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <Text className="label">{label}</Text>
      <Group align="baseline" wrap="wrap" gap={6}>
        <Text className="metric">{value}</Text>
        {hint && (
          <Text size="sm" c="dimmed">
            {hint}
          </Text>
        )}
      </Group>
    </Card>
  );
}

function Summary({ summary }: { summary: ApiRequestPage['summary'] }) {
  const failed = summary.by_status.error + summary.by_status.cut + summary.by_status.rejected;
  return (
    <SimpleGrid type="container" cols={{ base: 1, '420px': 2, '900px': 5 }} spacing="md">
      <Metric
        label="Pedidos"
        value={formatNumber(summary.requests, 0)}
        hint={failed ? `${formatNumber(failed, 0)} sin completar` : undefined}
      />
      <Metric
        label="LLM · tokens"
        value={formatNumber(summary.input_tokens + summary.output_tokens, 0)}
        hint={`${formatNumber(summary.input_tokens, 0)} ent. / ${formatNumber(summary.output_tokens, 0)} sal.`}
      />
      <Metric label="Transcripción" value={`${formatNumber(summary.stt_seconds / 60, 2)} min`} />
      <Metric label="Síntesis de voz" value={`${formatNumber(summary.tts_seconds / 60, 2)} min`} />
      <Metric
        label="Duración promedio"
        value={formatMs(summary.avg_duration_ms)}
        hint={summary.avg_duration_ms == null ? undefined : 'completados'}
      />
    </SimpleGrid>
  );
}

/** Lo que se descontó del plan: tokens del LLM o segundos de audio. */
export function Consumption({ r }: { r: ApiRequest }) {
  if (r.kind === 'llm') {
    if (r.input_tokens == null && r.output_tokens == null) return <Dash />;
    return (
      <>
        {formatNumber(r.input_tokens ?? 0, 0)} / {formatNumber(r.output_tokens ?? 0, 0)}
        <Text size="xs" c="dimmed">
          tokens ent. / sal.
        </Text>
      </>
    );
  }
  if (r.audio_seconds == null) return <Dash />;
  return (
    <>
      {formatNumber(r.audio_seconds, 1)} s
      <Text size="xs" c="dimmed">
        {r.kind === 'tts' && r.characters != null
          ? `de audio · ${formatNumber(r.characters, 0)} caracteres`
          : 'de audio'}
      </Text>
    </>
  );
}

function StatusCell({ r, isAdmin }: { r: ApiRequest; isAdmin: boolean }) {
  const l = API_REQUEST_STATUS[r.status];
  const badge = <Badge color={l.color}>{l.label}</Badge>;
  if (!r.error_code) return badge;
  // El codigo es el mismo que recibio el sistema del cliente en la respuesta (docs/API_INFERENCIA.md).
  return isAdmin ? (
    <Stack gap={2} align="flex-start">
      {badge}
      <Text size="xs" c="dimmed" className="mono">
        {r.http_status} {r.error_code}
      </Text>
    </Stack>
  ) : (
    <Tooltip label={`HTTP ${r.http_status} · ${r.error_code}`} withArrow>
      {badge}
    </Tooltip>
  );
}

function RequestsTable({
  page,
  isAdmin,
  showClient,
  current,
  onPage,
}: {
  page: ApiRequestPage;
  isAdmin: boolean;
  showClient: boolean;
  current: number;
  onPage: (p: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(page.total / PAGE_SIZE));
  return (
    <Card>
      <Group gap="xs" mb="sm">
        <Title order={4}>Pedidos</Title>
        <Badge color="gray">{page.total}</Badge>
      </Group>
      {!page.items.length ? (
        <EmptyState>
          {isAdmin
            ? 'Sin pedidos con estos filtros.'
            : 'No hay pedidos con estos filtros. Los que hagan tus sistemas con una API key aparecen acá.'}
        </EmptyState>
      ) : (
        <Table.ScrollContainer minWidth={isAdmin ? 980 : 720}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                {showClient && <Table.Th>Cliente</Table.Th>}
                <Table.Th>API key</Table.Th>
                <Table.Th>Tipo</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th ta="right">Duración</Table.Th>
                {isAdmin && <Table.Th ta="right">Primer byte</Table.Th>}
                <Table.Th ta="right">Consumo</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {page.items.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td className="mono" style={{ whiteSpace: 'nowrap' }}>
                    {formatDateTimeLong(r.created_at)}
                  </Table.Td>
                  {showClient && <Table.Td>{r.client_name}</Table.Td>}
                  <Table.Td>
                    {r.api_key_name ?? <Dash />}
                    {r.api_key_prefix && (
                      <Text size="xs" c="dimmed" className="mono">
                        {r.api_key_prefix}…
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Badge color="gray">{API_KIND[r.kind].label}</Badge>
                    {(r.stream || r.voice || (isAdmin && r.response_format)) && (
                      <Text size="xs" c="dimmed">
                        {[r.stream && 'streaming', r.voice, isAdmin && r.response_format]
                          .filter(Boolean)
                          .join(' · ')}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <StatusCell r={r} isAdmin={isAdmin} />
                  </Table.Td>
                  <Table.Td ta="right" className="mono">
                    {formatMs(r.duration_ms)}
                  </Table.Td>
                  {isAdmin && (
                    <Table.Td ta="right" className="mono">
                      {r.ttfb_ms == null ? <Dash /> : formatMs(r.ttfb_ms)}
                    </Table.Td>
                  )}
                  <Table.Td ta="right" className="mono" style={{ whiteSpace: 'nowrap' }}>
                    <Consumption r={r} />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
      {pages > 1 && (
        <Group justify="flex-end" mt="sm">
          <Pagination total={pages} value={Math.min(current, pages)} onChange={onPage} size="sm" />
        </Group>
      )}
    </Card>
  );
}

/** Pedidos a la API de inferencia (LLM, STT y TTS por API key), uno por uno: el admin ve los de
 * todos los clientes; el cliente, los suyos. No incluye los agentes integrados. */
export function ApiRequestsPage() {
  const isAdmin = useIsAdmin();
  const me = useCurrentUser();
  const { filters, update, dates } = useFilters();
  const clientId = isAdmin ? (filters.client ?? undefined) : (me.client_id ?? undefined);
  const clients = useClients(isAdmin);
  const keys = useApiKeys(clientId);
  const inferenceKeys = (keys.data ?? []).filter((k) => k.scopes.some((s) => s !== 'calls'));
  const requests = useApiRequests({
    client_id: isAdmin ? clientId : undefined,
    api_key_id: filters.key ?? undefined,
    kind: filters.kind ? [filters.kind] : undefined,
    status: filters.status ? [filters.status] : undefined,
    stream: filters.stream == null ? undefined : filters.stream === 'true',
    date_from: dates.from,
    date_to: dates.to,
    limit: PAGE_SIZE,
    offset: (filters.page - 1) * PAGE_SIZE,
  });

  return (
    <Stack gap="md">
      <PageHeader
        title="Uso de la API"
        description={`Cada pedido a la API de LLM, transcripción y síntesis de voz, con su duración y consumo, del ${formatDate(`${dates.from}T00:00:00`)} al ${formatDate(`${dates.to}T00:00:00`)}. No incluye las llamadas ni WhatsApp.`}
      />
      <Card>
        <Group gap="sm" align="flex-end" wrap="wrap">
          {isAdmin && (
            <Select
              label="Cliente"
              data={[
                { value: '', label: 'Todos' },
                ...(clients.data ?? []).map((c) => ({ value: c.id, label: c.name })),
              ]}
              value={filters.client ?? ''}
              onChange={(v) => update({ client: v || null, key: null })}
              allowDeselect={false}
              searchable
              w={200}
            />
          )}
          <Select
            label="API key"
            data={[
              { value: '', label: 'Todas' },
              ...inferenceKeys.map((k) => ({
                value: k.id,
                label: `${k.name} (${k.prefix}…)${k.revoked_at ? ' · revocada' : ''}`,
              })),
            ]}
            value={filters.key ?? ''}
            onChange={(v) => update({ key: v || null })}
            allowDeselect={false}
            disabled={!clientId}
            searchable
            w={220}
          />
          <Select
            label="Tipo"
            data={options(API_KIND, 'Todos')}
            value={filters.kind ?? ''}
            onChange={(v) => update({ kind: (v || null) as ApiKind | null })}
            allowDeselect={false}
            w={170}
          />
          <Select
            label="Estado"
            data={options(API_REQUEST_STATUS, 'Todos')}
            value={filters.status ?? ''}
            onChange={(v) => update({ status: (v || null) as ApiRequestStatus | null })}
            allowDeselect={false}
            w={200}
          />
          <Select
            label="Streaming"
            data={MODES}
            value={filters.stream ?? ''}
            onChange={(v) => update({ stream: v || null })}
            allowDeselect={false}
            w={160}
          />
          <Select
            label="Período"
            data={RANGES}
            value={filters.range}
            onChange={(v) => update({ range: v ?? '7' })}
            allowDeselect={false}
            w={170}
          />
          {filters.range === 'custom' && (
            <DatePickerInput
              type="range"
              label="Fechas"
              placeholder="Desde – hasta"
              value={[filters.from, filters.to]}
              onChange={([from, to]) => update({ from, to })}
              valueFormat="DD/MM/YYYY"
              maxDate={toIsoDate(new Date())}
              allowSingleDateInRange
              clearable
              w={240}
            />
          )}
        </Group>
      </Card>
      {requests.isError ? (
        <ErrorAlert error={requests.error} onRetry={() => void requests.refetch()} />
      ) : !requests.data ? (
        <Text size="sm" c="dimmed">
          Cargando…
        </Text>
      ) : (
        <>
          <Summary summary={requests.data.summary} />
          <RequestsTable
            page={requests.data}
            isAdmin={isAdmin}
            showClient={isAdmin && !filters.client}
            current={filters.page}
            onPage={(page) => update({ page })}
          />
        </>
      )}
    </Stack>
  );
}
