import { Accordion, Card, Stack, Text } from '@mantine/core';
import { useLocalStorage } from '@mantine/hooks';
import { IconPhonePlus } from '@tabler/icons-react';
import { PageHeader } from '@/components/PageHeader';
import { useIsAdmin } from '@/features/auth/api';
import { useCalls, useDailyStats, useLiveCalls, useStats } from '@/features/calls/api';
import { NewCallForm } from '@/features/calls/NewCallForm';
import { formatDate } from '@/lib/format';
import { CallsTable, PAGE_SIZE } from './CallsTable';
import { DailyChart } from './DailyChart';
import { DashboardFiltersBar } from './DashboardFiltersBar';
import { LiveCalls } from './LiveCalls';
import { StatsGrid } from './StatsGrid';
import { useDashboardFilters } from './useDashboardFilters';

export function DashboardPage() {
  const isAdmin = useIsAdmin();
  const { filters, update, dates, apiFilters } = useDashboardFilters();
  const stats = useStats(apiFilters);
  const daily = useDailyStats({ ...apiFilters, date_from: dates.from, date_to: dates.to });
  const live = useLiveCalls({ client_id: apiFilters.client_id, agent_id: apiFilters.agent_id });
  const calls = useCalls({
    ...apiFilters,
    status: filters.status ? [filters.status] : undefined,
    mode: filters.mode ?? undefined,
    limit: PAGE_SIZE,
    offset: (filters.page - 1) * PAGE_SIZE,
  });
  const showClient = isAdmin && !filters.client;
  // Abierto o cerrado, se recuerda por navegador.
  const [newCallOpen, setNewCallOpen] = useLocalStorage<string | null>({
    key: 'oime:new-call-open',
    defaultValue: 'new-call',
  });

  return (
    <Stack gap="md">
      <PageHeader
        title="Inicio"
        description={`Conversaciones del ${formatDate(`${dates.from}T00:00:00`)} al ${formatDate(`${dates.to}T00:00:00`)}`}
      />
      <Card p="md">
        <DashboardFiltersBar filters={filters} update={update} />
      </Card>

      <Accordion variant="separated" radius="md" value={newCallOpen} onChange={setNewCallOpen}>
        <Accordion.Item value="new-call">
          <Accordion.Control icon={<IconPhonePlus size={20} />}>
            <Text fw={600}>Nueva llamada</Text>
          </Accordion.Control>
          <Accordion.Panel>
            <NewCallForm />
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>

      <LiveCalls calls={live.data ?? []} showClient={showClient} />
      <StatsGrid stats={stats.data} />
      <DailyChart data={daily.data} error={daily.error} />
      <CallsTable
        items={calls.data?.items ?? []}
        total={calls.data?.total ?? 0}
        error={calls.error}
        loading={calls.isPending}
        showClient={showClient}
        page={filters.page}
        status={filters.status}
        mode={filters.mode}
        onPage={(page) => update({ page })}
        onStatus={(status) => update({ status })}
        onMode={(mode) => update({ mode })}
      />
    </Stack>
  );
}
