import { ActionIcon, Button, Group, Stack, Table, Text, TextInput, Tooltip } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { isSystemVariable, useVariableCatalog, usedVariables } from '@/components/variables';
import {
  type Draft,
  MAX_VARIABLE_VALUE,
  MAX_VARIABLES,
  newVariable,
  sectionId,
  type VariableDraft,
  variableNameError,
} from './draft';

/** Nombres que nombran los textos del agente, sin las del sistema (los valores los completa la plataforma). */
function usedNames(draft: Draft, catalog: Parameters<typeof isSystemVariable>[1]): string[] {
  const text = [draft.prompt, draft.firstMessage, draft.analysis.instructions].join('\n');
  return usedVariables(text).filter((n) => !isSystemVariable(n, catalog));
}

/**
 * Variables declaradas del agente (el "Default Dynamic Variables" de Retell): nombre, qué es y su valor por
 * defecto. Avisa, sin bloquear, las que los textos nombran y no están declaradas y las declaradas sin usar.
 */
export function VariablesSection({
  draft,
  update,
}: {
  draft: Draft;
  update: (fn: (d: Draft) => Draft) => void;
}) {
  const catalog = useVariableCatalog().data;
  const variables = draft.variables;
  const names = variables.map((v) => v.name);
  const used = usedNames(draft, catalog);
  const undeclared = used.filter((n) => !names.some((d) => d.trim() === n));
  const unused = names.filter((n) => n.trim() && !used.includes(n.trim()));

  const set = (index: number, patch: Partial<VariableDraft>) =>
    update((d) => ({
      ...d,
      variables: d.variables.map((v, i) => (i === index ? { ...v, ...patch } : v)),
    }));
  const remove = (index: number) =>
    update((d) => ({ ...d, variables: d.variables.filter((_, i) => i !== index) }));

  const declare = () =>
    update((d) => ({
      ...d,
      variables: [
        ...d.variables,
        ...undeclared
          .filter((n) => !d.variables.some((v) => v.name.trim() === n))
          .map((n) => ({ ...newVariable(d.variables), name: n })),
      ],
    }));

  return (
    <Stack gap="sm">
      {variables.length === 0 ? (
        <Text size="sm" c="dimmed">
          Sin variables declaradas. Las que el prompt nombre y nadie declare vienen del pedido de la llamada,
          el contacto o el pre-call.
        </Text>
      ) : (
        <Table.ScrollContainer minWidth={620}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={200}>Variable</Table.Th>
                <Table.Th>Descripción</Table.Th>
                <Table.Th w={200}>Valor por defecto</Table.Th>
                <Table.Th w={48} />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {variables.map((v, i) => {
                const nameError = v.name.trim() ? variableNameError(v.name, catalog, names, i) : undefined;
                const value = String(v.default);
                return (
                  <Table.Tr key={v.key} id={sectionId(`variable-${v.key}`)} style={{ scrollMarginTop: 140 }}>
                    <Table.Td>
                      <TextInput
                        aria-label={`Nombre de la variable ${i + 1}`}
                        placeholder="deuda"
                        classNames={{ input: 'mono' }}
                        size="xs"
                        value={v.name}
                        error={nameError}
                        onChange={(e) => set(i, { name: e.currentTarget.value })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <TextInput
                        aria-label={`Descripción de la variable ${i + 1}`}
                        placeholder="Qué es y de dónde puede venir"
                        size="xs"
                        value={v.description}
                        maxLength={300}
                        onChange={(e) => set(i, { description: e.currentTarget.value })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <TextInput
                        aria-label={`Valor por defecto de la variable ${i + 1}`}
                        placeholder="Vacío"
                        classNames={{ input: 'mono' }}
                        size="xs"
                        value={value}
                        error={
                          value.length > MAX_VARIABLE_VALUE
                            ? `Hasta ${MAX_VARIABLE_VALUE} caracteres.`
                            : undefined
                        }
                        onChange={(e) => set(i, { default: e.currentTarget.value })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Tooltip label="Quitar variable" withArrow>
                        <ActionIcon
                          variant="subtle"
                          color="red"
                          aria-label={`Quitar la variable ${i + 1}`}
                          onClick={() => remove(i)}
                        >
                          <IconTrash size={18} />
                        </ActionIcon>
                      </Tooltip>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      <Button
        variant="subtle"
        size="compact-sm"
        leftSection={<IconPlus size={16} />}
        w="fit-content"
        disabled={variables.length >= MAX_VARIABLES}
        onClick={() => update((d) => ({ ...d, variables: [...d.variables, newVariable(d.variables)] }))}
      >
        Agregar variable
      </Button>

      {undeclared.length > 0 && (
        <Group justify="space-between" align="flex-start" gap="xs" wrap="nowrap">
          <Text size="xs" c="yellow.8" data-testid="undeclared-variables">
            Usadas en el prompt sin declarar: {undeclared.map((n) => `{{${n}}}`).join(', ')}
          </Text>
          <Button variant="default" size="compact-xs" onClick={declare}>
            Declarar
          </Button>
        </Group>
      )}
      {unused.length > 0 && (
        <Text size="xs" c="dimmed" data-testid="unused-variables">
          Declaradas sin usar: {unused.map((n) => `{{${n}}}`).join(', ')}
        </Text>
      )}
    </Stack>
  );
}
