import { Alert, Badge, Button, Card, Group, Modal, Stack, Table, Text } from '@mantine/core';
import { useState } from 'react';
import {
  caseResults,
  fallbackCount,
  isFinished,
  useTestRun,
  variantLabel,
  type CaseResult,
  type VariantResult,
} from './api';
import { RunResults } from './RunResults';
import { RunStatus } from './RunStatus';

const variant = (item: CaseResult, key: string): VariantResult | undefined =>
  item.variants.find((v) => v.key === key);

/** "pasa X/N" con los respaldos, para las celdas de la comparación. */
const cell = (v: VariantResult | undefined) => {
  if (!v) return '–';
  const fallbacks = fallbackCount(v);
  return `pasa ${v.passed}/${v.total}${fallbacks > 0 ? ` · ${fallbacks} respaldo` : ''}`;
};

/** Una columna por variante de la corrida (publicada, cambios y/o modelos), en su orden (T6). */
type RunVariant = { key: string; label: string | null };

const runVariants = (variants: Record<string, unknown>[] | undefined): RunVariant[] =>
  (variants ?? []).map((v) => ({
    key: String(v.key ?? ''),
    label: typeof v.label === 'string' ? v.label : null,
  }));

/** Comparación de las variantes de una corrida, por caso (app/agent_tests/runner.py). */
export function CompareModal({
  agentId,
  runId,
  opened,
  onClose,
}: {
  agentId: string;
  runId: string | null;
  opened: boolean;
  onClose: () => void;
}) {
  const run = useTestRun(agentId, runId);
  const [openCase, setOpenCase] = useState<string | null>(null);
  const results = caseResults(run.data);
  const columns = runVariants(run.data?.variants);
  // La corrida pidió borrador (viene en `variants`) aunque no haya llegado a correrlo.
  const requestedDraft = columns.some((v) => v.key === 'borrador');
  const hasDraft = results.some((item) => variant(item, 'borrador'));
  const anyFallback = results.some((item) => item.variants.some((v) => fallbackCount(v) > 0));

  return (
    <Modal opened={opened} onClose={onClose} size="xl" title="Comparación de pruebas">
      <Stack gap="md">
        {run.isError && <Alert color="red">No se pudo leer la corrida.</Alert>}
        {run.data && (
          <>
            <RunStatus agentId={agentId} run={run.data} />
            {anyFallback && (
              <Alert color="orange">
                Parte de la comparación la contestó el respaldo local, no el modelo configurado.
              </Alert>
            )}
            {run.data.status === 'done' && requestedDraft && !hasDraft && (
              <Alert color="gray">Los cambios son iguales a la versión publicada: no hay nada que comparar.</Alert>
            )}
            {isFinished(run.data.status) && columns.length > 0 && (
              <Card withBorder>
                <Table.ScrollContainer minWidth={480}>
                  <Table>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Caso</Table.Th>
                        {columns.map((d) => (
                          <Table.Th key={d.key}>{variantLabel(d.key, d.label)}</Table.Th>
                        ))}
                        <Table.Th />
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {results.map((item) => {
                        const published = variant(item, 'publicada');
                        return (
                          <Table.Tr key={item.case_id}>
                            <Table.Td>
                              <Text size="sm">{item.name}</Text>
                              {item.known_failure && <Badge color="gray">Falla conocida</Badge>}
                            </Table.Td>
                            {columns.map((d) => {
                              const v = variant(item, d.key);
                              const worse = d.key !== 'publicada' && !!v && !!published && v.passed < published.passed;
                              return (
                                <Table.Td key={d.key}>
                                  <Text size="sm" c={worse ? 'red.7' : undefined} fw={worse ? 700 : undefined}>
                                    {cell(v)}
                                    {worse ? ' ⚠ empeora' : ''}
                                  </Text>
                                </Table.Td>
                              );
                            })}
                            <Table.Td>
                              <Button size="compact-xs" variant="subtle" onClick={() => setOpenCase(item.case_id)}>
                                Ver respuestas
                              </Button>
                            </Table.Td>
                          </Table.Tr>
                        );
                      })}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              </Card>
            )}
            {openCase && (
              <Card withBorder>
                <Group justify="space-between" mb="xs">
                  <Text fw={600}>{results.find((r) => r.case_id === openCase)?.name}</Text>
                  <Button size="compact-xs" variant="subtle" onClick={() => setOpenCase(null)}>
                    Cerrar
                  </Button>
                </Group>
                <RunResults results={results.filter((item) => item.case_id === openCase)} />
              </Card>
            )}
          </>
        )}
      </Stack>
    </Modal>
  );
}
