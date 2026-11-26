import { Alert, Badge, Button, Card, Group, Modal, Stack, Table, Text } from '@mantine/core';
import { useState } from 'react';
import { caseResults, isFinished, useTestRun, type CaseResult, type VariantResult } from './api';
import { RunResults } from './RunResults';
import { RunStatus } from './RunStatus';

const variant = (item: CaseResult, key: string): VariantResult | undefined =>
  item.variants.find((v) => v.key === key);

/** Comparacion publicada vs cambios sin guardar, por caso (app/agent_tests/runner.py). */
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
  const hasDraft = results.some((item) => variant(item, 'borrador'));

  return (
    <Modal opened={opened} onClose={onClose} size="xl" title="Comparación de pruebas">
      <Stack gap="md">
        {run.isError && <Alert color="red">No se pudo leer la corrida.</Alert>}
        {run.data && (
          <>
            <RunStatus agentId={agentId} run={run.data} />
            {run.data.status === 'done' && !hasDraft && (
              <Alert color="gray">Los cambios son iguales a la versión publicada: no hay nada que comparar.</Alert>
            )}
            {isFinished(run.data.status) && hasDraft && (
              <Card withBorder>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Caso</Table.Th>
                      <Table.Th>Publicada</Table.Th>
                      <Table.Th>Cambios</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {results.map((item) => {
                      const published = variant(item, 'publicada');
                      const draft = variant(item, 'borrador');
                      const worse = !!draft && !!published && draft.passed < published.passed;
                      return (
                        <Table.Tr key={item.case_id}>
                          <Table.Td>
                            <Text size="sm">{item.name}</Text>
                            {item.known_failure && <Badge color="gray">Falla conocida</Badge>}
                          </Table.Td>
                          <Table.Td>{published ? `pasa ${published.passed}/${published.total}` : '–'}</Table.Td>
                          <Table.Td>
                            <Text size="sm" c={worse ? 'red.7' : undefined} fw={worse ? 700 : undefined}>
                              {draft ? `pasa ${draft.passed}/${draft.total}` : '–'}
                              {worse ? ' ⚠ empeora' : ''}
                            </Text>
                          </Table.Td>
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
