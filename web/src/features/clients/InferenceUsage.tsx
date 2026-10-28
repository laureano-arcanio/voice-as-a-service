import { Badge, Group, SimpleGrid, Stack, Table, Text } from '@mantine/core';
import type { InferenceUsage } from '@/api/types';
import { formatNumber } from '@/lib/format';
import { UsageMeter } from './UsageMeters';

type Meter = InferenceUsage['llm_input_tokens'];

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

/** Consumo de la API por key (LLM, STT y TTS). */
export function KeysTable({ usage }: { usage: InferenceUsage }) {
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
