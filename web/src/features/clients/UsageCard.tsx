import { Card, Group, Progress, Select, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import type { Usage } from '@/api/types';
import { ErrorAlert } from '@/components/QueryState';
import {
  formatMonth,
  formatPeriod,
  formatNumber,
  recentMonths,
  usageColor,
  usagePercent,
} from '@/lib/format';
import { useClientUsage } from './api';

export interface MeterProps {
  label: string;
  used: number;
  limit: number | null;
  unit?: string;
  hint?: string;
}

/** Como se nombran los limites: "tier" para el equipo, "plan" para el cliente. */
type LimitsName = 'tier' | 'plan';

/** Consumo contra un limite: barra coloreada por % usado; sin limite, "Ilimitado". */
export function UsageMeter({ label, used, limit, unit = '', hint }: MeterProps) {
  const pct = usagePercent(used, limit);
  const color = usageColor(pct);
  return (
    <Stack gap={6}>
      <Text className="label">{label}</Text>
      <Group justify="space-between" gap="xs" align="baseline" wrap="nowrap">
        <Text className="metric">
          {formatNumber(used)}
          <Text span size="sm" c="dimmed" fw={500} ff="text" style={{ letterSpacing: 0 }}>
            {' / '}
            {limit == null ? 'Ilimitado' : `${formatNumber(limit)}${unit}`}
          </Text>
        </Text>
        {pct != null && (
          <Text size="xs" c={color === 'green' ? 'dimmed' : color} fw={600}>
            {formatNumber(pct, 0)}%
          </Text>
        )}
      </Group>
      <Progress
        value={pct == null ? 0 : Math.min(pct, 100)}
        color={color}
        size="md"
        aria-label={`${label}: ${pct == null ? 'ilimitado' : `${formatNumber(pct, 0)}% usado`}`}
      />
      {hint && (
        <Text size="xs" c="dimmed">
          {hint}
        </Text>
      )}
    </Stack>
  );
}

export function UsageMeters({ usage, limitsName = 'tier' }: { usage: Usage; limitsName?: LimitsName }) {
  const noLimit = `Sin límite en el ${limitsName}.`;
  return (
    <SimpleGrid type="container" cols={{ base: 1, '420px': 2, '900px': 4 }} spacing="lg">
      <UsageMeter
        label="Llamadas simultáneas"
        used={usage.active_calls}
        limit={usage.max_concurrent_calls}
        hint={`Activas ahora contra el tope del ${limitsName}.`}
      />
      <UsageMeter
        label="Números"
        used={usage.phone_numbers.used}
        limit={usage.phone_numbers.limit}
        hint={
          usage.phone_numbers.limit != null
            ? `Quedan ${Math.max(usage.phone_numbers.limit - usage.phone_numbers.used, 0)} por asignar.`
            : noLimit
        }
      />
      <UsageMeter
        label="Minutos entrantes"
        used={usage.inbound.used_minutes}
        limit={usage.inbound.limit_minutes}
        unit=" min"
        hint={
          usage.inbound.remaining_minutes != null
            ? `Quedan ${formatNumber(usage.inbound.remaining_minutes)} min.`
            : noLimit
        }
      />
      <UsageMeter
        label="Minutos salientes"
        used={usage.outbound.used_minutes}
        limit={usage.outbound.limit_minutes}
        unit=" min"
        hint={
          usage.outbound.remaining_minutes != null
            ? `Quedan ${formatNumber(usage.outbound.remaining_minutes)} min.`
            : noLimit
        }
      />
    </SimpleGrid>
  );
}

/** Consumo del mes de un cliente, con selector de mes. */
export function UsageCard({
  clientId,
  month,
  onMonth,
  limitsName,
}: {
  clientId: string;
  month: string;
  onMonth: (m: string) => void;
  limitsName?: LimitsName;
}) {
  const months = recentMonths(12);
  const current = months[0];
  const usage = useClientUsage(clientId, month, month === current ? 10_000 : false);
  return (
    <Card>
      <Group justify="space-between" mb="md" wrap="wrap">
        <Stack gap={0}>
          <Title order={4}>Consumo</Title>
          {usage.data && (
            <Text size="xs" c="dimmed">
              Período: {formatPeriod(usage.data.period_start, usage.data.period_end)}
            </Text>
          )}
        </Stack>
        <Select
          data={months.map((m) => ({ value: m, label: formatMonth(m) }))}
          value={month}
          onChange={(v) => onMonth(v ?? current)}
          allowDeselect={false}
          w={200}
          size="xs"
          aria-label="Mes"
        />
      </Group>
      {usage.isError ? (
        <ErrorAlert error={usage.error} onRetry={usage.refetch} />
      ) : usage.data ? (
        <UsageMeters usage={usage.data} limitsName={limitsName} />
      ) : (
        <Text size="sm" c="dimmed">
          Cargando…
        </Text>
      )}
    </Card>
  );
}
