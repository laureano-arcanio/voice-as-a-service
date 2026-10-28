import { Badge, Card, Center, Loader, Stack, Tabs } from '@mantine/core';
import { IconLock } from '@tabler/icons-react';
import type { ComponentType } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { PlanAlert } from '@/components/PlanGate';
import { EmptyState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useFeatureLock, usePlanFeatures } from '@/features/billing/features';
import { formatDate } from '@/lib/format';
import { CallsTab } from './CallsTab';
import { CampaignsTab } from './CampaignsTab';
import { ReportContext } from './format';
import { MessagesTab } from './MessagesTab';
import { OutcomesTab } from './OutcomesTab';
import { PlatformTab } from './PlatformTab';
import { ReportFiltersBar } from './ReportFiltersBar';
import { SummaryTab } from './SummaryTab';
import { TechnicalTab } from './TechnicalTab';
import { TransfersTab } from './TransfersTab';
import type { ReportQuery } from './types';
import { UsageTab } from './UsageTab';
import { useReportFilters } from './useReportFilters';

interface TabDef {
  value: string;
  label: string;
  Component: ComponentType<{ query: ReportQuery }>;
  /** Necesita la funcion `advanced_reports` del plan (docs/REPORTES_PLAN.md, 7). */
  advanced?: boolean;
  /** Solo el admin (vocabulario y datos internos). */
  admin?: boolean;
}

const TABS: TabDef[] = [
  { value: 'summary', label: 'Resumen', Component: SummaryTab },
  { value: 'usage', label: 'Consumo', Component: UsageTab },
  { value: 'calls', label: 'Llamadas', Component: CallsTab },
  { value: 'outcomes', label: 'Resultados', Component: OutcomesTab, advanced: true },
  { value: 'messages', label: 'Mensajes', Component: MessagesTab, advanced: true },
  { value: 'transfers', label: 'Transferencias', Component: TransfersTab, advanced: true },
  { value: 'campaigns', label: 'Campañas', Component: CampaignsTab, advanced: true },
  { value: 'technical', label: 'Técnico', Component: TechnicalTab, admin: true },
];

export function ReportsPage() {
  const isAdmin = useIsAdmin();
  const lock = useFeatureLock('advanced_reports');
  // Hasta saber el plan del cliente no se piden los reportes del plan (la API daria 403).
  const planPending = usePlanFeatures().isLoading;
  const { filters, update, dates, query } = useReportFilters();
  const withPlatform = isAdmin && !filters.client;
  const tabs = TABS.filter((t) => !t.admin || isAdmin);
  const values = [...tabs.map((t) => t.value), ...(withPlatform ? ['platform'] : [])];
  const tab = filters.tab && values.includes(filters.tab) ? filters.tab : 'summary';

  return (
    <Stack gap="md">
      <PageHeader
        title="Reportes"
        description={
          tab === 'usage'
            ? 'Consumo de tu plan en el mes de facturación'
            : `Del ${formatDate(`${dates.from}T00:00:00`)} al ${formatDate(`${dates.to}T00:00:00`)}`
        }
      />
      {/* El consumo es del mes de facturación: solo el admin elige a qué cliente, sin período, agente ni canal. */}
      {(tab !== 'usage' || isAdmin) && (
        <Card>
          <ReportFiltersBar filters={filters} update={update} clientOnly={tab === 'usage'} />
        </Card>
      )}
      <ReportContext.Provider value={{ tab, from: dates.from, to: dates.to }}>
        <Tabs value={tab} onChange={(v) => update({ tab: v === 'summary' ? null : v })} keepMounted={false}>
          <Tabs.List mb="md">
            {tabs.map((t) => (
              <Tabs.Tab
                key={t.value}
                value={t.value}
                rightSection={
                  t.advanced && lock.locked ? (
                    <IconLock
                      size={14}
                      color="var(--mantine-color-gray-6)"
                      aria-label="No incluido en tu plan"
                    />
                  ) : t.admin ? (
                    <Badge color="gray">interno</Badge>
                  ) : undefined
                }
              >
                {t.label}
              </Tabs.Tab>
            ))}
            {withPlatform && (
              <Tabs.Tab value="platform" rightSection={<Badge color="gray">interno</Badge>}>
                Plataforma
              </Tabs.Tab>
            )}
          </Tabs.List>
          {tabs.map((t) => (
            <Tabs.Panel key={t.value} value={t.value}>
              {t.advanced && planPending ? (
                <Center py="xl">
                  <Loader size="sm" />
                </Center>
              ) : t.advanced && lock.locked ? (
                <Stack gap="md">
                  <PlanAlert
                    feature="advanced_reports"
                    what={`el reporte de ${t.label.toLowerCase()}`}
                    hint="Resumen y Llamadas están en todos los planes."
                  />
                  <EmptyState>
                    Con un plan que lo incluya, acá vas a ver este reporte con tus datos.
                  </EmptyState>
                </Stack>
              ) : (
                <t.Component query={query} />
              )}
            </Tabs.Panel>
          ))}
          {withPlatform && (
            <Tabs.Panel value="platform">
              <PlatformTab query={query} onClient={(id) => update({ client: id, agent: null, tab: null })} />
            </Tabs.Panel>
          )}
        </Tabs>
      </ReportContext.Provider>
    </Stack>
  );
}
