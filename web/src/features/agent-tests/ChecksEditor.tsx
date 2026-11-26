import { ActionIcon, Autocomplete, Group, Select, Stack, Text, TextInput } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { CHECK_TYPES, type Check, checkLabel } from './api';

function newCheck(type: string): Check {
  switch (type) {
    case 'usa_herramienta':
      return { type, tool: '' };
    case 'no_usa_herramienta':
      return { type };
    case 'deriva_a':
      return { type, area: '' };
    case 'dice':
    case 'no_dice':
    case 'empieza_con':
      return { type, text: '' };
    default:
      return { type };
  }
}

/** Los chequeos del caso: tipo, y slug, area o texto segun corresponda (app/agent_tests/checks.py). */
export function ChecksEditor({
  value,
  onChange,
  tools = [],
  areas = [],
  disabled = false,
}: {
  value: Check[];
  onChange: (checks: Check[]) => void;
  tools?: string[];
  areas?: string[];
  disabled?: boolean;
}) {
  const update = (i: number, patch: Partial<Check>) =>
    onChange(value.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  const remove = (i: number) => onChange(value.filter((_, j) => j !== i));

  return (
    <Stack gap="xs">
      {value.length === 0 && (
        <Text size="sm" c="dimmed">
          Sin chequeos: el caso solo guarda la respuesta. Agregá lo que tenía que pasar.
        </Text>
      )}
      {value.map((check, i) => (
        <Group key={i} align="flex-start" gap="xs" wrap="nowrap">
          <Select
            aria-label={`Tipo del chequeo ${i + 1}`}
            data={CHECK_TYPES.map(([value, label]) => ({ value, label }))}
            value={check.type}
            onChange={(type) => type && onChange(value.map((c, j) => (j === i ? newCheck(type) : c)))}
            allowDeselect={false}
            disabled={disabled}
            w={230}
          />
          {check.type === 'usa_herramienta' && (
            <>
              <Autocomplete
                aria-label="Herramienta"
                placeholder="slug de la herramienta"
                data={tools}
                value={check.tool ?? ''}
                onChange={(tool) => update(i, { tool })}
                disabled={disabled}
                style={{ flex: 1 }}
              />
              <TextInput
                aria-label="Los argumentos contienen"
                placeholder="argumentos contienen (opcional)"
                value={check.argumentos_contienen ?? ''}
                onChange={(e) => update(i, { argumentos_contienen: e.currentTarget.value })}
                disabled={disabled}
                style={{ flex: 1 }}
              />
            </>
          )}
          {check.type === 'no_usa_herramienta' && (
            <Autocomplete
              aria-label="Herramienta"
              placeholder="cualquiera (opcional)"
              data={tools}
              value={check.tool ?? ''}
              onChange={(tool) => update(i, { tool })}
              disabled={disabled}
              style={{ flex: 1 }}
            />
          )}
          {check.type === 'deriva_a' && (
            <Autocomplete
              aria-label="Área"
              placeholder="nombre del área"
              data={areas}
              value={check.area ?? ''}
              onChange={(area) => update(i, { area })}
              disabled={disabled}
              style={{ flex: 1 }}
            />
          )}
          {(check.type === 'dice' || check.type === 'no_dice' || check.type === 'empieza_con') && (
            <TextInput
              aria-label={checkLabel(check.type)}
              placeholder="texto"
              value={check.text ?? ''}
              onChange={(e) => update(i, { text: e.currentTarget.value })}
              disabled={disabled}
              style={{ flex: 1 }}
              maxLength={500}
            />
          )}
          <ActionIcon
            variant="subtle"
            color="red"
            aria-label="Quitar chequeo"
            onClick={() => remove(i)}
            disabled={disabled}
          >
            <IconTrash size={16} />
          </ActionIcon>
        </Group>
      ))}
      <Group>
        <Select
          placeholder="Agregar chequeo"
          data={CHECK_TYPES.map(([value, label]) => ({ value, label }))}
          value={null}
          onChange={(type) => type && onChange([...value, newCheck(type)])}
          disabled={disabled}
          leftSection={<IconPlus size={14} />}
          w={230}
          aria-label="Agregar chequeo"
        />
      </Group>
    </Stack>
  );
}
