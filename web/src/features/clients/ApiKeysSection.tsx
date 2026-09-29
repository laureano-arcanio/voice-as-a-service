import {
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconAlertTriangle, IconKey, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import type { ApiKey, ApiKeyCreated } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { CopyIcon } from '@/components/Copy';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from './api';
import { curlExample } from './curl';

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
          <Alert color="amber" icon={<IconAlertTriangle size={18} />} title="Copiala ahora">
            Es la única vez que se muestra. Guardala en un lugar seguro.
          </Alert>
          <Group gap="xs" wrap="nowrap">
            <Code block style={{ flex: 1, wordBreak: 'break-all' }}>
              {created.key}
            </Code>
            <CopyIcon value={created.key} label="Copiar clave" />
          </Group>
          <Text size="sm" fw={600}>
            Ejemplo: lanzar una llamada
          </Text>
          <Group gap="xs" wrap="nowrap" align="flex-start">
            <Code block style={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {curlExample(location.origin, created.key)}
            </Code>
            <CopyIcon value={curlExample(location.origin, created.key)} label="Copiar ejemplo" />
          </Group>
          <Group justify="flex-end">
            <Button onClick={() => void close()}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!name.trim()) return;
            create.mutate(name.trim(), {
              onSuccess: (k) => setCreated(k),
              onError: (err) => notifyError(err, 'No se pudo crear la API key'),
            });
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
            <Group justify="flex-end">
              <Button variant="default" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" loading={create.isPending} disabled={!name.trim()}>
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
        Para que tus sistemas lancen llamadas y lean resultados: van en{' '}
        <Code>Authorization: Bearer &lt;key&gt;</Code>.
      </Text>
      <QueryState query={keys}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>Sin API keys.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={620}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Prefijo</Table.Th>
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
                      <Table.Td>{formatDateTime(k.created_at)}</Table.Td>
                      <Table.Td>{k.last_used_at ? formatDateTime(k.last_used_at) : 'Nunca'}</Table.Td>
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
                            size="compact-xs"
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
