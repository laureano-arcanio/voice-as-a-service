import { Select, Stack, Text } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useState } from 'react';
import { formatNumber } from '@/lib/format';
import { EMPTY_VOICE_FILTERS, useVoices, type VoiceFilters } from './api';
import { VOICE_METRICS_HINT, VoiceFiltersBar } from './VoiceFiltersBar';

const GENERO_LABEL: Record<string, string> = { mujer: 'mujer', hombre: 'hombre' };

/** Voz de la llamada: '' = la del agente; o una del catalogo, filtrada por metricas. */
export function VoicePicker({
  value,
  onChange,
  agentVoice,
}: {
  value: string;
  onChange: (voice: string) => void;
  agentVoice: string | null | undefined;
}) {
  const [filters, setFilters] = useState<VoiceFilters>(EMPTY_VOICE_FILTERS);
  const [debounced] = useDebouncedValue(filters, 300);
  const voices = useVoices(debounced);

  const items = voices.data ?? [];
  const data = [
    { value: '', label: `La del agente${agentVoice ? ` (${agentVoice})` : ''}` },
    ...items.map((v) => ({
      value: v.nombre,
      label: `${v.nombre} · ${GENERO_LABEL[v.genero] ?? v.genero} · WER ${formatNumber(v.wer)}% · ${formatNumber(v.car_s)} car/s`,
    })),
  ];
  // Si el filtro deja afuera la voz elegida, se sigue mostrando.
  if (value && !items.some((v) => v.nombre === value)) data.splice(1, 0, { value, label: value });

  return (
    <Stack gap={6}>
      <Select
        label="Voz"
        data={data}
        value={value}
        onChange={(v) => onChange(v ?? '')}
        allowDeselect={false}
        searchable
        nothingFoundMessage="Ninguna voz con esos filtros"
      />
      <VoiceFiltersBar value={filters} onChange={setFilters} />
      <Text size="xs" c="dimmed">
        {VOICE_METRICS_HINT}
        {voices.data && ` ${voices.data.length} voces con estos filtros.`}
      </Text>
    </Stack>
  );
}
