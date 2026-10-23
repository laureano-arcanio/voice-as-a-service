import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  PasswordInput,
  Radio,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconPlus, IconShieldLock } from '@tabler/icons-react';
import { useState } from 'react';
import type { LlmConnection, LlmConnectionKind } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { Dash } from '@/components/Badges';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  useCreateLlmConnection,
  useDeleteLlmConnection,
  useLlmConnections,
  useTestLlmConnection,
  useUpdateLlmConnection,
} from './api';
import { JSON_MODE_LABEL, KIND_HELP, KIND_LABEL, LOCAL_LABEL } from './labels';

const KINDS: LlmConnectionKind[] = ['anthropic', 'openrouter', 'openai_compatible'];
const MODEL_EXAMPLE: Record<LlmConnectionKind, string> = {
  anthropic: 'claude-haiku-5-5',
  openrouter: 'openai/gpt-4.1-mini',
  openai_compatible: 'gpt-4.1-mini',
};

function TestBadge({ c }: { c: LlmConnection }) {
  if (c.last_test_ok === null || c.last_test_ok === undefined) return <Badge color="gray">Sin probar</Badge>;
  return c.last_test_ok ? (
    <Badge color="green">Funciona</Badge>
  ) : (
    <Badge color="red">Falló la prueba</Badge>
  );
}

/** Alta y edicion de una conexion. La clave se manda una vez y no se vuelve a ver. */
function ConnectionModal({
  clientId,
  connection,
  onClose,
}: {
  clientId: string;
  connection: LlmConnection | null;
  onClose: () => void;
}) {
  const editing = connection !== null;
  const create = useCreateLlmConnection(clientId);
  const update = useUpdateLlmConnection(clientId);
  const test = useTestLlmConnection(clientId);
  const [kind, setKind] = useState<LlmConnectionKind>(connection?.kind ?? 'anthropic');
  const [name, setName] = useState(connection?.name ?? '');
  const [baseUrl, setBaseUrl] = useState(connection?.kind === 'openai_compatible' ? connection.base_url : '');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState(connection?.default_model ?? '');

  const needsUrl = kind === 'openai_compatible';
  const valid = name.trim() && (editing || apiKey.trim()) && (!needsUrl || baseUrl.trim());
  const busy = create.isPending || update.isPending || test.isPending;

  /** Despues de guardar, una prueba real: dice enseguida si la clave y el modelo andan. */
  const verify = (id: string) =>
    test.mutate(
      { id, model: model.trim() || undefined },
      {
        onSuccess: (c) => {
          if (c.last_test_ok) notifySuccess(`Conexión guardada y probada (${c.last_test_detail}).`);
          else notifyError(c.last_test_detail, 'Se guardó, pero la prueba falló');
          onClose();
        },
        onError: (e) => {
          notifyError(e, 'Se guardó, pero no se pudo probar');
          onClose();
        },
      },
    );

  const submit = () => {
    if (!valid) return;
    if (editing) {
      update.mutate(
        {
          id: connection.id,
          body: {
            name: name.trim(),
            default_model: model.trim(),
            ...(needsUrl ? { base_url: baseUrl.trim() } : {}),
            ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
          },
        },
        {
          onSuccess: (c) => (apiKey.trim() ? verify(c.id) : (notifySuccess('Conexión guardada.'), onClose())),
          onError: (e) => notifyError(e, 'No se pudo guardar la conexión'),
        },
      );
    } else {
      create.mutate(
        {
          name: name.trim(),
          kind,
          api_key: apiKey.trim(),
          default_model: model.trim(),
          ...(needsUrl ? { base_url: baseUrl.trim() } : {}),
        },
        {
          onSuccess: (c) => verify(c.id),
          onError: (e) => notifyError(e, 'No se pudo crear la conexión'),
        },
      );
    }
  };

  return (
    <Modal opened onClose={onClose} title={editing ? 'Editar conexión' : 'Nueva conexión'} size="lg">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Stack>
          {editing ? (
            <Group gap="xs">
              <Text size="sm" c="dimmed">
                Proveedor
              </Text>
              <Badge color="gray">{KIND_LABEL[connection.kind]}</Badge>
            </Group>
          ) : (
            <Radio.Group label="Proveedor" value={kind} onChange={(v) => setKind(v as LlmConnectionKind)}>
              <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xs" mt="xs">
                {KINDS.map((k) => (
                  <Radio.Card key={k} value={k} p="sm">
                    <Group wrap="nowrap" align="flex-start" gap="sm">
                      <Radio.Indicator />
                      <Stack gap={2} style={{ minWidth: 0 }}>
                        <Text size="sm" fw={600}>
                          {KIND_LABEL[k]}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {KIND_HELP[k]}
                        </Text>
                      </Stack>
                    </Group>
                  </Radio.Card>
                ))}
              </SimpleGrid>
            </Radio.Group>
          )}
          <TextInput
            label="Nombre"
            description="Para reconocerla al elegirla en un agente."
            placeholder="Mi cuenta de Anthropic"
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            maxLength={64}
            required
            data-autofocus
          />
          {needsUrl && (
            <TextInput
              label="URL base"
              description="La de la API de chat completions, con /v1."
              placeholder="https://api.openai.com/v1"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.currentTarget.value)}
              required
            />
          )}
          <PasswordInput
            label="API key"
            description={
              editing
                ? `Dejala vacía para conservar la actual (…${connection.last4}).`
                : 'Se guarda cifrada y no se vuelve a mostrar.'
            }
            placeholder={editing ? '••••••••' : 'sk-…'}
            value={apiKey}
            onChange={(e) => setApiKey(e.currentTarget.value)}
            autoComplete="off"
            required={!editing}
          />
          <TextInput
            label="Modelo por defecto"
            description="El que se propone al elegir esta conexión en un agente. Se puede cambiar en cada uno."
            placeholder={MODEL_EXAMPLE[kind]}
            value={model}
            onChange={(e) => setModel(e.currentTarget.value)}
            maxLength={128}
          />
          <Alert color="yellow" icon={<IconShieldLock size={18} />} title="Las conversaciones salen del servidor">
            Los agentes que usen esta conexión mandan sus conversaciones a {KIND_LABEL[kind]}. Los tokens los
            cobra tu proveedor, no Atentina. Si falla, el agente sigue con el modelo {LOCAL_LABEL}.
          </Alert>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={busy} disabled={!valid}>
              {editing ? 'Guardar cambios' : 'Guardar y probar'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

/** Conexiones de LLM de un cliente (BYOK): las gestiona el cliente o un admin. */
export function LlmConnectionsSection({ clientId }: { clientId: string }) {
  const list = useLlmConnections(clientId);
  const test = useTestLlmConnection(clientId);
  const remove = useDeleteLlmConnection(clientId);
  const [modal, setModal] = useState<{ connection: LlmConnection | null } | null>(null);
  const [testing, setTesting] = useState<string | null>(null);

  const runTest = (c: LlmConnection) => {
    setTesting(c.id);
    test.mutate(
      { id: c.id },
      {
        onSuccess: (r) =>
          r.last_test_ok
            ? notifySuccess(`${r.name}: funciona (${r.last_test_detail}).`)
            : notifyError(r.last_test_detail, `${r.name}: falló la prueba`),
        onError: (e) => notifyError(e, 'No se pudo probar la conexión'),
        onSettled: () => setTesting(null),
      },
    );
  };

  const doRemove = async (c: LlmConnection) => {
    const used = c.used_by ?? 0;
    const message =
      used > 0
        ? `¿Dar de baja "${c.name}"? ${used === 1 ? 'Un agente la usa' : `${used} agentes la usan`} y pasa${used === 1 ? '' : 'n'} a contestar con el modelo ${LOCAL_LABEL}.`
        : `¿Dar de baja "${c.name}"? La clave guardada se descarta.`;
    if (await confirmAction({ title: 'Dar de baja conexión', message, confirmLabel: 'Dar de baja', danger: true })) {
      remove.mutate(c.id, {
        onSuccess: () => notifySuccess('Conexión dada de baja.'),
        onError: (e) => notifyError(e),
      });
    }
  };

  return (
    <Card>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Conexiones de modelos</Title>
        <Button size="xs" leftSection={<IconPlus size={16} />} onClick={() => setModal({ connection: null })}>
          Nueva conexión
        </Button>
      </Group>
      <Text size="xs" c="dimmed" mb="sm">
        Traé la clave de tu proveedor (Anthropic, OpenRouter o uno compatible con OpenAI) y elegí en cada
        agente desde qué turno lo usa. El modelo {LOCAL_LABEL} siempre está disponible y es el respaldo.
      </Text>
      <QueryState query={list}>
        {(connections) =>
          connections.length === 0 ? (
            <EmptyState>
              Sin conexiones: los agentes usan el modelo {LOCAL_LABEL}. Cargá una para usar tu propio modelo.
            </EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={760}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Proveedor</Table.Th>
                    <Table.Th>Clave</Table.Th>
                    <Table.Th>Modelo</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th ta="right">Agentes</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {connections.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td>
                        <Text size="sm" fw={600}>
                          {c.name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          Cargada {formatDateTime(c.created_at)}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge color="gray">{KIND_LABEL[c.kind]}</Badge>
                      </Table.Td>
                      <Table.Td className="mono">…{c.last4}</Table.Td>
                      <Table.Td className="mono">{c.default_model || <Dash />}</Table.Td>
                      <Table.Td>
                        <TestBadge c={c} />
                        {c.last_test_detail && (
                          <Text size="xs" c="dimmed">
                            {c.last_test_detail}
                            {c.last_test_ok ? ` · ${JSON_MODE_LABEL[c.json_mode]}` : ''}
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td ta="right" className="mono">
                        {c.used_by ?? 0}
                      </Table.Td>
                      <Table.Td ta="right" style={{ whiteSpace: 'nowrap' }}>
                        <Button
                          size="compact-sm"
                          variant="subtle"
                          loading={testing === c.id}
                          onClick={() => runTest(c)}
                        >
                          Probar
                        </Button>
                        <Button size="compact-sm" variant="subtle" onClick={() => setModal({ connection: c })}>
                          Editar
                        </Button>
                        <Button
                          size="compact-sm"
                          variant="subtle"
                          color="red"
                          onClick={() => void doRemove(c)}
                        >
                          Dar de baja
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      {modal && (
        <ConnectionModal
          key={modal.connection?.id ?? 'new'}
          clientId={clientId}
          connection={modal.connection}
          onClose={() => setModal(null)}
        />
      )}
    </Card>
  );
}
