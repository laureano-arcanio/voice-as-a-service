import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core';
import { useQueryClient } from '@tanstack/react-query';
import { IconFlask, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { AgentDetail } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { JsonEditor } from '@/components/JsonEditor';
import { ChatView } from '@/features/calls/ChatView';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifyInfo, notifySuccess } from '@/lib/notify';
import {
  caseResults,
  describeCheck,
  isFinished,
  isRunInProgress,
  summaryText,
  testKeys,
  useCreateRun,
  useDeleteCase,
  useTestCase,
  useTestRun,
  useUpdateCase,
  type Check,
  type TestCaseDetail,
  type ToolResult,
} from './api';
import { ChecksEditor } from './ChecksEditor';
import { RunResults } from './RunResults';
import { RunStatus } from './RunStatus';

function PassSummary({ variants }: { variants?: Record<string, unknown>[] }) {
  if (!variants?.length) return <Text size="xs" c="dimmed">Sin corridas</Text>;
  return (
    <Group gap={6}>
      {variants.map((v) => {
        const passed = Number(v.passed ?? 0);
        const total = Number(v.total ?? 0);
        return (
          <Badge key={String(v.key)} size="sm" color={total === 0 ? 'gray' : passed === total ? 'green' : passed === 0 ? 'red' : 'yellow'}>
            {String(v.key)}: pasa {passed}/{total}
          </Badge>
        );
      })}
    </Group>
  );
}

function CaseBody({
  agent,
  caseId,
  data,
  onClose,
  onDeleted,
}: {
  agent: AgentDetail;
  caseId: string;
  data: TestCaseDetail;
  onClose: () => void;
  onDeleted?: () => void;
}) {
  const update = useUpdateCase(agent.id, caseId);
  const remove = useDeleteCase(agent.id);
  const createRun = useCreateRun(agent.id);
  const qc = useQueryClient();
  const [runId, setRunId] = useState<string | null>(null);
  const run = useTestRun(agent.id, runId);
  const [checks, setChecks] = useState<Check[]>(() => (data.checks ?? []) as Check[]);
  const [knownFailure, setKnownFailure] = useState(data.known_failure);
  const [editJson, setEditJson] = useState(false);
  const [jsonText, setJsonText] = useState(() => JSON.stringify(data.tool_results ?? [], null, 2));

  const tools = ((agent.definition.tools ?? []) as { tool?: string }[]).map((t) => t.tool).filter(Boolean) as string[];
  const snapshot = data.snapshot as
    | { messages?: { role: 'assistant' | 'user'; text: string }[]; user_message?: string }
    | null
    | undefined;
  const messages = snapshot
    ? [...(snapshot.messages ?? []), { role: 'user' as const, text: snapshot.user_message ?? '' }]
    : [];

  const save = (body: Parameters<typeof update.mutate>[0]) =>
    update.mutate(body, {
      onSuccess: () => notifySuccess('Caso actualizado.'),
      onError: (e) => notifyError(e, 'No se pudo guardar'),
    });

  const saveJson = () => {
    try {
      const parsed = JSON.parse(jsonText) as ToolResult[];
      save({ tool_results: parsed });
      setEditJson(false);
    } catch {
      notifyError(new Error('El JSON no parsea'), 'No se pudo guardar');
    }
  };

  const runCase = () =>
    createRun.mutate(
      { repetitions: 5, case_ids: [caseId] },
      {
        onSuccess: (r) => setRunId(r.id),
        onError: (e) => {
          if (!isRunInProgress(e)) return notifyError(e, 'No se pudo correr');
          // La corrida activa se ve en la pestaña Pruebas: se refresca y se cierra el detalle.
          void qc.invalidateQueries({ queryKey: testKeys.runs(agent.id) });
          notifyInfo('Ya hay una corrida en curso: seguí su avance en la pestaña Pruebas.');
          onClose();
        },
      },
    );

  const del = async () => {
    const ok = await confirmAction({
      title: '¿Borrar el caso de prueba?',
      message: 'Se borra el caso y su historial de corridas. Las conversaciones no se tocan.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      remove.mutate(caseId, {
        onSuccess: () => {
          notifySuccess('Caso borrado.');
          onDeleted?.();
          onClose();
        },
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  return (
    <Stack gap="md">
      <Group gap="xs" wrap="wrap">
        {data.known_failure && <Badge color="gray">Falla conocida</Badge>}
        <Badge color="gray">{data.channel === 'voice' ? 'Voz' : 'WhatsApp'}</Badge>
        {data.source_conversation_id && (
          <Anchor component={Link} to={`/calls/${data.source_conversation_id}`} size="xs">
            Ver la llamada de origen
          </Anchor>
        )}
        <Text size="xs" c="dimmed">
          Creado {formatDateTime(data.created_at)}
        </Text>
      </Group>

      <Card withBorder>
        <Title order={6} mb="xs">
          Conversación grabada
        </Title>
        <ChatView messages={messages} maxHeight={260} />
      </Card>

      <Card withBorder>
        <Group justify="space-between" mb="xs">
          <Title order={6}>¿Qué tenía que pasar?</Title>
          <Button
            size="xs"
            onClick={() => save({ checks, known_failure: knownFailure })}
            loading={update.isPending}
          >
            Guardar chequeos
          </Button>
        </Group>
        <ChecksEditor value={checks} onChange={setChecks} tools={tools} />
        <Switch
          mt="sm"
          label="Falla conocida (se muestra aparte y no se espera que pase)"
          checked={knownFailure}
          onChange={(e) => setKnownFailure(e.currentTarget.checked)}
        />
        {checks.length > 0 && (
          <Stack gap={2} mt="sm">
            {checks.map((c, i) => (
              <Text key={i} size="xs" c="dimmed">
                · {describeCheck(c)}
              </Text>
            ))}
          </Stack>
        )}
      </Card>

      <Card withBorder>
        <Group justify="space-between" mb="xs">
          <Title order={6}>Resultado grabado de la herramienta</Title>
          {editJson ? (
            <Group gap="xs">
              <Button size="xs" variant="default" onClick={() => setEditJson(false)}>
                Cancelar
              </Button>
              <Button size="xs" onClick={saveJson}>
                Guardar JSON
              </Button>
            </Group>
          ) : (
            <Button size="xs" variant="subtle" onClick={() => setEditJson(true)}>
              Editar JSON
            </Button>
          )}
        </Group>
        {editJson ? (
          <JsonEditor value={jsonText} onChange={setJsonText} height="220px" />
        ) : (
          <pre className="code" style={{ maxHeight: 220, overflow: 'auto' }}>
            {JSON.stringify(data.tool_results ?? [], null, 2)}
          </pre>
        )}
      </Card>

      <Group justify="space-between">
        <Group>
          <Button leftSection={<IconFlask size={16} />} onClick={runCase} loading={createRun.isPending}>
            Correr este caso (5×)
          </Button>
          <Button variant="subtle" color="red" leftSection={<IconTrash size={16} />} onClick={() => void del()}>
            Borrar
          </Button>
        </Group>
        <PassSummary variants={data.last_run?.variants as Record<string, unknown>[] | undefined} />
      </Group>

      {runId && run.data && (
        <Card withBorder>
          <Text fw={600} mb="xs">
            Resultado
          </Text>
          <Stack gap="sm">
            <RunStatus agentId={agent.id} run={run.data} />
            {isFinished(run.data.status) && caseResults(run.data).length > 0 && (
              <RunResults results={caseResults(run.data)} />
            )}
          </Stack>
        </Card>
      )}

      <Card withBorder>
        <Title order={6} mb="xs">
          Historial
        </Title>
        {(data.history ?? []).length === 0 && (
          <Text size="sm" c="dimmed">
            Todavía no se corrió.
          </Text>
        )}
        <Stack gap={4}>
          {(data.history ?? []).map((h) => (
            <Group key={h.run_id} justify="space-between">
              <Text size="sm">{formatDateTime(h.created_at)}</Text>
              <Group gap="xs">
                <Text size="xs" c="dimmed">
                  {summaryText(h)}
                </Text>
                <Button size="compact-xs" variant="subtle" onClick={() => setRunId(h.run_id)}>
                  Ver respuestas
                </Button>
              </Group>
            </Group>
          ))}
        </Stack>
      </Card>
    </Stack>
  );
}

/** Detalle de un caso: conversación, chequeos editables, lo grabado, historial y respuestas. */
export function CaseDetail({
  agent,
  caseId,
  opened,
  onClose,
  onDeleted,
}: {
  agent: AgentDetail;
  caseId: string | null;
  opened: boolean;
  onClose: () => void;
  onDeleted?: () => void;
}) {
  const detail = useTestCase(agent.id, caseId);
  const data = detail.data;
  return (
    <Modal opened={opened} onClose={onClose} size="xl" title={data?.name ?? 'Caso de prueba'}>
      {detail.isError && <Alert color="red">No se pudo leer el caso.</Alert>}
      {data && caseId && (
        <CaseBody
          key={`${data.id}:${data.updated_at}`}
          agent={agent}
          caseId={caseId}
          data={data}
          onClose={onClose}
          onDeleted={onDeleted}
        />
      )}
    </Modal>
  );
}
