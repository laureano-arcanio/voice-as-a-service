import { BarChart, LineChart } from '@mantine/charts';
import { Card, SimpleGrid, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import type { Daily } from '@/api/types';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { formatNumber } from '@/lib/format';
import { dailyRows } from './stats';

/** Cantidad y porcentaje van en dos graficos: un solo eje Y por grafico. */
export function DailyChart({ data, error }: { data: Daily | undefined; error: unknown }) {
  const isAdmin = useIsAdmin();
  const rows = data ? dailyRows(data) : [];
  const empty = data && data.totals.every((t) => !t);
  const body = (chart: ReactNode) =>
    error ? (
      <ErrorAlert error={error} />
    ) : empty ? (
      <EmptyState>Sin conversaciones en el período.</EmptyState>
    ) : (
      chart
    );
  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
      <Card>
        <Title order={4} mb="md">
          Conversaciones por día
        </Title>
        {body(
          <BarChart
            h={240}
            data={rows}
            dataKey="day"
            yAxisProps={{ allowDecimals: false }}
            series={[{ name: 'total', label: 'Conversaciones', color: 'var(--chart-1)' }]}
          />,
        )}
      </Card>
      <Card>
        <Title order={4} mb="md">
          Resultado por día
        </Title>
        {body(
          <LineChart
            h={240}
            data={rows}
            dataKey="day"
            withLegend
            legendProps={{ verticalAlign: 'bottom' }}
            yAxisProps={{ domain: [0, 100] }}
            unit="%"
            valueFormatter={(v) => formatNumber(v)}
            curveType="linear"
            connectNulls
            series={[
              {
                name: 'completed',
                label: isAdmin ? '% workflow completo' : '% completas',
                color: 'var(--chart-1)',
              },
              { name: 'goal', label: '% objetivo cumplido', color: 'var(--chart-2)' },
            ]}
          />,
        )}
      </Card>
    </SimpleGrid>
  );
}
