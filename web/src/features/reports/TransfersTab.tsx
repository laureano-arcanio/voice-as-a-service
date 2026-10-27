import { BarChart } from '@mantine/charts';
import { Stack } from '@mantine/core';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDayLabel, formatDuration, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { KpiGrid, ReportCard, TableCard, type Column } from './parts';
import type { ReportQuery, TransfersReport } from './types';

type Area = TransfersReport['by_area'][number];
type Member = TransfersReport['by_member'][number];

const AREA_COLS: Column<Area>[] = [
  { label: 'Área', value: 'name' },
  { label: 'Pedidas', value: 'requested', num: true },
  { label: 'Atendidas', value: 'answered', num: true },
  { label: 'No atendidas', value: 'not_answered', num: true },
  { label: 'Fuera de horario o sin personas', value: 'unavailable', num: true },
];

const MEMBER_COLS: Column<Member>[] = [
  { label: 'Persona', value: 'name' },
  { label: 'Intentos', value: 'attempts', num: true },
  { label: 'Atendidas', value: 'answered', num: true },
  { label: 'No atendidas', value: 'not_answered', num: true },
  {
    label: 'Tiempo hasta atender',
    value: 'avg_answer_seconds',
    num: true,
    render: (r) => formatDuration(r.avg_answer_seconds),
  },
  { label: 'Minutos', value: 'minutes', num: true },
];

export function TransfersTab({ query }: { query: ReportQuery }) {
  const report = useReport('transfers', query);
  return (
    <QueryState query={report}>
      {(r) => {
        const k = r.kpis;
        const wa = r.whatsapp;
        return (
          <Stack gap="md">
            <KpiGrid
              kpis={[
                { label: 'Pedidas', value: formatNumber(k.requested, 0) },
                {
                  label: 'Atendidas',
                  value: formatNumber(k.answered, 0),
                  sub: k.requested ? pct(k.answer_pct) : undefined,
                },
                {
                  label: 'Sin atender',
                  value: formatNumber(k.not_answered + k.unavailable, 0),
                  sub: k.unavailable ? `${k.unavailable} fuera de horario` : undefined,
                  tone: k.not_answered ? 'yellow' : undefined,
                },
                {
                  label: 'Tiempo hasta atender',
                  value: formatDuration(k.avg_answer_seconds),
                  sub: `${formatNumber(k.minutes)} min`,
                },
              ]}
            />
            <ReportCard
              title="Transferencias por día"
              csv={{
                rows: r.daily,
                columns: [
                  { label: 'Fecha', value: 'date' },
                  { label: 'Pedidas', value: 'requested' },
                  { label: 'Atendidas', value: 'answered' },
                ],
              }}
            >
              {k.requested ? (
                <BarChart
                  h={240}
                  data={r.daily.map((d) => ({ ...d, day: formatDayLabel(d.date) }))}
                  dataKey="day"
                  withLegend
                  legendProps={{ verticalAlign: 'bottom' }}
                  yAxisProps={{ allowDecimals: false }}
                  series={[
                    { name: 'requested', label: 'Pedidas', color: 'var(--chart-1)' },
                    { name: 'answered', label: 'Atendidas', color: 'green.5' },
                  ]}
                />
              ) : (
                <EmptyState>Nadie pidió hablar con una persona en el período.</EmptyState>
              )}
            </ReportCard>
            <TableCard
              title="Por área"
              rows={r.by_area}
              columns={AREA_COLS}
              rowKey={(x, i) => x.area_id ?? String(i)}
            />
            <TableCard
              title="Por persona del equipo"
              rows={r.by_member}
              columns={MEMBER_COLS}
              rowKey={(x) => x.team_member_id}
            />
            <ReportCard
              title="WhatsApp"
              description="Conversaciones derivadas a un vendedor por WhatsApp."
              csv={{
                rows: [wa],
                columns: [
                  { label: 'Asignadas', value: 'assigned' },
                  { label: 'Con respuesta', value: 'first_reply' },
                  { label: 'Primera respuesta (s)', value: 'avg_first_reply_seconds' },
                  { label: 'Reasignadas', value: 'reassigned' },
                ],
              }}
            >
              <KpiGrid
                kpis={[
                  { label: 'Asignadas', value: formatNumber(wa.assigned, 0) },
                  { label: 'Con respuesta', value: formatNumber(wa.first_reply, 0) },
                  { label: 'Primera respuesta', value: formatDuration(wa.avg_first_reply_seconds) },
                  { label: 'Reasignadas', value: formatNumber(wa.reassigned, 0) },
                ]}
              />
            </ReportCard>
          </Stack>
        );
      }}
    </QueryState>
  );
}
