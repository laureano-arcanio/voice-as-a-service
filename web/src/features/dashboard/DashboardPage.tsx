import { Button, Card, Stack } from '@mantine/core';
import { useLocalStorage } from '@mantine/hooks';
import { IconMessages, IconPhonePlus } from '@tabler/icons-react';
import { Link, useSearchParams } from 'react-router';
import { CollapsibleCard } from '@/components/CollapsibleCard';
import { PageHeader } from '@/components/PageHeader';
import { useIsAdmin } from '@/features/auth/api';
import { useDailyStats, useLiveCalls, useStats } from '@/features/calls/api';
import { NewCallForm } from '@/features/calls/NewCallForm';
import { formatDate } from '@/lib/format';
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
  // El listado vive en /calls: el link lleva los mismos filtros (cliente, agente y periodo).
  const [params] = useSearchParams();
  const listParams = new URLSearchParams(
    [...params].filter(([k]) => ['client', 'agent', 'range', 'from', 'to'].includes(k)),
  ).toString();
  const showClient = isAdmin && !filters.client;
  // Abierto o cerrado, se recuerda por navegador.
  const [newCallOpen, setNewCallOpen] = useLocalStorage<string | null>({
    key: 'atentina:new-call-open',
    defaultValue: 'new-call',
  });

  return (
    <Stack gap="md">
      <PageHeader
        title="Inicio"
        description={`Conversaciones del ${formatDate(`${dates.from}T00:00:00`)} al ${formatDate(`${dates.to}T00:00:00`)}`}
        actions={
          <Button
            component={Link}
            to={`/calls${listParams ? `?${listParams}` : ''}`}
            variant="default"
            leftSection={<IconMessages size={18} />}
          >
            Ver conversaciones
          </Button>
        }
      />
      <Card>
        <DashboardFiltersBar filters={filters} update={update} />
      </Card>

      <CollapsibleCard
        title="Nueva llamada"
        icon={<IconPhonePlus size={20} />}
        opened={newCallOpen === 'new-call'}
        onToggle={() => setNewCallOpen(newCallOpen === 'new-call' ? null : 'new-call')}
      >
        <NewCallForm />
      </CollapsibleCard>

      <LiveCalls calls={live.data ?? []} showClient={showClient} />
      <StatsGrid stats={stats.data} />
      <DailyChart data={daily.data} error={daily.error} />
    </Stack>
  );
}
