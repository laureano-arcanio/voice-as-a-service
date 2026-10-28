import { Group, Progress, SimpleGrid, Stack, Text } from '@mantine/core';
import type { MinutesUsage, Usage } from '@/api/types';
import { formatNumber, recentMonths, usageColor, usagePercent } from '@/lib/format';

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

/** Topes de cantidad de llamadas. La hora y el dia son los en curso: solo se muestran en el mes actual. */
const CALL_COUNTS = [
  { key: 'calls_hour', label: 'Llamadas esta hora', currentOnly: true },
  { key: 'calls_day', label: 'Llamadas hoy', currentOnly: true },
  { key: 'calls_month', label: 'Llamadas del mes', currentOnly: false },
] as const;

/** "Quedan 90 min." y, en el mes en curso, a dónde llega al ritmo actual. */
function minutesHint(m: MinutesUsage, noLimit: string): string {
  const left = m.remaining_minutes != null ? `Quedan ${formatNumber(m.remaining_minutes)} min.` : noLimit;
  if (m.projected_minutes == null || !m.used_minutes) return left;
  const over = m.limit_minutes != null && m.projected_minutes > m.limit_minutes;
  return `${left} Al ritmo actual: ${formatNumber(m.projected_minutes, 0)} min a fin de mes${over ? ', más de lo que incluye el plan' : ''}.`;
}

export function UsageMeters({ usage, limitsName = 'tier' }: { usage: Usage; limitsName?: LimitsName }) {
  const noLimit = `Sin límite en el ${limitsName}.`;
  const isCurrentMonth = usage.month === recentMonths(1)[0];
  return (
    <SimpleGrid type="container" cols={{ base: 1, '420px': 2, '900px': 4 }} spacing="lg">
      <UsageMeter
        label="Minutos entrantes"
        used={usage.inbound.used_minutes}
        limit={usage.inbound.limit_minutes}
        unit=" min"
        hint={minutesHint(usage.inbound, noLimit)}
      />
      <UsageMeter
        label="Minutos salientes"
        used={usage.outbound.used_minutes}
        limit={usage.outbound.limit_minutes}
        unit=" min"
        hint={minutesHint(usage.outbound, noLimit)}
      />
      <UsageMeter
        label="Llamadas simultáneas"
        used={usage.active_calls}
        limit={usage.max_concurrent_calls}
        hint={`Activas ahora contra el tope del ${limitsName}.`}
      />
      {CALL_COUNTS.filter((c) => usage[c.key].limit != null && (isCurrentMonth || !c.currentOnly)).map(
        (c) => {
          const { used, limit } = usage[c.key];
          return (
            <UsageMeter
              key={c.key}
              label={c.label}
              used={used}
              limit={limit}
              hint={`Quedan ${Math.max((limit ?? 0) - used, 0)}.`}
            />
          );
        },
      )}
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
    </SimpleGrid>
  );
}
