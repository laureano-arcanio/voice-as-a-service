import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Progress,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconCheck, IconFlask } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { errorMessage } from '@/api/errors';
import { ChatView } from '@/features/calls/ChatView';
import { useAgent } from '@/features/agents/api';
import { useAreas } from '@/features/team/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { buildCaseBody, addNoDice } from './caseBody';
import { ChecksEditor } from './ChecksEditor';
import { RunResults } from './RunResults';
import {
  caseResults,
  useCreateCase,
  useCreateRun,
  usePreviewCase,
  useTestRun,
  type Check,
  type Preview,
  type TestCaseDetail,
} from './api';

const DEFAULT_REPETITIONS = 5;

function agentOptions(definition: Record<string, unknown> | undefined, areas: string[]) {
  const tools = Array.isArray(definition?.tools)
    ? (definition.tools as { tool?: string }[]).map((t) => t.tool).filter((t): t is string => !!t)
    : [];
  return { tools, areas };
}

function CaseForm({
  agentId,
  conversationId,
  messageIndex,
  preview,
  tools,
  areas,
  onClose,
  onCreated,
}: {
  agentId: string;
  conversationId: string;
  messageIndex: number;
  preview: Preview;
  tools: string[];
  areas: string[];
  onClose: () => void;
  onCreated?: (created: TestCaseDetail) => void;
}) {
  const create = useCreateCase(agentId);
  const createRun = useCreateRun(agentId);
  const [name, setName] = useState(() => `Caso: ${preview.snapshot.user_message ?? ''}`.slice(0, 120));
  const [checks, setChecks] = useState<Check[]>(() => preview.checks ?? []);
  const [selection, setSelection] = useState('');
  const [runId, setRunId] = useState<string | null>(null);
  const run = useTestRun(agentId, runId);

  const body = () =>
    buildCaseBody(preview, {
      conversationId,
      messageIndex,
      name: name.trim() || 'Caso de prueba',
      checks,
    });

  const tryNow = () =>
    createRun.mutate(
      { repetitions: DEFAULT_REPETITIONS, draft_case: body() },
      {
        onSuccess: (r) => setRunId(r.id),
        onError: (e) => notifyError(e, 'No se pudo correr'),
      },
    );

  const save = () =>
    create.mutate(body(), {
      onSuccess: (created) => {
        notifySuccess('Caso de prueba guardado.');
        onCreated?.(created);
        onClose();
      },
      onError: (e) => notifyError(e, 'No se pudo guardar'),
    });

  const grabSelection = () => {
    const text = globalThis.getSelection?.()?.toString() ?? '';
    if (text.trim()) setSelection(text);
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={5} mb={4}>
          La conversación hasta el turno
        </Title>
        <ChatView
          messages={preview.snapshot.messages.concat([
            { role: 'user', text: preview.snapshot.user_message } as never,
          ])}
          maxHeight={260}
        />
      </div>
      <Card withBorder>
        <Group justify="space-between" mb={4}>
          <Text fw={600}>Lo que respondió el agente</Text>
          {preview.reply.handoff && <Badge color="blue">Derivó a {preview.reply.handoff}</Badge>}
        </Group>
        <Text size="sm" onMouseUp={grabSelection} style={{ whiteSpace: 'pre-wrap' }}>
          {preview.reply.text || '(sin texto)'}
        </Text>
        {selection && (
          <Button
            mt="xs"
            size="xs"
            variant="light"
            onClick={() => {
              setChecks((prev) => addNoDice(prev, selection));
              setSelection('');
            }}
          >
            No tiene que decir esto
          </Button>
        )}
        {preview.reply.tool_calls.length > 0 && (
          <Stack gap={2} mt="sm">
            {preview.reply.tool_calls.map((call, i) => (
              <Text key={i} size="xs" c="dimmed" className="mono">
                {call.name}: {preview.reply.tool_results[i]}
              </Text>
            ))}
          </Stack>
        )}
      </Card>
      <div>
        <Title order={5} mb={4}>
          ¿Qué tenía que pasar?
        </Title>
        <ChecksEditor value={checks} onChange={setChecks} tools={tools} areas={areas} />
      </div>
      <TextInput label="Nombre" value={name} onChange={(e) => setName(e.currentTarget.value)} maxLength={200} />
      {runId && run.data && (
        <Card withBorder>
          <Group justify="space-between" mb="xs">
            <Text fw={600}>Corrida de prueba ({DEFAULT_REPETITIONS}×)</Text>
            <Badge color={run.data.status === 'done' ? 'green' : 'blue'}>{run.data.status}</Badge>
          </Group>
          {(run.data.status === 'queued' || run.data.status === 'running') && (
            <Progress value={run.data.total ? (run.data.done / run.data.total) * 100 : 0} />
          )}
          {run.data.status === 'failed' && <Alert color="red">{run.data.error}</Alert>}
          {run.data.status === 'done' && <RunResults results={caseResults(run.data)} />}
        </Card>
      )}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          variant="light"
          leftSection={<IconFlask size={16} />}
          onClick={tryNow}
          loading={createRun.isPending}
          disabled={!!runId && run.data?.status !== 'done' && run.data?.status !== 'failed'}
        >
          Probar ahora ({DEFAULT_REPETITIONS}×)
        </Button>
        <Button leftSection={<IconCheck size={16} />} onClick={save} loading={create.isPending}>
          Guardar
        </Button>
      </Group>
    </Stack>
  );
}

/** Crear un caso de prueba desde un turno de una conversación (docs/features/CASOS_DE_PRUEBA.md). */
export function CreateCaseModal({
  agentId,
  clientId,
  conversationId,
  messageIndex,
  opened,
  onClose,
  onCreated,
}: {
  agentId: string;
  clientId?: string | null;
  conversationId: string;
  messageIndex: number;
  opened: boolean;
  onClose: () => void;
  onCreated?: (created: TestCaseDetail) => void;
}) {
  const preview = usePreviewCase(agentId);
  const agent = useAgent(agentId);
  const areas = useAreas(clientId ?? undefined);

  useEffect(() => {
    if (!opened) return;
    preview.mutate({ conversation_id: conversationId, message_index: messageIndex });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened, conversationId, messageIndex]);

  const close = () => {
    preview.reset();
    onClose();
  };
  const options = agentOptions(
    agent.data?.definition as Record<string, unknown> | undefined,
    (areas.data ?? []).map((a) => a.name),
  );

  return (
    <Modal opened={opened} onClose={close} size="xl" title="Crear caso de prueba">
      <Stack gap="md">
        {preview.isError && (
          <Alert color="red" title="No se pudo leer la conversación">
            {errorMessage(preview.error)}
          </Alert>
        )}
        {preview.isPending && <Text size="sm">Leyendo el turno…</Text>}
        {preview.data && (
          <CaseForm
            key={`${conversationId}:${messageIndex}`}
            agentId={agentId}
            conversationId={conversationId}
            messageIndex={messageIndex}
            preview={preview.data}
            tools={options.tools}
            areas={options.areas}
            onClose={close}
            onCreated={onCreated}
          />
        )}
      </Stack>
    </Modal>
  );
}
