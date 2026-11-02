import { Card, Stack, Tabs } from '@mantine/core';
import { PageHeader } from '@/components/PageHeader';
import { useIsAdmin } from '@/features/auth/api';
import { CallsTable, PAGE_SIZE } from './CallsTable';
import { CallFiltersBar } from './CallFiltersBar';
import { useCallFilters } from './useCallFilters';
import { formatDate } from '@/lib/format';
import { useCalls } from './api';

/** Una tabla por tipo de conversación en la administración; el cliente ve todas juntas. */
const ADMIN_TABS: { value: string; label: string; modes: string[]; landing?: boolean }[] = [
  { value: 'entrantes', label: 'Entrantes', modes: ['entrante'] },
  { value: 'salientes', label: 'Salientes', modes: ['saliente', 'directa'] },
  { value: 'pruebas', label: 'Pruebas de clientes', modes: ['prueba', 'celular'], landing: false },
  { value: 'link', label: 'Link web', modes: ['web'] },
  { value: 'landing', label: 'Landing', modes: ['prueba'], landing: true },
  { value: 'otras', label: 'WhatsApp y otras', modes: ['whatsapp', 'api', 'loadtest'] },
];

/** Las conversaciones (llamadas, API y WhatsApp), con los filtros en la URL. */
export function ConversationsPage() {
  const isAdmin = useIsAdmin();
  const { filters, update, dates, apiFilters } = useCallFilters();
  const tab = isAdmin ? (ADMIN_TABS.find((t) => t.value === filters.tab) ?? ADMIN_TABS[0]) : null;
  const modeFilter = filters.mode ? [filters.mode] : undefined;
  const calls = useCalls({
    ...apiFilters,
    status: filters.status ? [filters.status] : undefined,
    mode: tab ? (tab.modes.includes(filters.mode ?? '') ? modeFilter : tab.modes) : modeFilter,
    landing: tab?.landing,
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
      {tab && (
        <Tabs
          value={tab.value}
          onChange={(value) => update({ tab: value === ADMIN_TABS[0].value ? null : value, mode: null, answered: null })}
        >
          <Tabs.List>
            {ADMIN_TABS.map((t) => (
              <Tabs.Tab key={t.value} value={t.value}>
                {t.label}
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs>
      )}
      <CallsTable
        // La selección para borrar no pasa de una solapa a otra.
        key={tab?.value}
        title={tab?.label}
        modes={tab?.modes}
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
        onAnswered={!tab || tab.value === 'entrantes' ? (answered) => update({ answered }) : undefined}
        onUser={
          !tab || tab.value === 'entrantes' || tab.value === 'salientes'
            ? (user) => update({ user })
            : undefined
        }
      />
    </Stack>
  );
}
