import { Alert, Badge, Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { useQueryClient } from '@tanstack/react-query';
import { IconFlag, IconFlask } from '@tabler/icons-react';
import { useState } from 'react';
import type { AgentDetail } from '@/api/types';
import { errorMessage } from '@/api/errors';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifyInfo } from '@/lib/notify';
import {
  caseResults,
  isFinished,
  isRunInProgress,
  summaryText,
  testKeys,
  useCreateRun,
  useLatestRun,
  useTestCases,
  useTestRun,
  type TestCaseSummary,
} from './api';
import { CaseDetail } from './CaseDetail';
import { RunResults } from './RunResults';
import { RunStatus } from './RunStatus';

function passColor(c: TestCaseSummary) {
  const variants = c.last_run?.variants ?? [];
  if (!variants.length) return 'gray';
  const passed = variants.reduce((a, v) => a + Number(v.passed ?? 0), 0);
  const total = variants.reduce((a, v) => a + Number(v.total ?? 0), 0);
  if (total === 0) return 'gray';
  return passed === total ? 'green' : passed === 0 ? 'red' : 'yellow';
}

/** La pestaña Pruebas del agente: casos guardados, "Correr todos" y el detalle (docs/features/CASOS_DE_PRUEBA.md). */
export function TestsTab({ agent }: { agent: AgentDetail }) {
  const cases = useTestCases(agent.id);
  const createRun = useCreateRun(agent.id);
  const latest = useLatestRun(agent.id);
  const run = useTestRun(agent.id, latest.data?.id ?? null);
  const qc = useQueryClient();
  const [openCase, setOpenCase] = useState<string | null>(null);

  const runAll = (repetitions: number) =>
    createRun.mutate(
      { repetitions },
      {
        onError: (e) => {
          if (!isRunInProgress(e)) return notifyError(e, 'No se pudo correr');
          // La corrida activa se ve abajo: se refresca la última.
          void qc.invalidateQueries({ queryKey: testKeys.runs(agent.id) });
          notifyInfo('Ya hay una corrida en curso: seguí su avance en «Última corrida».');
        },
      },
    );

  if ((agent.definition as { external?: unknown }).external)
    return (
      <Alert color="blue">
        Los casos de prueba no aplican a tu propio agente: el prompt y las herramientas son de tu endpoint.
      </Alert>
    );

  const list = cases.data ?? [];
  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="wrap">
        <div>
          <Title order={4}>Pruebas</Title>
          <Text size="xs" c="dimmed">
            Conversaciones grabadas con chequeos: se corren contra la versión guardada o contra los cambios sin
            guardar. Informan, no bloquean, y nunca ejecutan una herramienta real.
          </Text>
        </div>
        {list.length > 0 && (
          <Group gap="xs">
            <Button variant="default" leftSection={<IconFlask size={16} />} onClick={() => runAll(5)} loading={createRun.isPending}>
              Correr todos 5×
            </Button>
            <Button variant="default" onClick={() => runAll(10)} loading={createRun.isPending}>
              10×
            </Button>
          </Group>
        )}
      </Group>

      {cases.isError && <Alert color="red">{errorMessage(cases.error)}</Alert>}
      {list.length === 0 && !cases.isPending && (
        <Card withBorder>
          <Text size="sm">
            Todavía no hay casos. Se crean desde una llamada (el botón «Crear caso de prueba» en cada respuesta del
            agente) o desde la pestaña <b>Probar</b>, en la respuesta que querés fijar.
          </Text>
        </Card>
      )}

      <Stack gap="xs">
        {list.map((c) => (
          <Card key={c.id} withBorder>
            <Group justify="space-between" wrap="wrap">
              <Group gap="xs">
                <Text fw={600}>{c.name}</Text>
                <Badge color={passColor(c)}>{summaryText(c.last_run) || 'sin corridas'}</Badge>
                {c.known_failure && (
                  <Badge color="gray" leftSection={<IconFlag size={10} />}>
                    Falla conocida
                  </Badge>
                )}
              </Group>
              <Group gap="xs">
                <Text size="xs" c="dimmed">
                  {c.last_run ? formatDateTime(c.last_run.created_at) : `Creado ${formatDateTime(c.created_at)}`}
                </Text>
                <Button size="xs" variant="default" onClick={() => setOpenCase(c.id)}>
                  Ver
                </Button>
              </Group>
            </Group>
          </Card>
        ))}
      </Stack>

      {run.data && (
        <Card withBorder>
          <Group justify="space-between" mb="xs">
            <Text fw={600}>Última corrida</Text>
            <Text size="xs" c="dimmed">
              {formatDateTime(run.data.created_at)}
            </Text>
          </Group>
          <Stack gap="sm">
            <RunStatus agentId={agent.id} run={run.data} />
            {isFinished(run.data.status) && caseResults(run.data).length > 0 && (
              <RunResults results={caseResults(run.data)} />
            )}
          </Stack>
        </Card>
      )}

      <CaseDetail
        agent={agent}
        caseId={openCase}
        opened={!!openCase}
        onClose={() => setOpenCase(null)}
        onDeleted={() => void cases.refetch()}
      />
    </Stack>
  );
}
