import { BarChart } from '@mantine/charts';
import { SimpleGrid, Stack } from '@mantine/core';
import { HourHeatmap } from '@/components/HourHeatmap';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime, formatDayLabel, formatDuration, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { CALL_TYPE, ENDED_REASON, label } from './labels';
import { KpiGrid, ReportCard, TableCard, type Column } from './parts';
import type { CallsReport, ReportQuery } from './types';

type Daily = CallsReport['daily'][number];
type Agent = CallsReport['by_agent'][number];
type Line = CallsReport['by_line'][number];
type Ended = CallsReport['ended'][number];
type CallType = CallsReport['by_type'][number];
type CallUser = CallsReport['by_user'][number];
type Caller = CallsReport['callers']['top'][number];

const DAILY_CSV: Column<Daily>[] = [
  { label: 'Fecha', value: 'date' },
  { label: 'Entrantes', value: 'entrante' },
  { label: 'Salientes', value: 'saliente' },
  { label: 'Directas', value: 'directa' },
  { label: 'Web', value: 'web' },
  { label: 'Prueba', value: 'prueba' },
];

const duration = (r: { avg_duration: number | null }) => formatDuration(r.avg_duration);

const TYPE_COLS: Column<CallType>[] = [
  { label: 'Tipo', value: (r) => label(CALL_TYPE, r.type) },
  { label: 'Llamadas', value: 'calls', num: true },
  { label: 'Minutos', value: 'minutes', num: true },
  { label: 'Duración media', value: 'avg_duration', num: true, render: duration },
];

const USER_COLS: Column<CallUser>[] = [
  { label: 'Usuario', value: 'user_name' },
  { label: 'Directas', value: 'direct', num: true },
  { label: 'Entrantes atendidas', value: 'team', num: true },
  { label: 'Llamadas', value: 'calls', num: true },
  { label: 'Minutos', value: 'minutes', num: true },
  { label: 'Duración media', value: 'avg_duration', num: true, render: duration },
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
        // Llamadas: todas las del período, como suman "Por tipo" y "Cómo terminan"; la duración y los cortes
        // tempranos son de las finalizadas.
        const total = r.total;
        const finished = r.durations.reduce((s, d) => s + d.count, 0);
        const ended = r.ended.filter((e) => e.count > 0);
        const withTests = r.daily.some((d) => d.prueba);
        const withDirect = r.daily.some((d) => d.directa);
        // Tres series de color (guía de la app): con directas, la web se junta con la prueba en gris.
        const other = (d: Daily) => (withDirect ? d.web : 0) + d.prueba;
        const withOther = r.daily.some((d) => other(d) > 0);
        // Las directas y las del equipo no se muestran a quien nunca las usó.
        const withPeople = r.by_type.some((t) => t.type !== 'agent' && t.calls > 0) || r.by_user.length > 0;
        return (
          <Stack gap="md">
            <KpiGrid
              kpis={[
                { label: 'Llamadas', value: formatNumber(total, 0) },
                {
                  label: 'Cortes tempranos',
                  value: formatNumber(r.early_hangups, 0),
                  sub: finished
                    ? `${formatNumber((r.early_hangups / finished) * 100)}% de las finalizadas · menos de 15 s`
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
                  data={r.daily.map((d) => ({ ...d, other: other(d), day: formatDayLabel(d.date) }))}
                  dataKey="day"
                  type="stacked"
                  withLegend
                  legendProps={{ verticalAlign: 'bottom' }}
                  yAxisProps={{ allowDecimals: false }}
                  series={[
                    { name: 'entrante', label: 'Entrantes', color: 'var(--chart-1)' },
                    { name: 'saliente', label: 'Salientes', color: 'var(--chart-2)' },
                    withDirect
                      ? { name: 'directa', label: 'Directas', color: 'var(--chart-3)' }
                      : { name: 'web', label: 'Web', color: 'var(--chart-3)' },
                    ...(withOther
                      ? [
                          {
                            name: withDirect ? 'other' : 'prueba',
                            label: withDirect ? (withTests ? 'Web y prueba' : 'Web') : 'Prueba',
                            color: 'gray.5',
                          },
                        ]
                      : []),
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
            {withPeople && (
              <>
                <TableCard
                  title="Por tipo"
                  description="Con el agente, directas que hace el equipo y entrantes que atiende el equipo. Las dos últimas no tienen conversión ni resultados."
                  rows={r.by_type}
                  columns={TYPE_COLS}
                  rowKey={(x) => x.type}
                />
                <TableCard
                  title="Por usuario"
                  description="Las directas que hizo cada persona y las entrantes del equipo que atendió."
                  rows={r.by_user}
                  columns={USER_COLS}
                  empty="Nadie del equipo llamó ni atendió en el período."
                  rowKey={(x) => x.user_id}
                />
              </>
            )}
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
                description="Las llamadas finalizadas."
                csv={{
                  rows: r.durations,
                  columns: [
                    { label: 'Duración', value: 'bucket' },
                    { label: 'Llamadas', value: 'count' },
                  ],
                }}
              >
                {finished ? (
                  <BarChart
                    h={220}
                    data={r.durations}
                    dataKey="bucket"
                    yAxisProps={{ allowDecimals: false }}
                    series={[{ name: 'count', label: 'Llamadas', color: 'var(--chart-1)' }]}
                  />
                ) : (
                  <EmptyState>Sin llamadas finalizadas en el período.</EmptyState>
                )}
              </ReportCard>
              <TableCard
                title="Cómo terminan"
                rows={ended}
                columns={ENDED_COLS}
                empty="Sin llamadas en el período."
                rowKey={(x) => x.reason}
              />
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
