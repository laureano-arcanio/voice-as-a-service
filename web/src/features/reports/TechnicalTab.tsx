import { BarChart, LineChart } from '@mantine/charts';
import { SimpleGrid, Stack, Text } from '@mantine/core';
import { EmptyState, QueryState } from '@/components/QueryState';
import { CLIENT_TOOL_TYPE } from '@/lib/labels';
import { formatDateTime, formatDayLabel, formatMs, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { KpiGrid, ReportCard, TableCard, type Column } from './parts';
import type { ReportQuery, TechnicalReport } from './types';

type Latency = TechnicalReport['latency_daily'][number];
type Provider = TechnicalReport['by_provider'][number];
type Tool = TechnicalReport['tools'][number];
type ErrorRow = TechnicalReport['errors'][number];

const ms = (v: number | null) => formatMs(v);

const LATENCY_COLS: Column<Latency>[] = [
  { label: 'Fecha', value: 'date' },
  { label: 'p50', value: 'p50', num: true, render: (r) => ms(r.p50) },
  { label: 'p95', value: 'p95', num: true, render: (r) => ms(r.p95) },
  { label: 'STT p50', value: 'stt_p50', num: true, render: (r) => ms(r.stt_p50) },
  { label: 'EOU p50', value: 'eou_p50', num: true, render: (r) => ms(r.eou_p50) },
  { label: 'LLM p50', value: 'llm_p50', num: true, render: (r) => ms(r.llm_p50) },
  { label: 'TTS p50', value: 'tts_p50', num: true, render: (r) => ms(r.tts_p50) },
];

const PROVIDER_COLS: Column<Provider>[] = [
  { label: 'Proveedor', value: 'provider' },
  { label: 'Modelo', value: 'model', render: (r) => <span className="mono">{r.model ?? '–'}</span> },
  { label: 'Turnos', value: 'turns', num: true },
  { label: 'Promedio', value: 'avg_ms', num: true, render: (r) => ms(r.avg_ms) },
  { label: 'Errores', value: 'errors', num: true },
];

const TOOL_COLS: Column<Tool>[] = [
  { label: 'Herramienta', value: 'slug', render: (r) => <span className="mono">{r.slug}</span> },
  { label: 'Tipo', value: (r) => CLIENT_TOOL_TYPE[r.type] ?? r.type },
  { label: 'Usos', value: 'runs', num: true },
  { label: 'Errores', value: 'errors', num: true },
  { label: '% error', value: 'error_pct', num: true, render: (r) => pct(r.error_pct) },
  { label: 'p50', value: 'p50_ms', num: true, render: (r) => ms(r.p50_ms) },
  { label: 'p95', value: 'p95_ms', num: true, render: (r) => ms(r.p95_ms) },
  {
    label: 'Último error',
    value: 'last_error',
    render: (r) =>
      r.last_error ? (
        <Text size="xs" className="mono" lineClamp={2} title={r.last_error}>
          {formatDateTime(r.last_error_at)} · {r.last_error}
        </Text>
      ) : (
        '–'
      ),
  },
];

const ERROR_COLS: Column<ErrorRow>[] = [
  { label: 'Motivo', value: 'reason', render: (r) => <span className="mono">{r.reason}</span> },
  { label: 'Llamadas', value: 'count', num: true },
];

/** Lo tecnico de un cliente (o de todos): solo el admin. */
export function TechnicalTab({ query }: { query: ReportQuery }) {
  const report = useReport('technical', query);
  return (
    <QueryState query={report}>
      {(r) => {
        const withLatency = r.latency_daily.some((d) => d.p50 != null);
        return (
          <Stack gap="md">
            <KpiGrid
              kpis={[
                { label: 'Turnos por conversación', value: formatNumber(r.turns_avg) },
                { label: 'Tokens de entrada', value: formatNumber(r.tokens.input, 0) },
                { label: 'Tokens de salida', value: formatNumber(r.tokens.output, 0) },
                {
                  label: 'Mails de resumen fallidos',
                  value: formatNumber(r.failed_summary_emails, 0),
                  tone: r.failed_summary_emails ? 'red' : undefined,
                },
              ]}
            />
            <ReportCard
              title="Latencia por turno"
              description="Tiempo total de respuesta por día (p50 y p95); el desglose por etapa, en el CSV y en la tabla."
              csv={{ rows: r.latency_daily, columns: LATENCY_COLS }}
            >
              {withLatency ? (
                <LineChart
                  h={240}
                  data={r.latency_daily.map((d) => ({ ...d, day: formatDayLabel(d.date) }))}
                  dataKey="day"
                  withLegend
                  legendProps={{ verticalAlign: 'bottom' }}
                  unit=" ms"
                  valueFormatter={(v) => formatNumber(v, 0)}
                  curveType="linear"
                  connectNulls
                  series={[
                    { name: 'p50', label: 'p50', color: 'var(--chart-1)' },
                    { name: 'p95', label: 'p95', color: 'var(--chart-2)' },
                  ]}
                />
              ) : (
                <EmptyState>Sin turnos medidos en el período.</EmptyState>
              )}
            </ReportCard>
            <TableCard
              title="Latencia por etapa"
              rows={r.latency_daily}
              columns={LATENCY_COLS}
              rowKey={(x) => x.date}
            />
            <TableCard
              title="LLM por proveedor"
              rows={r.by_provider}
              columns={PROVIDER_COLS}
              rowKey={(x) => `${x.provider}-${x.model}`}
            />
            <TableCard
              title="Herramientas"
              description="La API del cliente caída o lenta alarga la espera en la llamada."
              rows={r.tools}
              columns={TOOL_COLS}
              empty="Sin herramientas usadas en el período."
              sortable
              rowKey={(x) => x.tool_id ?? x.slug}
            />
            <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
              <TableCard
                title="Errores"
                rows={r.errors}
                columns={ERROR_COLS}
                empty="Sin llamadas con error en el período."
                rowKey={(x) => x.reason}
              />
              <ReportCard
                title="Tokens por día"
                csv={{
                  rows: r.tokens.by_day,
                  columns: [
                    { label: 'Fecha', value: 'date' },
                    { label: 'Entrada', value: 'input' },
                    { label: 'Salida', value: 'output' },
                  ],
                }}
              >
                {r.tokens.input + r.tokens.output ? (
                  <BarChart
                    h={220}
                    data={r.tokens.by_day.map((d) => ({ ...d, day: formatDayLabel(d.date) }))}
                    dataKey="day"
                    type="stacked"
                    withLegend
                    legendProps={{ verticalAlign: 'bottom' }}
                    series={[
                      { name: 'input', label: 'Entrada', color: 'var(--chart-1)' },
                      { name: 'output', label: 'Salida', color: 'var(--chart-2)' },
                    ]}
                  />
                ) : (
                  <EmptyState>Sin tokens registrados en el período.</EmptyState>
                )}
              </ReportCard>
            </SimpleGrid>
          </Stack>
        );
      }}
    </QueryState>
  );
}
