import { ActionIcon, Group, Stack, Switch, Text, Tooltip } from '@mantine/core';
import { DatePickerInput, TimeInput } from '@mantine/dates';
import { IconPlus, IconX } from '@tabler/icons-react';
import { DAY_LABEL, DAYS, type Day, type Range, type ScheduleDraft } from './schedule';

/**
 * Editor del horario (areas de derivacion y numeros que atiende el equipo): atiende siempre, franjas por dia y
 * dias cerrados. El error de validacion lo muestra el que lo usa, pasandolo en `error`.
 */
export function ScheduleFields({
  value,
  onChange,
  error,
}: {
  value: ScheduleDraft;
  onChange: (next: ScheduleDraft) => void;
  error?: React.ReactNode;
}) {
  const set = (next: Partial<ScheduleDraft>) => onChange({ ...value, ...next });
  const setDay = (day: Day, ranges: Range[]) => set({ week: { ...value.week, [day]: ranges } });
  return (
    <>
      <Switch
        label="Atiende siempre"
        description="Sin horario: todos los días, a toda hora."
        checked={value.always}
        onChange={(e) => set({ always: e.currentTarget.checked })}
      />
      {!value.always && (
        <>
          <Stack gap={6}>
            {DAYS.map((d) => (
              <DayRanges key={d} day={d} ranges={value.week[d]} onChange={(r) => setDay(d, r)} />
            ))}
          </Stack>
          <DatePickerInput
            type="multiple"
            label="Días cerrados"
            description="Feriados o días sin atención, aunque tengan horario."
            placeholder="Ninguno"
            valueFormat="DD/MM/YYYY"
            value={value.closed}
            onChange={(dates) => set({ closed: dates.map(String) })}
            clearable
          />
        </>
      )}
      {error && (
        <Text size="sm" c="red" role="alert">
          {error}
        </Text>
      )}
    </>
  );
}

/** Las franjas de un dia; sin ninguna, el dia esta cerrado. */
function DayRanges({ day, ranges, onChange }: { day: Day; ranges: Range[]; onChange: (r: Range[]) => void }) {
  const label = DAY_LABEL[day];
  const set = (i: number, j: 0 | 1, value: string) =>
    onChange(ranges.map((r, k) => (k === i ? (j === 0 ? [value, r[1]] : [r[0], value]) : r)));
  return (
    <Group align="flex-start" gap="xs" wrap="nowrap">
      <Text size="sm" fw={600} w={86} pt={6} style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Stack gap={6} style={{ flex: 1 }}>
        {ranges.length === 0 && (
          <Text size="sm" c="dimmed" pt={6}>
            Cerrado
          </Text>
        )}
        {ranges.map(([from, to], i) => (
          <Group key={i} gap={6} wrap="nowrap">
            <TimeInput
              aria-label={`${label}, franja ${i + 1}, desde`}
              value={from}
              onChange={(e) => set(i, 0, e.currentTarget.value)}
              w={110}
            />
            <Text size="sm" c="dimmed">
              a
            </Text>
            <TimeInput
              aria-label={`${label}, franja ${i + 1}, hasta`}
              value={to}
              onChange={(e) => set(i, 1, e.currentTarget.value)}
              w={110}
            />
            <Tooltip label="Quitar franja" withArrow>
              <ActionIcon
                variant="subtle"
                color="gray"
                aria-label={`Quitar franja ${i + 1} del ${label.toLowerCase()}`}
                onClick={() => onChange(ranges.filter((_, k) => k !== i))}
              >
                <IconX size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
        ))}
      </Stack>
      <Tooltip label="Agregar franja" withArrow>
        <ActionIcon
          variant="default"
          aria-label={`Agregar franja el ${label.toLowerCase()}`}
          onClick={() => onChange([...ranges, ranges.length ? ['', ''] : ['09:00', '18:00']])}
        >
          <IconPlus size={16} />
        </ActionIcon>
      </Tooltip>
    </Group>
  );
}
