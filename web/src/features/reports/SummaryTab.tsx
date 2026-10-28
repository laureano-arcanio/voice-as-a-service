import { CompositeChart } from '@mantine/charts';
import { Stack } from '@mantine/core';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDayLabel, formatDuration, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { deltaPct, deltaPoints, pct, type Kpi } from './format';
import { KpiGrid, ReportCard } from './parts';
import type { ReportQuery, SummaryDay, SummaryReport } from './types';

const DAILY_CSV = [
  { label: 'Fecha', value: 'date' as const },
  { label: 'Teléfono entrante', value: 'voice_in' as const },
  { label: 'Teléfono saliente', value: 'voice_out' as const },
  { label: 'WhatsApp', value: 'whatsapp' as const },
  { label: 'Web', value: 'web' as const },
  { label: 'Transferencias pedidas', value: 'transfers' as const },
  { label: 'Transferencias atendidas', value: 'transfers_answered' as const },
];

function summaryKpis(r: SummaryReport): Kpi[] {
  const k = r.kpis;
  const p = r.previous;
  const channels = [
    k.by_channel.voice_in && `${k.by_channel.voice_in} ent.`,
    k.by_channel.voice_out && `${k.by_channel.voice_out} sal.`,
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
  const empty = daily.every((d) => !d.voice_in && !d.voice_out && !d.whatsapp && !d.web);
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
            { name: 'voice_in', label: 'Teléfono entrante', color: 'var(--chart-1)', type: 'bar' },
            { name: 'voice_out', label: 'Teléfono saliente', color: 'var(--chart-2)', type: 'bar' },
            { name: 'whatsapp', label: 'WhatsApp', color: 'var(--chart-3)', type: 'bar' },
            { name: 'web', label: 'Web', color: 'gray.5', type: 'bar' },
            { name: 'transfers', label: 'Transferencias pedidas', color: 'gray.7', type: 'line' },
            { name: 'transfers_answered', label: 'Transferencias atendidas', color: 'green.6', type: 'line' },
          ]}
        />
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
        </Stack>
      )}
    </QueryState>
  );
}
