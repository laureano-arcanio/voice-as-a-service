import { Stack, Text } from '@mantine/core';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDuration, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { ENDED_REASON, label, SPLIT_ARM, SPLIT_REASON } from './labels';
import { KpiGrid, ReportCard, ReportTable, type Column } from './parts';
import type { ReportQuery, SplitGroup, SplitReport } from './types';

type Bucket = { experiment: string | null; percent: number | null; arms: SplitGroup[] };

/** Agrupa las filas del backend por experimento y porcentaje: cada uno es una comparación. */
function buckets(report: SplitReport): Bucket[] {
  const map = new Map<string, Bucket>();
  for (const g of report.groups) {
    const key = `${g.experiment ?? ''}|${g.percent ?? ''}`;
    const b = map.get(key) ?? { experiment: g.experiment, percent: g.percent, arms: [] };
    b.arms.push(g);
    map.set(key, b);
  }
  return [...map.values()];
}

const armOf = (arms: SplitGroup[], arm: SplitGroup['arm']) => arms.find((g) => g.arm === arm);
const show = (v: number | null | undefined, digits = 0) => (v == null ? '–' : formatNumber(v, digits));

type Row = { metric: string; agent: string; team: string };

function comparison(arms: SplitGroup[]): Row[] {
  const agent = armOf(arms, 'agent');
  const team = armOf(arms, 'team');
  const row = (metric: string, get: (g: SplitGroup) => string): Row => ({
    metric,
    agent: agent ? get(agent) : '–',
    team: team ? get(team) : '–',
  });
  return [
    row('Llamadas', (g) => formatNumber(g.calls, 0)),
    row('Llamantes distintos', (g) => formatNumber(g.callers, 0)),
    row('Pedidos de derivación', (g) => formatNumber(g.handoff_requested, 0)),
    row('Derivaciones atendidas', (g) => formatNumber(g.handoff_connected, 0)),
    row('Rellamadas dentro de 24 h', (g) => formatNumber(g.callbacks_24h, 0)),
    row('Cortes antes de 15 s', (g) => formatNumber(g.early_hangups, 0)),
    row('Duración P50', (g) => formatDuration(g.duration_p50)),
    row('Duración P90', (g) => formatDuration(g.duration_p90)),
    row('Llamadas con objetivo cumplido', (g) =>
      g.arm === 'agent' ? `${formatNumber(g.goals, 0)} de ${formatNumber(g.calls, 0)}` : '–',
    ),
  ];
}

const COMPARE_COLS: Column<Row>[] = [
  { label: 'Métrica', value: 'metric' },
  { label: 'Agente', value: 'agent', num: true },
  { label: 'Equipo', value: 'team', num: true },
];

type ReasonRow = { arm: string; reason: string; count: number };

const REASON_COLS: Column<ReasonRow>[] = [
  { label: 'Brazo', value: 'arm' },
  {
    label: 'Motivo',
    value: (r) => label(SPLIT_REASON, r.reason),
  },
  { label: 'Llamadas', value: 'count', num: true },
];

type EndedRow = { arm: string; reason: string; count: number };

const ENDED_COLS: Column<EndedRow>[] = [
  { label: 'Brazo', value: 'arm' },
  {
    label: 'Cómo terminó',
    value: (r) => label(ENDED_REASON, r.reason),
  },
  { label: 'Llamadas', value: 'count', num: true },
];

type OutcomeRow = { label: string; goal: boolean; count: number; pct: string };

const OUTCOME_COLS: Column<OutcomeRow>[] = [
  {
    label: 'Resultado',
    value: (r) => (r.goal ? `${r.label} (objetivo)` : r.label),
  },
  { label: 'Llamadas', value: 'count', num: true },
  { label: '% del brazo agente', value: 'pct', num: true },
];

export function SplitTab({ query }: { query: ReportQuery }) {
  const report = useReport('split', query);
  return (
    <QueryState query={report}>
      {(r) => {
        if (!r.has_data) {
          return (
            <EmptyState>
              Todavía no hay llamadas con reparto. Se activa por número, en Números, eligiendo
              &quot;Agente y equipo&quot;.
            </EmptyState>
          );
        }
        const bucketsWithData = buckets(r);
        if (!bucketsWithData.length) {
          return <EmptyState>Sin llamadas con reparto en el período.</EmptyState>;
        }
        const calls = r.groups.reduce((n, g) => n + g.calls, 0);
        const answered = r.groups.reduce((n, g) => n + g.handoff_connected, 0);
        const callbacks = r.groups.reduce((n, g) => n + g.callbacks_24h, 0);
        return (
          <Stack gap="md">
            <KpiGrid
              kpis={[
                { label: 'Llamadas con reparto', value: formatNumber(calls, 0) },
                { label: 'Comparaciones', value: formatNumber(bucketsWithData.length, 0) },
                { label: 'Derivaciones atendidas', value: formatNumber(answered, 0) },
                { label: 'Rellamadas en 24 h', value: formatNumber(callbacks, 0) },
              ]}
            />
            {bucketsWithData.map((b) => {
              const title = `Reparto${b.percent != null ? ` ${b.percent} % al agente` : ''}${
                b.experiment ? ` · experimento ${b.experiment}` : ''
              }`;
              const agent = armOf(b.arms, 'agent');
              const reasons: ReasonRow[] = b.arms.flatMap((g) =>
                g.reasons.map((x) => ({ arm: label(SPLIT_ARM, g.arm), reason: x.reason, count: x.count })),
              );
              const ended: EndedRow[] = b.arms.flatMap((g) =>
                g.ended.map((x) => ({ arm: label(SPLIT_ARM, g.arm), reason: x.reason, count: x.count })),
              );
              const outcomes: OutcomeRow[] = (agent?.outcomes ?? []).map((o) => ({
                label: o.label,
                goal: o.goal,
                count: o.count,
                pct: pct(agent?.calls ? (o.count / agent.calls) * 100 : null),
              }));
              return (
                <Stack key={`${b.experiment ?? ''}-${b.percent ?? ''}`} gap="md">
                  <ReportCard
                    title={title}
                    description="Las mismas condiciones para los dos brazos: por sorteo, por tope o por disponibilidad."
                    csv={{
                      rows: comparison(b.arms),
                      columns: [
                        { label: 'Métrica', value: 'metric' },
                        { label: 'Agente', value: 'agent' },
                        { label: 'Equipo', value: 'team' },
                      ],
                    }}
                  >
                    <Text fw={600} mb="xs">
                      Por brazo
                    </Text>
                    <ReportTable rows={comparison(b.arms)} columns={COMPARE_COLS} rowKey={(x) => x.metric} />
                  </ReportCard>
                  {reasons.length > 0 && (
                    <ReportCard
                      title="Cómo se repartió"
                      csv={{
                        rows: reasons,
                        columns: [
                          { label: 'Brazo', value: 'arm' },
                          { label: 'Motivo', value: 'reason' },
                          { label: 'Llamadas', value: 'count' },
                        ],
                      }}
                    >
                      <ReportTable rows={reasons} columns={REASON_COLS} rowKey={(x, i) => `${x.arm}-${i}`} />
                    </ReportCard>
                  )}
                  {ended.length > 0 && (
                    <ReportCard
                      title="Cómo terminan"
                      csv={{
                        rows: ended,
                        columns: [
                          { label: 'Brazo', value: 'arm' },
                          { label: 'Cómo terminó', value: 'reason' },
                          { label: 'Llamadas', value: 'count' },
                        ],
                      }}
                    >
                      <ReportTable rows={ended} columns={ENDED_COLS} rowKey={(x, i) => `${x.arm}-${i}`} />
                    </ReportCard>
                  )}
                  {outcomes.length > 0 && (
                    <ReportCard
                      title="Resultados del brazo agente"
                      csv={{
                        rows: outcomes,
                        columns: [
                          { label: 'Resultado', value: 'label' },
                          { label: 'Objetivo', value: (x) => (x.goal ? 'Sí' : 'No') },
                          { label: 'Llamadas', value: 'count' },
                          { label: '% del brazo agente', value: 'pct' },
                        ],
                      }}
                    >
                      <ReportTable rows={outcomes} columns={OUTCOME_COLS} rowKey={(x) => x.label} />
                    </ReportCard>
                  )}
                </Stack>
              );
            })}
            {r.both_arms.length > 0 && (
              <ReportCard
                title="Llamantes que pasaron por los dos brazos"
                description="Los mismos números entraron al agente y al equipo en el mismo experimento y porcentaje."
              >
                <ReportTable
                  rows={r.both_arms}
                  columns={[
                    { label: 'Experimento', value: (x) => x.experiment ?? '–' },
                    { label: '% al agente', value: (x) => (x.percent == null ? '–' : `${x.percent} %`) },
                    { label: 'Llamantes', value: 'callers', num: true },
                    { label: 'Llamadas', value: 'calls', num: true },
                    {
                      label: 'Llamadas al agente',
                      value: (x) => show(armOf(x.arms, 'agent')?.calls),
                      num: true,
                    },
                    {
                      label: 'Llamadas al equipo',
                      value: (x) => show(armOf(x.arms, 'team')?.calls),
                      num: true,
                    },
                  ]}
                  rowKey={(x, i) => `${x.experiment ?? ''}-${x.percent ?? ''}-${i}`}
                />
              </ReportCard>
            )}
          </Stack>
        );
      }}
    </QueryState>
  );
}
