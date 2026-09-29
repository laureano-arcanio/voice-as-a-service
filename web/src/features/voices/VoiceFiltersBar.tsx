import { Group, NumberInput, Select } from '@mantine/core';
import type { VoiceFilters } from './api';

const GENEROS = [
  { value: '', label: 'Todas' },
  { value: 'mujer', label: 'Mujeres' },
  { value: 'hombre', label: 'Hombres' },
];

function num(v: string | number): number | '' {
  return typeof v === 'number' ? v : v === '' ? '' : Number(v) || '';
}

export function VoiceFiltersBar({
  value,
  onChange,
}: {
  value: VoiceFilters;
  onChange: (v: VoiceFilters) => void;
}) {
  return (
    <Group gap="xs" align="flex-end" wrap="wrap">
      <Select
        label="Género"
        data={GENEROS}
        value={value.genero}
        onChange={(g) => onChange({ ...value, genero: g ?? '' })}
        allowDeselect={false}
        w={120}
        size="xs"
      />
      <NumberInput
        label="WER máx. (%)"
        value={value.wer_max}
        onChange={(v) => onChange({ ...value, wer_max: num(v) })}
        min={0}
        step={0.5}
        decimalScale={1}
        decimalSeparator=","
        w={110}
        size="xs"
      />
      <NumberInput
        label="car/s mín."
        value={value.car_min}
        onChange={(v) => onChange({ ...value, car_min: num(v) })}
        min={0}
        step={0.5}
        decimalScale={1}
        decimalSeparator=","
        w={100}
        size="xs"
      />
      <NumberInput
        label="car/s máx."
        value={value.car_max}
        onChange={(v) => onChange({ ...value, car_max: num(v) })}
        min={0}
        step={0.5}
        decimalScale={1}
        decimalSeparator=","
        w={100}
        size="xs"
      />
    </Group>
  );
}

export const VOICE_METRICS_HINT =
  'WER: errores del ASR sobre frases de dominio (menos es más claro). car/s: velocidad del habla.';
