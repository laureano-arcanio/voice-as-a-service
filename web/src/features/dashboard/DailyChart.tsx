import { CompositeChart } from '@mantine/charts';
import { Card, Group, Text, Title } from '@mantine/core';
import type { Daily } from '@/api/types';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { dailyRows } from './stats';

export function DailyChart({ data, error }: { data: Daily | undefined; error: unknown }) {
  const rows = data ? dailyRows(data) : [];
  const empty = data && data.totals.every((t) => !t);
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Evolución de conversaciones</Title>
        <Text size="xs" c="dimmed">
          Barras: conversaciones por día · líneas: % (eje derecho)
        </Text>
      </Group>
      {error ? (
        <ErrorAlert error={error} />
      ) : empty ? (
        <EmptyState>Sin conversaciones en el período.</EmptyState>
      ) : (
        <CompositeChart
          h={260}
          data={rows}
          dataKey="day"
          withLegend
          legendProps={{ verticalAlign: 'bottom' }}
          withRightYAxis
          yAxisProps={{ allowDecimals: false }}
          rightYAxisProps={{ domain: [0, 100], tickFormatter: (v: number) => `${v}%` }}
          maxBarWidth={28}
          connectNulls
          series={[
            { name: 'Conversaciones', color: 'navy.3', type: 'bar' },
            { name: '% workflow completo', color: 'green.6', type: 'line', yAxisId: 'right' },
            { name: '% objetivo cumplido', color: 'amber.6', type: 'line', yAxisId: 'right' },
          ]}
        />
      )}
    </Card>
  );
}
