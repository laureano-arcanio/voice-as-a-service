import { Badge, Card, Group, Select, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import type { InferenceUsage } from '@/api/types';
import { ErrorAlert } from '@/components/QueryState';
import { UsageMeter } from '@/features/clients/UsageCard';
import { formatMonth, formatNumber, recentMonths } from '@/lib/format';
import { useInferenceUsage } from './api';

type Meter = InferenceUsage['llm_input_tokens'];

/** '01/10/2026 al 31/10/2026' desde fechas YYYY-MM-DD (el fin es exclusivo). Sin husos: son dias, no instantes. */
function dayRange(start: string, endExclusive: string) {
  const f = (d: string) => d.split('-').reverse().join('/');
  const last = new Date(Date.parse(`${endExclusive}T00:00:00Z`) - 86_400_000).toISOString().slice(0, 10);
  return `${f(start)} al ${f(last)}`;
}

/** Un cupo del plan: barra de consumo, o aviso si el plan no incluye ese motor (limite 0). */
function ApiMeter({ label, meter, unit }: { label: string; meter: Meter; unit: string }) {
  if (meter.limit === 0) {
    return (
      <Stack gap={6}>
        <Text className="label">{label}</Text>
        <Badge color="gray" w="fit-content">
          No incluido en el plan
        </Badge>
      </Stack>
    );
  }
  return (
    <UsageMeter
      label={label}
      used={meter.used}
      limit={meter.limit}
      unit={unit}
      hint={
        meter.remaining != null ? `Quedan ${formatNumber(meter.remaining)}${unit}.` : 'Sin límite en el plan.'
      }
    />
  );
}

export function InferenceMeters({ usage }: { usage: InferenceUsage }) {
  return (
    <Stack gap="md">
      <SimpleGrid type="container" cols={{ base: 1, '420px': 2, '900px': 4 }} spacing="lg">
        <ApiMeter label="LLM · tokens de entrada" meter={usage.llm_input_tokens} unit=" tokens" />
        <ApiMeter label="LLM · tokens de salida" meter={usage.llm_output_tokens} unit=" tokens" />
        <ApiMeter label="Síntesis (TTS)" meter={usage.tts_minutes} unit=" min" />
        <ApiMeter label="Transcripción (STT)" meter={usage.stt_minutes} unit=" min" />
      </SimpleGrid>
      <Text size="xs" c="dimmed">
        {usage.rate_limit == null
          ? 'Sin tope de pedidos por minuto.'
          : usage.rate_limit === 0
            ? 'Tu plan no incluye la API de inferencia.'
            : `Hasta ${formatNumber(usage.rate_limit, 0)} pedidos por minuto, sumando los tres motores y todas tus API keys.`}{' '}
        Pedidos del mes: {formatNumber(usage.requests.llm, 0)} LLM, {formatNumber(usage.requests.stt, 0)} STT,{' '}
        {formatNumber(usage.requests.tts, 0)} TTS.
      </Text>
    </Stack>
  );
}

function KeysTable({ usage }: { usage: InferenceUsage }) {
  if (usage.keys.length === 0) return null;
  return (
    <Table.ScrollContainer minWidth={640}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>API key</Table.Th>
            <Table.Th>Acceso</Table.Th>
            <Table.Th ta="right">Pedidos</Table.Th>
            <Table.Th ta="right">Tokens (ent. / sal.)</Table.Th>
            <Table.Th ta="right">TTS (min)</Table.Th>
            <Table.Th ta="right">STT (min)</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {usage.keys.map((k) => (
            <Table.Tr key={k.key_id} style={k.revoked ? { opacity: 0.6 } : undefined}>
              <Table.Td>
                {k.name}{' '}
                <Text span className="mono" size="xs" c="dimmed">
                  {k.prefix}…
                </Text>
                {k.revoked && (
                  <Badge color="gray" ml={6}>
                    revocada
                  </Badge>
                )}
              </Table.Td>
              <Table.Td>
                <Group gap={4}>
                  {k.scopes.map((s) => (
                    <Badge key={s} color="gray">
                      {s}
                    </Badge>
                  ))}
                </Group>
              </Table.Td>
              <Table.Td ta="right">
                {formatNumber(k.requests.llm + k.requests.stt + k.requests.tts, 0)}
              </Table.Td>
              <Table.Td ta="right">
                {formatNumber(k.llm_input_tokens, 0)} / {formatNumber(k.llm_output_tokens, 0)}
              </Table.Td>
              <Table.Td ta="right">{formatNumber(k.tts_minutes, 2)}</Table.Td>
              <Table.Td ta="right">{formatNumber(k.stt_minutes, 2)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

/** Consumo del mes de la API de inferencia (no incluye los agentes integrados), con selector de mes. */
export function InferenceUsageCard({
  clientId,
  month,
  onMonth,
}: {
  clientId: string;
  month: string;
  onMonth: (m: string) => void;
}) {
  const months = recentMonths(12);
  const usage = useInferenceUsage(clientId, month, month === months[0] ? 10_000 : false);
  return (
    <Card>
      <Group justify="space-between" mb="md" wrap="wrap">
        <Stack gap={0}>
          <Title order={4}>Consumo de la API</Title>
          <Text size="xs" c="dimmed">
            LLM, STT y TTS por API key. No cuenta los agentes integrados (llamadas y WhatsApp).
            {usage.data && ` Período: ${dayRange(usage.data.period_start, usage.data.period_end)}`}
          </Text>
        </Stack>
        <Select
          data={months.map((m) => ({ value: m, label: formatMonth(m) }))}
          value={month}
          onChange={(v) => onMonth(v ?? months[0])}
          allowDeselect={false}
          w={200}
          size="xs"
          aria-label="Mes"
        />
      </Group>
      {usage.isError ? (
        <ErrorAlert error={usage.error} onRetry={usage.refetch} />
      ) : usage.data ? (
        <Stack gap="lg">
          <InferenceMeters usage={usage.data} />
          <KeysTable usage={usage.data} />
        </Stack>
      ) : (
        <Text size="sm" c="dimmed">
          Cargando…
        </Text>
      )}
    </Card>
  );
}
