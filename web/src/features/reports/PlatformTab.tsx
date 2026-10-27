import { BarChart, LineChart } from '@mantine/charts';
import { Anchor, Badge, Group, SimpleGrid, Stack, Text } from '@mantine/core';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatArs, formatDateTime, formatDayLabel, formatNumber } from '@/lib/format';
import { useReport } from './api';
import { pct } from './format';
import { ALERT_KIND, REJECT_REASON, label } from './labels';
import { KpiGrid, ReportCard, TableCard, type Column } from './parts';
import type { PlatformClientRow, PlatformReport, ReportQuery } from './types';

type Alert = PlatformReport['alerts'][number];

const signed = (v: number | null) => (v == null ? '–' : `${v >= 0 ? '+' : ''}${formatNumber(v, 0)} %`);

/** Toda la plataforma (admin, cliente "Todos"). `onClient` filtra la pantalla por ese cliente. */
export function PlatformTab({ query, onClient }: { query: ReportQuery; onClient: (id: string) => void }) {
  const report = useReport('platform', query);

  const clientCols: Column<PlatformClientRow>[] = [
    {
      label: 'Cliente',
      value: 'name',
      render: (r) => (
        <Anchor component="button" type="button" size="sm" onClick={() => onClient(r.client_id)}>
          {r.name}
        </Anchor>
      ),
    },
    { label: 'Tier', value: 'tier' },
    { label: 'Conversaciones', value: 'conversations', num: true },
    { label: 'Minutos', value: 'minutes', num: true },
    {
      label: '% del cupo',
      value: 'quota_pct',
      num: true,
      render: (r) => (
        <Text span inherit c={r.quota_pct != null && r.quota_pct >= 80 ? 'yellow' : undefined}>
          {pct(r.quota_pct)}
        </Text>
      ),
    },
    { label: '% completas', value: 'conversion_pct', num: true, render: (r) => pct(r.conversion_pct) },
    { label: 'Errores', value: 'errors', num: true },
    { label: 'Último uso', value: 'last_activity_at', render: (r) => formatDateTime(r.last_activity_at) },
    { label: 'Variación', value: 'delta_pct', num: true, render: (r) => signed(r.delta_pct) },
  ];

  const alertCols: Column<Alert>[] = [
    {
      label: 'Alerta',
      value: (r) => ALERT_KIND[r.kind]?.label ?? r.kind,
      render: (r) => {
        const k = ALERT_KIND[r.kind] ?? { label: r.kind, color: 'gray' };
        return <Badge color={k.color}>{k.label}</Badge>;
      },
    },
    {
      label: 'Cliente',
      value: 'name',
      render: (r) => (
        <Anchor component="button" type="button" size="sm" onClick={() => onClient(r.client_id)}>
          {r.name}
        </Anchor>
      ),
    },
    { label: 'Detalle', value: 'detail' },
  ];

  return (
    <QueryState query={report}>
      {(r) => {
        const b = r.business;
        const op = r.operation;
        // Pico de llamadas simultaneas por dia (el maximo de sus horas), para el grafico.
        const peakByDay = [...new Set(op.peak_concurrency.map((p) => p.date))].sort().map((date) => ({
          date,
          day: formatDayLabel(date),
          peak: Math.max(...op.peak_concurrency.filter((p) => p.date === date).map((p) => p.peak)),
        }));
        const failuresByReason = Object.entries(
          op.failures.reduce<Record<string, number>>((acc, f) => {
            acc[f.reason] = (acc[f.reason] ?? 0) + f.count;
            return acc;
          }, {}),
        )
          .map(([reason, count]) => ({ reason, count }))
          .sort((x, y) => y.count - x.count);
        return (
          <Stack gap="md">
            <TableCard
              title="Alertas"
              description="Cerca del cupo: 80 % o más de los minutos entrantes del mes. Inactivo: 14 días sin conversaciones."
              rows={r.alerts}
              columns={alertCols}
              empty="Sin alertas."
              rowKey={(x) => `${x.kind}-${x.client_id}`}
            />
            <TableCard
              title="Clientes"
              description="Click en un encabezado para ordenar; en un cliente, para ver sus reportes."
              rows={r.clients}
              columns={clientCols}
              sortable
              rowKey={(x) => x.client_id}
            />
            <KpiGrid
              kpis={[
                { label: 'Ingreso mensual recurrente', value: formatArs(b.mrr_ars) },
                { label: 'Pagos del mes', value: formatArs(b.payments_month_ars) },
                {
                  label: 'Vencidos',
                  value: formatNumber(b.past_due, 0),
                  tone: b.past_due ? 'red' : undefined,
                },
                { label: 'Free a pago', value: formatNumber(b.free_to_paid, 0) },
              ]}
            />
            <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
              <TableCard
                title="Clientes por tier"
                rows={b.clients_by_tier}
                columns={[
                  { label: 'Tier', value: 'tier' },
                  { label: 'Clientes', value: 'count', num: true },
                ]}
                rowKey={(x) => x.tier}
              />
              <ReportCard
                title="Altas por día"
                csv={{
                  rows: b.signups,
                  columns: [
                    { label: 'Fecha', value: 'date' },
                    { label: 'Altas', value: 'count' },
                  ],
                }}
              >
                {b.signups.some((s) => s.count) ? (
                  <BarChart
                    h={200}
                    data={b.signups.map((s) => ({ ...s, day: formatDayLabel(s.date) }))}
                    dataKey="day"
                    yAxisProps={{ allowDecimals: false }}
                    series={[{ name: 'count', label: 'Altas', color: 'var(--chart-1)' }]}
                  />
                ) : (
                  <EmptyState>Sin altas en el período.</EmptyState>
                )}
              </ReportCard>
            </SimpleGrid>
            <ReportCard
              title="Pico de llamadas simultáneas"
              description="El máximo de cada día; por hora, en el CSV."
              csv={{
                rows: op.peak_concurrency,
                columns: [
                  { label: 'Fecha', value: 'date' },
                  { label: 'Hora', value: 'hour' },
                  { label: 'Pico', value: 'peak' },
                ],
              }}
            >
              {peakByDay.length ? (
                <LineChart
                  h={220}
                  data={peakByDay}
                  dataKey="day"
                  curveType="linear"
                  yAxisProps={{ allowDecimals: false }}
                  series={[{ name: 'peak', label: 'Pico', color: 'var(--chart-1)' }]}
                />
              ) : (
                <EmptyState>Sin llamadas en el período.</EmptyState>
              )}
            </ReportCard>
            <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
              <ReportCard
                title="Fallas por motivo"
                csv={{
                  rows: op.failures,
                  columns: [
                    { label: 'Fecha', value: 'date' },
                    { label: 'Motivo', value: 'reason' },
                    { label: 'Llamadas', value: 'count' },
                  ],
                }}
              >
                {failuresByReason.length ? (
                  <Stack gap={4}>
                    {failuresByReason.map((f) => (
                      <Group key={f.reason} justify="space-between" wrap="nowrap">
                        <Text size="sm" className="mono" lineClamp={1}>
                          {f.reason}
                        </Text>
                        <Text size="sm" className="mono">
                          {f.count}
                        </Text>
                      </Group>
                    ))}
                  </Stack>
                ) : (
                  <EmptyState>Sin fallas en el período.</EmptyState>
                )}
              </ReportCard>
              <TableCard
                title="Rechazadas por motivo"
                rows={op.rejected}
                columns={[
                  { label: 'Motivo', value: (x) => label(REJECT_REASON, x.reason) },
                  { label: 'Llamadas', value: 'count', num: true },
                ]}
                empty="Sin rechazos en el período."
                rowKey={(x) => x.reason}
              />
            </SimpleGrid>
          </Stack>
        );
      }}
    </QueryState>
  );
}
