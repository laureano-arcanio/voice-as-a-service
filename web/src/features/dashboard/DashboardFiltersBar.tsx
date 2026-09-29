import { Group, Select } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useAgents } from '@/features/agents/api';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { toIsoDate } from '@/lib/format';
import type { DashboardFilters, RangePreset } from './useDashboardFilters';

const RANGES = [
  { value: '7', label: 'Última semana' },
  { value: '30', label: 'Último mes' },
  { value: 'custom', label: 'Rango de fechas' },
];

export function DashboardFiltersBar({
  filters,
  update,
}: {
  filters: DashboardFilters;
  update: (patch: Partial<DashboardFilters>) => void;
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
        label="Período"
        data={RANGES}
        value={filters.range}
        onChange={(v) => update({ range: (v ?? '30') as RangePreset })}
        allowDeselect={false}
        w={170}
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
    </Group>
  );
}
