import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Code,
  Group,
  Modal,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconAlertTriangle, IconKey, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import type { ApiKey, ApiKeyCreated, ApiScope } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { CopyIcon } from '@/components/Copy';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from './api';
import { EXAMPLE_LABELS, inferenceExample, type ExampleKind } from '@/features/developers/examples';
import { curlExample } from './curl';

/** Para que sirve cada alcance de una key. `calls`: la API de llamadas; el resto, la de inferencia. */
const SCOPE_OPTIONS: { value: ApiScope; label: string; description: string }[] = [
  {
    value: 'calls',
    label: 'Llamadas y agentes',
    description: 'Lanzar llamadas, ver conversaciones y reportes.',
  },
  { value: 'llm', label: 'LLM', description: 'Chat con nuestro modelo de lenguaje.' },
  { value: 'stt', label: 'Transcripción (STT)', description: 'Audio a texto.' },
  { value: 'tts', label: 'Síntesis (TTS)', description: 'Texto a voz.' },
];
const INFERENCE_EXAMPLES: Record<string, ExampleKind> = { llm: 'llm', stt: 'stt', tts: 'tts' };

function ScopeBadges({ scopes }: { scopes: ApiScope[] }) {
  return (
    <Group gap={4}>
      {scopes.map((s) => (
        <Badge key={s} color={s === 'calls' ? 'blue' : 'gray'}>
          {s}
        </Badge>
      ))}
    </Group>
  );
}

/** Ejemplos de la key recien creada, uno por alcance. */
function KeyExamples({ created }: { created: ApiKeyCreated }) {
  const tabs = created.scopes.map((s) =>
    s === 'calls'
      ? { value: s, label: 'Lanzar una llamada', code: curlExample(location.origin, created.key) }
      : {
          value: s,
          label: EXAMPLE_LABELS[INFERENCE_EXAMPLES[s]],
          code: inferenceExample(INFERENCE_EXAMPLES[s], location.origin, created.key),
        },
  );
  return (
    <Tabs defaultValue={tabs[0].value} keepMounted={false}>
      <Tabs.List mb="xs">
        {tabs.map((t) => (
          <Tabs.Tab key={t.value} value={t.value}>
            {t.label}
          </Tabs.Tab>
        ))}
      </Tabs.List>
      {tabs.map((t) => (
        <Tabs.Panel key={t.value} value={t.value}>
          <Group gap="xs" wrap="nowrap" align="flex-start">
            <Code block style={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {t.code}
            </Code>
            <CopyIcon value={t.code} label="Copiar ejemplo" />
          </Group>
        </Tabs.Panel>
      ))}
    </Tabs>
  );
}

function NewKeyModal({
  clientId,
  opened,
  onClose,
}: {
  clientId: string;
  opened: boolean;
  onClose: () => void;
}) {
  const create = useCreateApiKey(clientId);
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<ApiScope[]>(['calls']);
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);

  const close = async () => {
    if (
      created &&
      !(await confirmAction({
        title: '¿Copiaste la clave?',
        message: 'Después de cerrar no se puede volver a ver. Si la perdés, revocala y creá otra.',
        confirmLabel: 'Ya la copié',
      }))
    ) {
      return;
    }
    onClose();
  };

  return (
    <Modal
      opened={opened}
      onClose={() => void close()}
      title={created ? 'API key creada' : 'Nueva API key'}
      size="lg"
    >
      {created ? (
        <Stack>
          <Alert color="yellow" icon={<IconAlertTriangle size={18} />} title="Copiala ahora">
            Es la única vez que se muestra. Guardala en un lugar seguro.
          </Alert>
          <Group gap="xs" wrap="nowrap">
            <Code block style={{ flex: 1, wordBreak: 'break-all' }}>
              {created.key}
            </Code>
            <CopyIcon value={created.key} label="Copiar clave" />
          </Group>
          <KeyExamples created={created} />
          <Group justify="flex-end">
            <Button onClick={() => void close()}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!name.trim()) return;
            create.mutate(
              { name: name.trim(), scopes },
              {
                onSuccess: (k) => setCreated(k),
                onError: (err) => notifyError(err, 'No se pudo crear la API key'),
              },
            );
          }}
        >
          <Stack>
            <TextInput
              label="Nombre"
              description="Para reconocerla después (ej. CRM, integración de ventas)."
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
              maxLength={64}
              data-autofocus
              required
            />
            <Checkbox.Group
              label="Acceso"
              description="Una key solo sirve para lo que marques acá. Las de inferencia cuentan contra los límites de tu plan."
              value={scopes}
              onChange={(v) => setScopes(v as ApiScope[])}
            >
              <Stack gap="xs" mt="xs">
                {SCOPE_OPTIONS.map((o) => (
                  <Checkbox key={o.value} value={o.value} label={o.label} description={o.description} />
                ))}
              </Stack>
            </Checkbox.Group>
            <Group justify="flex-end">
              <Button variant="default" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" loading={create.isPending} disabled={!name.trim() || scopes.length === 0}>
                Crear
              </Button>
            </Group>
          </Stack>
        </form>
      )}
    </Modal>
  );
}

export function ApiKeysSection({ clientId }: { clientId: string }) {
  const keys = useApiKeys(clientId);
  const revoke = useRevokeApiKey(clientId);
  const [creating, setCreating] = useState(false);

  const doRevoke = async (k: ApiKey) => {
    if (
      await confirmAction({
        title: 'Revocar API key',
        message: `Los sistemas que usan "${k.name}" (${k.prefix}…) dejan de tener acceso. No se puede deshacer.`,
        confirmLabel: 'Revocar',
        danger: true,
      })
    ) {
      revoke.mutate(k.id, {
        onSuccess: () => notifySuccess('API key revocada.'),
        onError: (e) => notifyError(e),
      });
    }
  };

  return (
    <Card>
      <Group justify="space-between" mb="xs">
        <Title order={4}>API keys</Title>
        <Button size="xs" leftSection={<IconPlus size={16} />} onClick={() => setCreating(true)}>
          Nueva API key
        </Button>
      </Group>
      <Text size="xs" c="dimmed" mb="sm">
        Para que tus sistemas lancen llamadas, lean resultados o usen el LLM, la transcripción y la síntesis
        de voz: van en <Code>Authorization: Bearer &lt;key&gt;</Code>. Cada key tiene su alcance.
      </Text>
      <QueryState query={keys}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>Sin API keys.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={720}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Prefijo</Table.Th>
                    <Table.Th>Acceso</Table.Th>
                    <Table.Th>Creada</Table.Th>
                    <Table.Th>Último uso</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((k) => (
                    <Table.Tr key={k.id} style={k.revoked_at ? { opacity: 0.6 } : undefined}>
                      <Table.Td>
                        <Group gap={6} wrap="nowrap">
                          <IconKey size={14} />
                          {k.name}
                        </Group>
                      </Table.Td>
                      <Table.Td className="mono">{k.prefix}…</Table.Td>
                      <Table.Td>
                        <ScopeBadges scopes={k.scopes} />
                      </Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(k.created_at)}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>
                        {k.last_used_at ? formatDateTime(k.last_used_at) : 'Nunca'}
                      </Table.Td>
                      <Table.Td>
                        {k.revoked_at ? (
                          <Badge color="gray">Revocada {formatDateTime(k.revoked_at)}</Badge>
                        ) : (
                          <Badge color="green">Activa</Badge>
                        )}
                      </Table.Td>
                      <Table.Td ta="right">
                        {!k.revoked_at && (
                          <Button
                            size="compact-sm"
                            variant="subtle"
                            color="red"
                            onClick={() => void doRevoke(k)}
                          >
                            Revocar
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      {creating && <NewKeyModal clientId={clientId} opened onClose={() => setCreating(false)} />}
    </Card>
  );
}
