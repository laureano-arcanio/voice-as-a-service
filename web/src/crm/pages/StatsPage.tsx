import { BarChart } from '@mantine/charts';
import { Card, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useStats, useToday } from '../api';
import { STAGES } from '../format';
import { Inbox, NextActions, QueueCard, Replies, ReplyRates, Tasks } from '../components/Panels';
import type { Stage, Stats } from '../types';

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

function ChartCard({ title, help, children }: { title: string; help?: string; children: ReactNode }) {
  return (
    <Card withBorder>
      <Title order={4} mb={help ? 0 : 'md'}>
        {title}
      </Title>
      {help && (
        <Text size="xs" c="dimmed" mb="md">
          {help}
        </Text>
      )}
      {children}
    </Card>
  );
}

const pct = (a: number, b: number) => (b ? `${Math.round((100 * a) / b)} %` : undefined);
const dayLabel = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;

function Charts({ s }: { s: Stats }) {
  const days = s.sent_by_day.map((d) => ({ ...d, day: dayLabel(d.day) }));
  const stages = (Object.keys(STAGES) as Stage[])
    .filter((k) => s.by_stage[k])
    .map((k) => ({ stage: STAGES[k].label, leads: s.by_stage[k] }));
  return (
    <>
      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <ChartCard title="Enviados por día" help="Últimos 30 días, hora de Argentina.">
          {days.some((d) => d.first || d.follow_up) ? (
            <BarChart
              h={240}
              data={days}
              dataKey="day"
              type="stacked"
              withLegend
              legendProps={{ verticalAlign: 'bottom' }}
              yAxisProps={{ allowDecimals: false }}
              maxBarWidth={28}
              series={[
                { name: 'first', label: 'Primer mail', color: 'var(--chart-1)' },
                { name: 'follow_up', label: 'Seguimiento', color: 'var(--chart-2)' },
              ]}
            />
          ) : (
            <EmptyState>Nada enviado en los últimos 30 días.</EmptyState>
          )}
        </ChartCard>
        <ChartCard
          title="Por campaña"
          help="Leads alcanzados con el primer mail, cuántos respondieron y cuántos entraron al sitio."
        >
          {s.by_campaign.length ? (
            <BarChart
              h={240}
              data={s.by_campaign}
              dataKey="slug"
              withLegend
              legendProps={{ verticalAlign: 'bottom' }}
              yAxisProps={{ allowDecimals: false }}
              maxBarWidth={28}
              series={[
                { name: 'reached', label: 'Alcanzados', color: 'var(--chart-1)' },
                { name: 'replied', label: 'Respondieron', color: 'var(--chart-2)' },
                { name: 'clicked', label: 'Entraron al sitio', color: 'var(--chart-3)' },
              ]}
            />
          ) : (
            <EmptyState>Todavía no hay campañas con mails enviados.</EmptyState>
          )}
        </ChartCard>
      </SimpleGrid>
      <ChartCard title="Leads por etapa">
        <BarChart
          h={Math.max(160, stages.length * 32)}
          data={stages}
          dataKey="stage"
          orientation="vertical"
          yAxisProps={{ width: 120 }}
          xAxisProps={{ allowDecimals: false }}
          maxBarWidth={28}
          series={[{ name: 'leads', label: 'Leads', color: 'var(--chart-1)' }]}
        />
      </ChartCard>
    </>
  );
}

export function StatsPage() {
  const stats = useStats();
  const today = useToday();
  return (
    <>
      <PageHeader
        title="Tablero"
        description="Cola de envío, números del embudo y lo pendiente. Para elegir a quién mandar, Leads."
      />
      <Stack gap="md">
        {today.data && <QueueCard q={today.data.queue} />}
        {today.data && <Inbox items={today.data.inbox} />}
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
              <Charts s={s} />
            </Stack>
          )}
        </QueryState>
        <QueryState query={today}>
          {(data) => (
            <Stack gap="md">
              <ReplyRates rates={data.reply_rates} />
              <SimpleGrid cols={{ base: 1, md: 3 }}>
                <Tasks data={data} />
                <Replies data={data} />
                <NextActions data={data} />
              </SimpleGrid>
            </Stack>
          )}
        </QueryState>
      </Stack>
    </>
  );
}
