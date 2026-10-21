import { Card, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { PageHeader } from '@/components/PageHeader';
import { QueryState } from '@/components/QueryState';
import { useStats } from '../api';
import { STAGES } from '../format';
import type { Stage } from '../types';

function Metric({ label, value, help }: { label: string; value: number; help?: string }) {
  return (
    <Card withBorder p="md">
      <Text className="label">{label}</Text>
      <Text className="metric">{value}</Text>
      {help && (
        <Text size="xs" c="dimmed">
          {help}
        </Text>
      )}
    </Card>
  );
}

const pct = (a: number, b: number) => (b ? `${Math.round((100 * a) / b)} %` : undefined);

export function StatsPage() {
  const stats = useStats();
  return (
    <>
      <PageHeader title="Tablero" description="Números del embudo, calculados de la base." />
      <QueryState query={stats}>
        {(s) => (
          <Stack gap="md">
            <SimpleGrid cols={{ base: 2, sm: 4 }}>
              <Metric label="Leads" value={s.leads} />
              <Metric label="Contactados" value={s.contacted} help="con primer mail enviado" />
              <Metric label="Con seguimiento" value={s.followed_up} />
              <Metric label="Respondieron" value={s.replied} help={pct(s.replied, s.contacted)} />
              <Metric label="Con clics (GA)" value={s.with_clicks} help={pct(s.with_clicks, s.contacted)} />
              <Metric label="Direcciones que rebotaron" value={s.bounced_addresses} />
              <Metric label="Enviados en 7 días" value={s.sent_last_7d} />
            </SimpleGrid>
            <Card withBorder>
              <Title order={4} mb="sm">
                Por etapa
              </Title>
              <SimpleGrid cols={{ base: 2, sm: 4, lg: 6 }}>
                {(Object.keys(STAGES) as Stage[]).map((k) => (
                  <Stack key={k} gap={0}>
                    <Text className="label">{STAGES[k].label}</Text>
                    <Text className="metric">{s.by_stage[k] ?? 0}</Text>
                  </Stack>
                ))}
              </SimpleGrid>
            </Card>
          </Stack>
        )}
      </QueryState>
    </>
  );
}
