import { Alert, Badge, Button, Group, Progress, Stack, Text } from '@mantine/core';
import { confirmAction } from '@/components/confirm';
import { notifyError } from '@/lib/notify';
import { isActive, useCancelRun, type TestRun } from './api';

const STATES: Record<string, { label: string; color: string }> = {
  queued: { label: 'En cola', color: 'gray' },
  running: { label: 'Corriendo', color: 'blue' },
  done: { label: 'Terminada', color: 'green' },
  cancelled: { label: 'Cancelada', color: 'gray' },
  failed: { label: 'Falló', color: 'red' },
};

/** El estado en castellano; con el pedido de cancelación de una que corre, «Cancelando…». */
function runStatusLabel(run: TestRun): { label: string; color: string } {
  if (run.status === 'running' && run.cancel_requested_at) return { label: 'Cancelando…', color: 'yellow' };
  return STATES[run.status] ?? { label: run.status, color: 'gray' };
}

/** Estado de una corrida: badge, progreso mientras corre y «Cancelar» con confirmación (CASOS_DE_PRUEBA.md). */
export function RunStatus({ agentId, run }: { agentId: string; run: TestRun }) {
  const cancel = useCancelRun(agentId);
  const { label, color } = runStatusLabel(run);
  const active = isActive(run.status);

  const cancelRun = async () => {
    const ok = await confirmAction({
      title: '¿Cancelar la corrida?',
      message: 'Se guarda lo que ya corrió. Los turnos que están en el LLM terminan (hasta 90 s).',
      confirmLabel: 'Cancelar la corrida',
      cancelLabel: 'Seguir',
      danger: true,
    });
    if (ok) cancel.mutate(run.id, { onError: (e) => notifyError(e, 'No se pudo cancelar') });
  };

  return (
    <Stack gap="xs">
      <Group gap="xs" wrap="wrap">
        <Badge color={color}>{label}</Badge>
        {active && (
          <Text size="xs" c="dimmed">
            {run.done}/{run.total} repeticiones
          </Text>
        )}
        {active && !run.cancel_requested_at && (
          <Button
            size="compact-xs"
            variant="subtle"
            color="red"
            onClick={() => void cancelRun()}
            loading={cancel.isPending}
          >
            Cancelar
          </Button>
        )}
      </Group>
      {active && <Progress value={run.total ? (run.done / run.total) * 100 : 0} />}
      {run.status === 'failed' && run.error && <Alert color="red">{run.error}</Alert>}
    </Stack>
  );
}
