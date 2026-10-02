import { Card, Stack } from '@mantine/core';
import { PageHeader } from '@/components/PageHeader';
import { useIsAdmin } from '@/features/auth/api';
import { CallsTable, PAGE_SIZE } from '@/features/dashboard/CallsTable';
import { DashboardFiltersBar } from '@/features/dashboard/DashboardFiltersBar';
import { useDashboardFilters } from '@/features/dashboard/useDashboardFilters';
import { formatDate } from '@/lib/format';
import { useCalls } from './api';

/** Todas las conversaciones (llamadas, API y WhatsApp), con los filtros del inicio en la URL. */
export function ConversationsPage() {
  const isAdmin = useIsAdmin();
  const { filters, update, dates, apiFilters } = useDashboardFilters();
  const calls = useCalls({
    ...apiFilters,
    status: filters.status ? [filters.status] : undefined,
    mode: filters.mode ?? undefined,
    limit: PAGE_SIZE,
    offset: (filters.page - 1) * PAGE_SIZE,
  });

  return (
    <Stack gap="md">
      <PageHeader
        title="Conversaciones"
        description={`Llamadas, chats de WhatsApp y conversaciones por API del ${formatDate(`${dates.from}T00:00:00`)} al ${formatDate(`${dates.to}T00:00:00`)}`}
      />
      <Card>
        <DashboardFiltersBar filters={filters} update={update} />
      </Card>
      <CallsTable
        items={calls.data?.items ?? []}
        total={calls.data?.total ?? 0}
        error={calls.error}
        loading={calls.isPending}
        showClient={isAdmin && !filters.client}
        showWorkflow={isAdmin}
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
