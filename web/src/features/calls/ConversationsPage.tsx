import { Card, Stack } from '@mantine/core';
import { PageHeader } from '@/components/PageHeader';
import { useIsAdmin } from '@/features/auth/api';
import { CallsTable, PAGE_SIZE } from './CallsTable';
import { CallFiltersBar } from './CallFiltersBar';
import { useCallFilters } from './useCallFilters';
import { formatDate } from '@/lib/format';
import { useCalls } from './api';

/** Todas las conversaciones (llamadas, API y WhatsApp), con los filtros en la URL. */
export function ConversationsPage() {
  const isAdmin = useIsAdmin();
  const { filters, update, dates, apiFilters } = useCallFilters();
  const calls = useCalls({
    ...apiFilters,
    status: filters.status ? [filters.status] : undefined,
    mode: filters.mode ?? undefined,
    answered_by: filters.answered ?? undefined,
    user_id: filters.user ?? undefined,
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
        <CallFiltersBar filters={filters} update={update} />
      </Card>
      <CallsTable
        items={calls.data?.items ?? []}
        total={calls.data?.total ?? 0}
        error={calls.error}
        loading={calls.isPending}
        showClient={isAdmin && !filters.client}
        showWorkflow={isAdmin}
        selectable={isAdmin}
        page={filters.page}
        status={filters.status}
        mode={filters.mode}
        answered={filters.answered}
        userId={filters.user}
        clientId={filters.client}
        onPage={(page) => update({ page })}
        onStatus={(status) => update({ status })}
        onMode={(mode) => update({ mode })}
        onAnswered={(answered) => update({ answered })}
        onUser={(user) => update({ user })}
      />
    </Stack>
  );
}
