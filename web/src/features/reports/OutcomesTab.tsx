import { BarChart } from '@mantine/charts';
import { Badge, Group, Progress, Stack, Text } from '@mantine/core';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDayLabel, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { ReportCard, TableCard, type Column } from './parts';
import type { OutcomesReport, ReportQuery } from './types';

type Daily = OutcomesReport['conversion_daily'][number];
type Agent = OutcomesReport['by_agent'][number];
type Outcome = OutcomesReport['outcomes'][number];
type Field = OutcomesReport['fields'][number];
type Version = OutcomesReport['by_version'][number];

const share = (n: number, total: number) => (total ? (n / total) * 100 : null);

const DAILY_CSV: Column<Daily>[] = [
  { label: 'Fecha', value: 'date' },
  { label: 'Completas', value: 'complete' },
  { label: 'Parciales', value: 'partial' },
  { label: 'Sin datos', value: 'empty' },
];

const AGENT_COLS: Column<Agent>[] = [
  { label: 'Agente', value: 'agent_name' },
  { label: 'Consultas', value: 'total', num: true },
  { label: 'Completas', value: 'complete', num: true },
  { label: 'Parciales', value: 'partial', num: true },
  { label: 'Sin datos', value: 'empty', num: true },
  { label: 'Objetivo', value: 'goal', num: true },
  {
    label: '% completas',
    value: (r) => share(r.complete, r.total),
    num: true,
    render: (r) => pct(share(r.complete, r.total)),
  },
];

const OUTCOME_COLS: Column<Outcome>[] = [
  { label: 'Agente', value: 'agent_name' },
  {
    label: 'Resultado',
    value: 'label',
    render: (r) => (
      <Group gap={6} wrap="nowrap">
        {r.label}
        {r.goal && <Badge color="green">Objetivo</Badge>}
      </Group>
    ),
  },
  { label: 'Objetivo', value: (r) => (r.goal ? 'sí' : 'no'), render: (r) => (r.goal ? 'Sí' : 'No') },
  { label: 'Conversaciones', value: 'count', num: true },
];

const FIELD_COLS: Column<Field>[] = [
  { label: 'Agente', value: 'agent_name' },
  { label: 'Dato', value: 'label' },
  { label: 'Obtenido', value: 'captured', num: true },
  { label: 'De', value: 'total', num: true },
  {
    label: '% obtenido',
    value: 'pct',
    render: (r) => (
      <Group gap="xs" wrap="nowrap">
        <Progress value={r.pct ?? 0} w={80} color="blue" aria-hidden />
        <Text size="sm" className="mono">
          {pct(r.pct)}
        </Text>
      </Group>
    ),
  },
];

const VERSION_COLS: Column<Version>[] = [
  { label: 'Agente', value: 'agent_name' },
  { label: 'Versión', value: 'version', render: (r) => <span className="mono">v{r.version}</span> },
  { label: 'Consultas', value: 'total', num: true },
  { label: '% completas', value: 'conversion_pct', num: true, render: (r) => pct(r.conversion_pct) },
  { label: '% objetivo', value: 'goal_pct', num: true, render: (r) => pct(r.goal_pct) },
];

/** Embudo: atendidas -> con algun dato -> completas -> objetivo, como barras de % sobre el total. */
function Funnel({ funnel }: { funnel: OutcomesReport['funnel'] }) {
  const steps = [
    { label: 'Consultas', value: funnel.conversations },
    { label: 'Con algún dato', value: funnel.with_data },
    { label: 'Completas', value: funnel.complete },
    { label: 'Objetivo cumplido', value: funnel.goal },
  ];
  if (!funnel.conversations) return <EmptyState>Sin consultas en el período.</EmptyState>;
  return (
    <Stack gap="sm">
      {steps.map((s) => {
        const p = share(s.value, funnel.conversations) ?? 0;
        return (
          <Stack gap={4} key={s.label}>
            <Group justify="space-between">
              <Text size="sm" fw={600}>
                {s.label}
              </Text>
              <Text size="sm" className="mono">
                {formatNumber(s.value, 0)} · {formatNumber(p)}%
              </Text>
            </Group>
            <Progress value={p} color="blue" aria-label={`${s.label}: ${formatNumber(p)}%`} />
          </Stack>
        );
      })}
    </Stack>
  );
}

export function OutcomesTab({ query }: { query: ReportQuery }) {
  const report = useReport('outcomes', query);
  return (
    <QueryState query={report}>
      {(r) => {
        const any = r.conversion_daily.some((d) => d.complete || d.partial || d.empty);
        return (
          <Stack gap="md">
            <ReportCard
              title="Conversión por día"
              description="Completa: obtuvo todos los datos. Parcial: alguno. Sin datos: ninguno."
              csv={{ rows: r.conversion_daily, columns: DAILY_CSV }}
            >
              {any ? (
                <BarChart
                  h={240}
                  data={r.conversion_daily.map((d) => ({ ...d, day: formatDayLabel(d.date) }))}
                  dataKey="day"
                  type="stacked"
                  withLegend
                  legendProps={{ verticalAlign: 'bottom' }}
                  yAxisProps={{ allowDecimals: false }}
                  series={[
                    { name: 'complete', label: 'Completas', color: 'green.5' },
                    { name: 'partial', label: 'Parciales', color: 'yellow.5' },
                    { name: 'empty', label: 'Sin datos', color: 'gray.4' },
                  ]}
                />
              ) : (
                <EmptyState>Sin consultas en el período.</EmptyState>
              )}
            </ReportCard>
            <ReportCard
              title="Embudo"
              csv={{
                rows: [r.funnel],
                columns: [
                  { label: 'Consultas', value: 'conversations' },
                  { label: 'Con algún dato', value: 'with_data' },
                  { label: 'Completas', value: 'complete' },
                  { label: 'Objetivo cumplido', value: 'goal' },
                ],
              }}
            >
              <Funnel funnel={r.funnel} />
            </ReportCard>
            <TableCard title="Por agente" rows={r.by_agent} columns={AGENT_COLS} rowKey={(x) => x.agent_id} />
            <TableCard
              title="Resultados"
              description="Los resultados que definiste en cada agente; los de objetivo, marcados."
              rows={r.outcomes}
              columns={OUTCOME_COLS}
              rowKey={(x) => `${x.agent_id}-${x.outcome}`}
            />
            <TableCard
              title="Datos obtenidos"
              description="En qué porcentaje de las consultas se obtuvo cada dato requerido: muestra qué pregunta se pierde."
              rows={r.fields}
              columns={FIELD_COLS}
              rowKey={(x) => `${x.agent_id}-${x.field}`}
            />
            <TableCard
              title="Por versión del agente"
              description="Para comparar antes y después de un cambio en el agente."
              rows={r.by_version}
              columns={VERSION_COLS}
              rowKey={(x) => `${x.agent_id}-${x.version}`}
            />
          </Stack>
        );
      }}
    </QueryState>
  );
}
