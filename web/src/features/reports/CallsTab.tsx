import { BarChart } from '@mantine/charts';
import { SimpleGrid, Stack } from '@mantine/core';
import { HourHeatmap } from '@/components/HourHeatmap';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime, formatDayLabel, formatDuration, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { ENDED_REASON, label } from './labels';
import { KpiGrid, ReportCard, TableCard, type Column } from './parts';
import type { CallsReport, ReportQuery } from './types';

type Daily = CallsReport['daily'][number];
type Agent = CallsReport['by_agent'][number];
type Line = CallsReport['by_line'][number];
type Ended = CallsReport['ended'][number];
type Caller = CallsReport['callers']['top'][number];

const DAILY_CSV: Column<Daily>[] = [
  { label: 'Fecha', value: 'date' },
  { label: 'Entrantes', value: 'entrante' },
  { label: 'Salientes', value: 'saliente' },
  { label: 'Web', value: 'web' },
  { label: 'Prueba', value: 'prueba' },
];

const AGENT_COLS: Column<Agent>[] = [
  { label: 'Agente', value: 'agent_name' },
  { label: 'Llamadas', value: 'calls', num: true },
  { label: 'Minutos', value: 'minutes', num: true },
  {
    label: 'Duración media',
    value: 'avg_duration',
    num: true,
    render: (r) => formatDuration(r.avg_duration),
  },
  { label: '% completas', value: 'conversion_pct', num: true, render: (r) => pct(r.conversion_pct) },
  { label: '% objetivo', value: 'goal_pct', num: true, render: (r) => pct(r.goal_pct) },
];

const LINE_COLS: Column<Line>[] = [
  { label: 'Línea', value: 'number', render: (r) => <span className="mono">{r.number}</span> },
  { label: 'Llamadas', value: 'calls', num: true },
  { label: 'Minutos', value: 'minutes', num: true },
  { label: '% completas', value: 'conversion_pct', num: true, render: (r) => pct(r.conversion_pct) },
];

const ENDED_COLS: Column<Ended>[] = [
  { label: 'Cómo terminó', value: (r) => label(ENDED_REASON, r.reason) },
  { label: 'Llamadas', value: 'count', num: true },
];

const CALLER_COLS: Column<Caller>[] = [
  { label: 'Teléfono', value: 'phone', render: (r) => <span className="mono">{r.phone}</span> },
  { label: 'Consultas', value: 'count', num: true },
  { label: 'Última', value: 'last_at', render: (r) => formatDateTime(r.last_at) },
];

export function CallsTab({ query }: { query: ReportQuery }) {
  const report = useReport('calls', query);
  return (
    <QueryState query={report}>
      {(r) => {
        const total = r.durations.reduce((s, d) => s + d.count, 0);
        const withTests = r.daily.some((d) => d.prueba);
        return (
          <Stack gap="md">
            <KpiGrid
              kpis={[
                { label: 'Llamadas', value: formatNumber(total, 0) },
                {
                  label: 'Cortes tempranos',
                  value: formatNumber(r.early_hangups, 0),
                  sub: total
                    ? `${formatNumber((r.early_hangups / total) * 100)}% · menos de 15 s`
                    : undefined,
                },
                { label: 'Llamantes nuevos', value: formatNumber(r.callers.new, 0) },
                { label: 'Vuelven a llamar', value: formatNumber(r.callers.returning, 0) },
              ]}
            />
            <ReportCard title="Llamadas por día" csv={{ rows: r.daily, columns: DAILY_CSV }}>
              {total ? (
                <BarChart
                  h={240}
                  data={r.daily.map((d) => ({ ...d, day: formatDayLabel(d.date) }))}
                  dataKey="day"
                  type="stacked"
                  withLegend
                  legendProps={{ verticalAlign: 'bottom' }}
                  yAxisProps={{ allowDecimals: false }}
                  series={[
                    { name: 'entrante', label: 'Entrantes', color: 'var(--chart-1)' },
                    { name: 'saliente', label: 'Salientes', color: 'var(--chart-2)' },
                    { name: 'web', label: 'Web', color: 'var(--chart-3)' },
                    ...(withTests ? [{ name: 'prueba', label: 'Prueba', color: 'gray.5' }] : []),
                  ]}
                />
              ) : (
                <EmptyState>Sin llamadas en el período.</EmptyState>
              )}
            </ReportCard>
            <ReportCard
              title="Cuándo llaman"
              description="Llamadas por día de la semana y hora. Sirve para los horarios de derivación y de campañas."
              csv={{
                rows: r.heatmap,
                columns: [
                  { label: 'Día (0 = lunes)', value: 'weekday' },
                  { label: 'Hora', value: 'hour' },
                  { label: 'Llamadas', value: 'count' },
                ],
              }}
            >
              <HourHeatmap
                caption="Llamadas por día de la semana y hora"
                unit="llamadas"
                cells={r.heatmap.map((c) => ({ weekday: c.weekday, hour: c.hour, value: c.count }))}
              />
            </ReportCard>
            <TableCard title="Por agente" rows={r.by_agent} columns={AGENT_COLS} rowKey={(x) => x.agent_id} />
            <TableCard
              title="Por línea"
              rows={r.by_line}
              columns={LINE_COLS}
              empty="Sin llamadas a tus números en el período."
              rowKey={(x) => x.phone_number_id}
            />
            <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
              <ReportCard
                title="Duración"
                csv={{
                  rows: r.durations,
                  columns: [
                    { label: 'Duración', value: 'bucket' },
                    { label: 'Llamadas', value: 'count' },
                  ],
                }}
              >
                {total ? (
                  <BarChart
                    h={220}
                    data={r.durations}
                    dataKey="bucket"
                    yAxisProps={{ allowDecimals: false }}
                    series={[{ name: 'count', label: 'Llamadas', color: 'var(--chart-1)' }]}
                  />
                ) : (
                  <EmptyState>Sin llamadas en el período.</EmptyState>
                )}
              </ReportCard>
              <TableCard title="Cómo terminan" rows={r.ended} columns={ENDED_COLS} rowKey={(x) => x.reason} />
            </SimpleGrid>
            <TableCard
              title="Los que más vuelven"
              description="Muchas consultas del mismo número pueden indicar un problema sin resolver."
              rows={r.callers.top}
              columns={CALLER_COLS}
              empty="Nadie llamó más de una vez en el período."
              rowKey={(x) => x.phone}
            />
          </Stack>
        );
      }}
    </QueryState>
  );
}
