import {
  ActionIcon,
  Button,
  Collapse,
  Group,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { IconChevronDown, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { TestValueRow } from './testVariables';

/**
 * Tabla plegable con los valores de prueba del agente. Las filas salen de la definición (ver
 * `useTestVariables`) y "Agregar" suma otras variables para la prueba.
 */
export function TestVariables({
  rows,
  onChange,
  fixedNames = [],
  description,
}: {
  rows: TestValueRow[];
  onChange: (rows: TestValueRow[]) => void;
  /** Las que salen de la definición: no se quitan (volverían a aparecer). */
  fixedNames?: string[];
  description?: string;
}) {
  const [open, setOpen] = useState(true);
  const set = (index: number, patch: Partial<TestValueRow>) =>
    onChange(rows.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  return (
    <Stack gap="xs">
      <UnstyledButton
        onClick={() => setOpen((x) => !x)}
        aria-expanded={open}
        aria-controls="test-variables-body"
      >
        <Group gap={6} wrap="nowrap">
          <Text size="sm" fw={600}>
            Valores de prueba
          </Text>
          <Text size="xs" c="dimmed">
            {rows.length ? `${rows.length} variable${rows.length === 1 ? '' : 's'}` : 'sin variables'}
          </Text>
          <IconChevronDown
            size={16}
            className="chevron"
            aria-hidden
            style={{ transform: open ? 'rotate(180deg)' : undefined }}
          />
        </Group>
      </UnstyledButton>
      <Collapse in={open} id="test-variables-body">
        <Stack gap="xs">
          <Text size="xs" c="dimmed">
            {description ??
              'Se mandan como variables de la prueba: el agente las ve donde su prompt, su primer mensaje o su análisis las nombran. Se recuerdan en esta pestaña.'}
          </Text>
          {rows.length > 0 && (
            <Table.ScrollContainer minWidth={420}>
              <Table>
                <Table.Tbody>
                  {rows.map((r, i) => (
                    <Table.Tr key={i}>
                      <Table.Td w="38%">
                        <TextInput
                          aria-label={`Variable de prueba ${i + 1}`}
                          placeholder="otra_variable"
                          classNames={{ input: 'mono' }}
                          size="xs"
                          value={r.name}
                          onChange={(e) => set(i, { name: e.currentTarget.value })}
                        />
                      </Table.Td>
                      <Table.Td>
                        <TextInput
                          aria-label={`Valor de ${r.name || `la variable ${i + 1}`}`}
                          placeholder="Vacío"
                          size="xs"
                          value={r.value}
                          onChange={(e) => set(i, { value: e.currentTarget.value })}
                        />
                      </Table.Td>
                      <Table.Td w={40}>
                        {!fixedNames.includes(r.name) && (
                          <Tooltip label="Quitar" withArrow>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              aria-label={`Quitar la variable de prueba ${i + 1}`}
                              onClick={() => onChange(rows.filter((_, j) => j !== i))}
                            >
                              <IconTrash size={18} />
                            </ActionIcon>
                          </Tooltip>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )}
          <Button
            variant="subtle"
            size="compact-sm"
            leftSection={<IconPlus size={16} />}
            w="fit-content"
            onClick={() => onChange([...rows, { name: '', value: '' }])}
          >
            Agregar
          </Button>
        </Stack>
      </Collapse>
    </Stack>
  );
}
