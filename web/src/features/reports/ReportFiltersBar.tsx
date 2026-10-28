import { Group, Select, Switch } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useAgents } from '@/features/agents/api';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { toIsoDate } from '@/lib/format';
import { CHANNEL_LABEL } from './labels';
import type { Channel } from './types';
import type { ReportFilters, ReportRange } from './useReportFilters';

const RANGES: { value: ReportRange; label: string }[] = [
  { value: '7', label: 'Últimos 7 días' },
  { value: '30', label: 'Últimos 30 días' },
  { value: '90', label: 'Últimos 90 días' },
  { value: 'month', label: 'Este mes' },
  { value: 'prev_month', label: 'Mes anterior' },
  { value: 'custom', label: 'Rango de fechas' },
];

export function ReportFiltersBar({
  filters,
  update,
  clientOnly = false,
}: {
  filters: ReportFilters;
  update: (patch: Partial<ReportFilters>) => void;
  /** Solo el selector de cliente (la pestaña Consumo no depende del período ni de los demás filtros). */
  clientOnly?: boolean;
}) {
  const isAdmin = useIsAdmin();
  const clients = useClients(isAdmin);
  const agents = useAgents(filters.client ?? undefined, true);

  return (
    <Group gap="sm" align="flex-end" wrap="wrap">
      {isAdmin && (
        <Select
          label="Cliente"
          data={[
            { value: '', label: 'Todos' },
            ...(clients.data ?? []).map((c) => ({ value: c.id, label: c.name })),
          ]}
          value={filters.client ?? ''}
          onChange={(v) => update({ client: v || null, agent: null })}
          allowDeselect={false}
          searchable
          w={200}
        />
      )}
      {!clientOnly && (
        <>
          <Select
            label="Agente"
            data={[
              { value: '', label: 'Todos' },
              ...(agents.data ?? []).map((a) => ({
                value: a.id,
                label: a.archived ? `${a.name} (archivado)` : a.name,
              })),
            ]}
            value={filters.agent ?? ''}
            onChange={(v) => update({ agent: v || null })}
            allowDeselect={false}
            searchable
            w={220}
          />
          <Select
            label="Canal"
            data={[
              { value: '', label: 'Todos' },
              ...(Object.keys(CHANNEL_LABEL) as Channel[]).map((c) => ({
                value: c,
                label: CHANNEL_LABEL[c],
              })),
            ]}
            value={filters.channel ?? ''}
            onChange={(v) => update({ channel: (v || null) as Channel | null })}
            allowDeselect={false}
            w={150}
          />
          <Select
            label="Período"
            data={RANGES}
            value={filters.range}
            onChange={(v) => update({ range: (v ?? '30') as ReportRange })}
            allowDeselect={false}
            w={180}
          />
          {filters.range === 'custom' && (
            <DatePickerInput
              type="range"
              label="Fechas"
              placeholder="Desde – hasta"
              value={[filters.from, filters.to]}
              onChange={([from, to]) => update({ from, to })}
              valueFormat="DD/MM/YYYY"
              maxDate={toIsoDate(new Date())}
              allowSingleDateInRange
              clearable
              w={240}
            />
          )}
          <Switch
            label="Incluir pruebas"
            checked={filters.tests}
            onChange={(e) => update({ tests: e.currentTarget.checked })}
            mb={8}
          />
        </>
      )}
    </Group>
  );
}
