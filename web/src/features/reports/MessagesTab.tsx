import { BarChart } from '@mantine/charts';
import { Badge, Group, Stack, Text } from '@mantine/core';
import { Dash } from '@/components/Badges';
import { HourHeatmap } from '@/components/HourHeatmap';
import { EmptyState, QueryState } from '@/components/QueryState';
import { WA_QUALITY } from '@/features/whatsapp/labels';
import { formatDateTime, formatDayLabel, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { KpiGrid, ReportCard, TableCard, type Column } from './parts';
import type { MessagesReport, ReportQuery } from './types';

type Daily = MessagesReport['daily'][number];
type Failure = MessagesReport['failures'][number];
type Account = MessagesReport['accounts'][number];

const DAILY_CSV: Column<Daily>[] = [
  { label: 'Fecha', value: 'date' },
  { label: 'Entrantes', value: 'inbound' },
  { label: 'Salientes', value: 'outbound' },
  { label: 'Notas de voz entrantes', value: 'inbound_audio' },
  { label: 'Notas de voz salientes', value: 'outbound_audio' },
  { label: 'Conversaciones', value: 'conversations' },
];

const FAILURE_COLS: Column<Failure>[] = [
  {
    label: 'Código',
    value: 'code',
    render: (r) => (r.code == null ? <Dash /> : <span className="mono">{r.code}</span>),
  },
  { label: 'Error de Meta', value: 'message' },
  { label: 'Mensajes', value: 'count', num: true },
];

function Quality({ value }: { value: string | null }) {
  if (!value) return <Dash />;
  const q = WA_QUALITY[value] ?? { label: value, color: 'gray' };
  return <Badge color={q.color}>{q.label}</Badge>;
}

const ACCOUNT_COLS: Column<Account>[] = [
  {
    label: 'Número',
    value: 'display_phone_number',
    render: (r) => <span className="mono">{r.display_phone_number ?? '–'}</span>,
  },
  { label: 'Calidad', value: 'quality_rating', render: (r) => <Quality value={r.quality_rating} /> },
  { label: 'Límite de mensajería', value: 'messaging_limit' },
  {
    label: 'Cambios',
    value: (r) => r.history.length,
    render: (r) =>
      r.history.length ? (
        <Stack gap={2}>
          {r.history.slice(-3).map((h) => (
            <Group key={h.at} gap={6} wrap="nowrap">
              <Text size="xs" c="dimmed">
                {formatDateTime(h.at)}
              </Text>
              <Quality value={h.quality_rating} />
              {h.messaging_limit && (
                <Text size="xs" className="mono">
                  {h.messaging_limit}
                </Text>
              )}
            </Group>
          ))}
        </Stack>
      ) : (
        <Dash />
      ),
  },
];

export function MessagesTab({ query }: { query: ReportQuery }) {
  const report = useReport('messages', query);
  return (
    <QueryState query={report}>
      {(r) => {
        const inbound = r.daily.reduce((s, d) => s + d.inbound, 0);
        const outbound = r.daily.reduce((s, d) => s + d.outbound, 0);
        const audio = r.daily.reduce((s, d) => s + d.inbound_audio + d.outbound_audio, 0);
        const convs = r.conversion.complete + r.conversion.partial + r.conversion.empty;
        const d = r.delivery;
        return (
          <Stack gap="md">
            <KpiGrid
              kpis={[
                { label: 'Entrantes', value: formatNumber(inbound, 0) },
                { label: 'Salientes', value: formatNumber(outbound, 0) },
                {
                  label: 'Notas de voz',
                  value: formatNumber(audio, 0),
                  sub: inbound + outbound ? pct((audio / (inbound + outbound)) * 100) : undefined,
                },
                { label: 'Mensajes por conversación', value: formatNumber(r.per_conversation_avg) },
              ]}
            />
            <ReportCard title="Mensajes por día" csv={{ rows: r.daily, columns: DAILY_CSV }}>
              {inbound + outbound ? (
                <BarChart
                  h={240}
                  data={r.daily.map((x) => ({ ...x, day: formatDayLabel(x.date) }))}
                  dataKey="day"
                  withLegend
                  legendProps={{ verticalAlign: 'bottom' }}
                  yAxisProps={{ allowDecimals: false }}
                  series={[
                    { name: 'inbound', label: 'Entrantes', color: 'var(--chart-1)' },
                    { name: 'outbound', label: 'Salientes', color: 'var(--chart-2)' },
                  ]}
                />
              ) : (
                <EmptyState>Sin mensajes de WhatsApp en el período.</EmptyState>
              )}
            </ReportCard>
            <ReportCard
              title="Cuándo escriben"
              description="Mensajes entrantes por día de la semana y hora."
              csv={{
                rows: r.heatmap,
                columns: [
                  { label: 'Día (0 = lunes)', value: 'weekday' },
                  { label: 'Hora', value: 'hour' },
                  { label: 'Mensajes', value: 'count' },
                ],
              }}
            >
              <HourHeatmap
                caption="Mensajes entrantes por día de la semana y hora"
                unit="mensajes"
                cells={r.heatmap.map((c) => ({ weekday: c.weekday, hour: c.hour, value: c.count }))}
              />
            </ReportCard>
            <ReportCard
              title="Entrega"
              description="Mensajes que mandó el agente y hasta dónde llegaron."
              csv={{
                rows: [d],
                columns: [
                  { label: 'Enviados', value: 'sent' },
                  { label: 'Entregados', value: 'delivered' },
                  { label: 'Leídos', value: 'read' },
                  { label: 'Fallidos', value: 'failed' },
                ],
              }}
            >
              <KpiGrid
                kpis={[
                  { label: 'Enviados', value: formatNumber(d.sent, 0) },
                  {
                    label: 'Entregados',
                    value: formatNumber(d.delivered, 0),
                    sub: d.sent ? pct((d.delivered / d.sent) * 100) : undefined,
                  },
                  {
                    label: 'Leídos',
                    value: formatNumber(d.read, 0),
                    sub: d.sent ? pct((d.read / d.sent) * 100) : undefined,
                  },
                  { label: 'Fallidos', value: formatNumber(d.failed, 0), tone: d.failed ? 'red' : undefined },
                ]}
              />
            </ReportCard>
            <ReportCard
              title="Conversión"
              csv={{
                rows: [r.conversion],
                columns: [
                  { label: 'Completas', value: 'complete' },
                  { label: 'Parciales', value: 'partial' },
                  { label: 'Sin datos', value: 'empty' },
                ],
              }}
            >
              <KpiGrid
                cols={3}
                kpis={[
                  {
                    label: 'Completas',
                    value: formatNumber(r.conversion.complete, 0),
                    sub: convs ? pct((r.conversion.complete / convs) * 100) : undefined,
                  },
                  {
                    label: 'Parciales',
                    value: formatNumber(r.conversion.partial, 0),
                    sub: convs ? pct((r.conversion.partial / convs) * 100) : undefined,
                  },
                  {
                    label: 'Sin datos',
                    value: formatNumber(r.conversion.empty, 0),
                    sub: convs ? pct((r.conversion.empty / convs) * 100) : undefined,
                  },
                ]}
              />
            </ReportCard>
            <TableCard
              title="Mensajes que fallaron"
              rows={r.failures}
              columns={FAILURE_COLS}
              empty="Ningún mensaje falló en el período."
              rowKey={(x, i) => `${x.code}-${i}`}
            />
            <TableCard
              title="Cuentas de WhatsApp"
              description="Calidad y límite de mensajería que informa Meta, con los últimos cambios."
              rows={r.accounts}
              columns={ACCOUNT_COLS}
              empty="No hay cuentas de WhatsApp conectadas."
              rowKey={(x) => x.account_id}
            />
          </Stack>
        );
      }}
    </QueryState>
  );
}
