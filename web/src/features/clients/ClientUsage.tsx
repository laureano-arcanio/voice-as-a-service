import { Alert, Anchor, Card, Group, Select, Stack, Text, Title } from '@mantine/core';
import { IconAlertTriangle, IconCircleCheck } from '@tabler/icons-react';
import { Link } from 'react-router';
import { ErrorAlert } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useInferenceUsage } from '@/features/developers/api';
import { formatMonth, formatNumber, formatPeriod, recentMonths } from '@/lib/format';
import { useClientUsage } from './api';
import { InferenceMeters, KeysTable } from './InferenceUsage';
import { UsageMeters } from './UsageMeters';
import { NEAR_PCT, usageStatus, type UsageStatus } from './usageStatus';

type LimitsName = 'tier' | 'plan';

/** El estado de la cuenta en una línea: todo en orden, cerca de un tope o tope alcanzado. */
export function UsageStatusAlert({ status, limitsName }: { status: UsageStatus; limitsName: LimitsName }) {
  const of = limitsName === 'plan' ? 'de tu plan' : 'del tier';
  if (status.level === 'ok') {
    return (
      <Alert color="green" icon={<IconCircleCheck size={18} />} title="Todo en orden">
        Ningún consumo pasa del {NEAR_PCT}% {of}.
      </Alert>
    );
  }
  return (
    <Alert
      color={status.level === 'full' ? 'red' : 'yellow'}
      icon={<IconAlertTriangle size={18} />}
      title={status.level === 'full' ? 'Llegaste a un tope' : 'Cerca de un tope'}
    >
      <Stack gap={2}>
        {status.full.length > 0 && <Text size="sm">Tope alcanzado: {status.full.join(', ')}.</Text>}
        {status.near.length > 0 && (
          <Text size="sm">
            Cerca del tope: {status.near.map((n) => `${n.label} (${formatNumber(n.pct, 0)}%)`).join(', ')}.
          </Text>
        )}
        {status.willExceed.length > 0 && (
          <Text size="sm">Al ritmo actual vas a pasar los {status.willExceed.join(' y los ')} del mes.</Text>
        )}
      </Stack>
    </Alert>
  );
}

/**
 * Todo lo que consume un cliente contra su plan, en un solo lugar: minutos (con la proyección a fin de
 * mes), llamadas, números y la API de inferencia (LLM, STT y TTS, por API key), con el estado general arriba.
 * Lo usan la pestaña Consumo de Reportes y la ficha del cliente (admin).
 */
export function ClientUsage({
  clientId,
  month,
  onMonth,
  limitsName = 'tier',
}: {
  clientId: string;
  month: string;
  onMonth: (m: string) => void;
  limitsName?: LimitsName;
}) {
  const isAdmin = useIsAdmin();
  const months = recentMonths(12);
  const current = months[0];
  const refetch = month === current ? 10_000 : false;
  const usage = useClientUsage(clientId, month, refetch);
  const api = useInferenceUsage(clientId, month, refetch);
  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="wrap">
        <Stack gap={0}>
          <Title order={4}>Consumo del plan</Title>
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
        <>
          <UsageStatusAlert status={usageStatus(usage.data, api.data)} limitsName={limitsName} />
          <Card>
            <Title order={5} mb="md">
              Llamadas y minutos
            </Title>
            <UsageMeters usage={usage.data} limitsName={limitsName} />
          </Card>
        </>
      ) : (
        <Text size="sm" c="dimmed">
          Cargando…
        </Text>
      )}
      <Card>
        <Group justify="space-between" mb="md" wrap="wrap">
          <Stack gap={0}>
            <Title order={5}>API de inferencia</Title>
            <Text size="xs" c="dimmed">
              LLM, STT y TTS por API key. No cuenta los agentes integrados (llamadas y WhatsApp).
            </Text>
          </Stack>
          <Anchor
            component={Link}
            to={isAdmin ? `/admin/inference-requests?client=${clientId}` : '/inference-requests'}
            size="sm"
          >
            Ver los pedidos
          </Anchor>
        </Group>
        {api.isError ? (
          <ErrorAlert error={api.error} onRetry={api.refetch} />
        ) : api.data ? (
          <Stack gap="lg">
            <InferenceMeters usage={api.data} />
            <KeysTable usage={api.data} />
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">
            Cargando…
          </Text>
        )}
      </Card>
    </Stack>
  );
}
