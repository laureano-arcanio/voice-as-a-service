import { Stack } from '@mantine/core';
import { InferenceUsageCard } from '@/features/developers/InferenceUsageCard';
import { UsageCard } from './UsageCard';

/** Consumo del mes de un cliente: llamadas y numeros contra el tier, y la API de inferencia (LLM, STT y TTS). */
export function ClientUsage({
  clientId,
  month,
  onMonth,
  limitsName,
}: {
  clientId: string;
  month: string;
  onMonth: (m: string) => void;
  limitsName?: 'tier' | 'plan';
}) {
  return (
    <Stack gap="md">
      <UsageCard clientId={clientId} month={month} onMonth={onMonth} limitsName={limitsName} />
      <InferenceUsageCard clientId={clientId} month={month} onMonth={onMonth} />
    </Stack>
  );
}
