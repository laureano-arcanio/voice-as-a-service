import { CompositeChart } from '@mantine/charts';
import { Group, Progress, SimpleGrid, Stack, Text } from '@mantine/core';
import { EmptyState, QueryState } from '@/components/QueryState';
import {
  formatDate,
  formatDayLabel,
  formatDuration,
  formatLimit,
  formatNumber,
  formatPeriod,
  usageColor,
  usagePercent,
} from '@/lib/format';
import { useReport } from './api';
import { deltaPct, deltaPoints, pct, type Kpi } from './format';
import { KpiGrid, ReportCard } from './parts';
import type { ReportQuery, SummaryDay, SummaryPlan, SummaryReport } from './types';

const DAILY_CSV = [
  { label: 'Fecha', value: 'date' as const },
  { label: 'Teléfono', value: 'voice' as const },
  { label: 'WhatsApp', value: 'whatsapp' as const },
  { label: 'Web', value: 'web' as const },
  { label: 'Transferencias pedidas', value: 'transfers' as const },
  { label: 'Transferencias atendidas', value: 'transfers_answered' as const },
];

function summaryKpis(r: SummaryReport): Kpi[] {
  const k = r.kpis;
  const p = r.previous;
  const channels = [
    k.by_channel.voice && `${k.by_channel.voice} tel.`,
    k.by_channel.whatsapp && `${k.by_channel.whatsapp} WA`,
    k.by_channel.web && `${k.by_channel.web} web`,
  ].filter(Boolean);
  return [
    {
      label: 'Consultas',
      value: formatNumber(k.conversations, 0),
      sub: channels.length > 1 ? channels.join(' · ') : undefined,
      delta: deltaPct(k.conversations, p.conversations),
    },
    {
      label: 'Completas',
      value: pct(k.conversion_pct),
      sub: k.with_agent ? `${k.conversions} de ${k.with_agent}` : undefined,
      delta: deltaPoints(k.conversion_pct, p.conversion_pct),
    },
    {
      label: 'Objetivo cumplido',
      value: pct(k.goal_pct),
      sub: k.with_agent ? `${k.goals} de ${k.with_agent}` : undefined,
      delta: deltaPoints(k.goal_pct, p.goal_pct),
    },
    {
      label: 'Transferidas',
      value: formatNumber(k.transfers, 0),
      sub: k.transfers ? `${pct(k.transfer_pct)} · ${k.transfers_answered} atendidas` : undefined,
      delta: deltaPct(k.transfers, p.transfers),
    },
    {
      label: 'Minutos',
      value: formatNumber(k.minutes),
      sub:
        k.finished || k.failed
          ? `${k.finished} finalizadas${k.failed ? ` · ${k.failed} fallidas` : ''}`
          : undefined,
      delta: deltaPct(k.minutes, p.minutes),
    },
    {
      label: 'Duración media',
      value: formatDuration(k.avg_duration),
      delta: deltaPct(k.avg_duration, p.avg_duration),
    },
    {
      label: 'Mensajes de WhatsApp',
      value: formatNumber(k.wa_messages, 0),
      delta: deltaPct(k.wa_messages, p.wa_messages),
    },
    {
      label: 'Rechazadas por límite',
      value: formatNumber(k.rejected_by_limit, 0),
      tone: k.rejected_by_limit ? 'yellow' : undefined,
      delta: deltaPct(k.rejected_by_limit, p.rejected_by_limit),
    },
  ];
}

/** Consultas por dia por canal (barras apiladas) con las transferencias en el mismo grafico. */
export function ConsultasChart({ daily }: { daily: SummaryDay[] }) {
  const rows = daily.map((d) => ({ ...d, day: formatDayLabel(d.date) }));
  const empty = daily.every((d) => !d.voice && !d.whatsapp && !d.web);
  return (
    <ReportCard
      title="Consultas por día"
      description="Llamadas y conversaciones de WhatsApp por canal, y cuántas pidieron hablar con una persona."
      csv={{ rows: daily, columns: DAILY_CSV }}
    >
      {empty ? (
        <EmptyState>Sin consultas en el período.</EmptyState>
      ) : (
        <CompositeChart
          h={280}
          data={rows}
          dataKey="day"
          withLegend
          legendProps={{ verticalAlign: 'bottom' }}
          yAxisProps={{ allowDecimals: false }}
          maxBarWidth={28}
          barProps={{ stackId: 'consultas' }}
          curveType="linear"
          series={[
            { name: 'voice', label: 'Teléfono', color: 'var(--chart-1)', type: 'bar' },
            { name: 'whatsapp', label: 'WhatsApp', color: 'var(--chart-2)', type: 'bar' },
            { name: 'web', label: 'Web', color: 'var(--chart-3)', type: 'bar' },
            { name: 'transfers', label: 'Transferencias pedidas', color: 'gray.7', type: 'line' },
            { name: 'transfers_answered', label: 'Transferencias atendidas', color: 'green.6', type: 'line' },
          ]}
        />
      )}
    </ReportCard>
  );
}

function MinutesBar({ title, used, quota }: { title: string; used: number; quota: number | null }) {
  const p = usagePercent(used, quota);
  return (
    <Stack gap={4}>
      <Group justify="space-between" gap="xs">
        <Text size="sm" fw={600}>
          {title}
        </Text>
        <Text size="sm" className="mono">
          {formatNumber(used)} de {formatLimit(quota)}
          {quota != null ? ' min' : ''}
        </Text>
      </Group>
      {p != null && (
        <Progress
          value={Math.min(100, p)}
          color={usageColor(p)}
          aria-label={`${title}: ${formatNumber(p)}%`}
        />
      )}
    </Stack>
  );
}

/** Consumo del plan en el mes de facturacion, con la proyeccion al ritmo actual. */
export function PlanCard({ plan }: { plan: SummaryPlan }) {
  const projected = plan.projected_inbound_minutes;
  const over =
    projected != null && plan.inbound_minutes_quota != null && projected > plan.inbound_minutes_quota;
  return (
    <ReportCard
      title="Consumo del plan"
      description={`Mes en curso: ${formatPeriod(plan.period_start, plan.period_end)}`}
    >
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
        <MinutesBar
          title="Minutos entrantes"
          used={plan.inbound_minutes_used}
          quota={plan.inbound_minutes_quota}
        />
        <MinutesBar
          title="Minutos salientes"
          used={plan.outbound_minutes_used}
          quota={plan.outbound_minutes_quota}
        />
      </SimpleGrid>
      {projected != null && (
        <Text size="sm" mt="md" c={over ? 'yellow' : undefined}>
          Al ritmo actual, vas a usar unos {formatNumber(projected, 0)} minutos entrantes hasta el{' '}
          {formatDate(new Date(new Date(plan.period_end).getTime() - 1).toISOString())}
          {over ? ': más que los de tu plan.' : '.'}
        </Text>
      )}
    </ReportCard>
  );
}

export function SummaryTab({ query }: { query: ReportQuery }) {
  const report = useReport('summary', query);
  return (
    <QueryState query={report} loader={<KpiGrid kpis={null} />}>
      {(r) => (
        <Stack gap="md">
          <ConsultasChart daily={r.daily} />
          <KpiGrid kpis={summaryKpis(r)} />
          {r.plan && <PlanCard plan={r.plan} />}
        </Stack>
      )}
    </QueryState>
  );
}
