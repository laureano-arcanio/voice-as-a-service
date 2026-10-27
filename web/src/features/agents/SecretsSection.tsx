import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  PasswordInput,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconKey, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { AgentSecret } from '@/api/types';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAgentSecrets, useCreateSecret, useDeleteSecret, useUpdateSecret } from '@/features/tools/api';
import { SECRET_RE } from '@/features/tools/draft';

type Dialog = { kind: 'new'; name: string } | { kind: 'replace'; secret: AgentSecret } | null;

function SecretModal({
  agentId,
  dialog,
  onClose,
}: {
  agentId: string;
  dialog: Exclude<Dialog, null>;
  onClose: () => void;
}) {
  const create = useCreateSecret(agentId);
  const update = useUpdateSecret(agentId);
  const replacing = dialog.kind === 'replace';
  const form = useForm({
    initialValues: {
      name: replacing ? dialog.secret.name : dialog.name,
      value: '',
      description: replacing ? dialog.secret.description : '',
    },
    validate: {
      name: (v) => (SECRET_RE.test(v) ? null : 'Mayúsculas, números y _ (ej. CRM_TOKEN)'),
      value: (v) => (v ? null : 'Escribí el valor'),
    },
  });
  const fixedName = replacing || !!dialog.name;
  return (
    <Modal
      opened
      onClose={onClose}
      title={
        replacing
          ? `Reemplazar ${dialog.secret.name}`
          : dialog.name
            ? `Cargar ${dialog.name}`
            : 'Nuevo secreto'
      }
    >
      <form
        onSubmit={form.onSubmit((v) => {
          const done = {
            onSuccess: () => {
              notifySuccess(replacing ? 'Valor reemplazado.' : 'Secreto guardado.');
              onClose();
            },
            onError: (e: unknown) => notifyError(e, 'No se pudo guardar'),
          };
          if (replacing)
            update.mutate(
              { name: v.name, body: { value: v.value, description: v.description.trim() } },
              done,
            );
          else create.mutate({ name: v.name, value: v.value, description: v.description.trim() }, done);
        })}
      >
        <Stack>
          <TextInput
            label="Nombre"
            description="Las herramientas lo usan como {{secrets.NOMBRE}} o secrets.NOMBRE."
            placeholder="CRM_TOKEN"
            classNames={{ input: 'mono' }}
            readOnly={fixedName}
            data-autofocus={!fixedName || undefined}
            {...form.getInputProps('name')}
            onChange={(e) => form.setFieldValue('name', e.currentTarget.value.toUpperCase())}
          />
          <PasswordInput
            label="Valor"
            description="Se guarda cifrado y no se vuelve a mostrar. Para cambiarlo, se reemplaza."
            autoComplete="off"
            data-autofocus={fixedName || undefined}
            {...form.getInputProps('value')}
          />
          <TextInput
            label="Descripción"
            placeholder="Token de la API del CRM"
            maxLength={255}
            {...form.getInputProps('description')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending || update.isPending}>
              {replacing ? 'Reemplazar valor' : 'Guardar secreto'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

/**
 * Secretos del agente (tokens y claves de las herramientas): solo escritura. needed: los que piden las herramientas
 * elegidas en el formulario (aunque no se haya guardado), para avisar los que faltan antes de guardar.
 */
export function SecretsSection({ agentId, needed }: { agentId: string; needed: Map<string, string[]> }) {
  const secrets = useAgentSecrets(agentId);
  const remove = useDeleteSecret(agentId);
  const [dialog, setDialog] = useState<Dialog>(null);

  const del = async (s: AgentSecret) => {
    const ok = await confirmAction({
      title: `¿Borrar el secreto ${s.name}?`,
      message: 'Se borra el valor. Las herramientas que lo usan dejan de funcionar en este agente.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      remove.mutate(s.name, {
        onSuccess: () => notifySuccess('Secreto borrado.'),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  return (
    <Stack gap="xs">
      <Group justify="space-between" gap="sm">
        <div>
          <Text size="sm" fw={600}>
            Secretos
          </Text>
          <Text size="xs" c="dimmed">
            Tokens y claves que usan las herramientas de este agente. Se guardan cifrados y no se vuelven a
            mostrar; el agente nunca los ve.
          </Text>
        </div>
        <Button
          variant="default"
          size="xs"
          leftSection={<IconPlus size={16} />}
          onClick={() => setDialog({ kind: 'new', name: '' })}
        >
          Nuevo secreto
        </Button>
      </Group>
      <QueryState query={secrets}>
        {(list) => {
          const have = new Set(list.map((s) => s.name));
          // Los que piden las herramientas del formulario y todavia no estan (ni en la lista del servidor).
          const extra: AgentSecret[] = [...needed.entries()]
            .filter(([name]) => !have.has(name))
            .map(([name, tools]) => ({
              name,
              description: '',
              last4: '',
              used_by: tools,
              missing: true,
              created_at: null,
              updated_at: null,
            }));
          const rows = [...list, ...extra].map((s) => ({
            ...s,
            used_by: [...new Set([...s.used_by, ...(needed.get(s.name) ?? [])])],
          }));
          if (!rows.length)
            return (
              <Text size="sm" c="dimmed">
                Sin secretos. Si una herramienta necesita un token, cargalo acá.
              </Text>
            );
          return (
            <Table.ScrollContainer minWidth={620}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Valor</Table.Th>
                    <Table.Th>Descripción</Table.Th>
                    <Table.Th>Lo usan</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((s) => (
                    <Table.Tr key={s.name}>
                      <Table.Td className="mono">{s.name}</Table.Td>
                      <Table.Td>
                        {s.missing ? (
                          <Badge color="yellow">Falta</Badge>
                        ) : (
                          <Text span className="mono" size="sm">
                            ••••{s.last4}
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>{s.description ? <Text size="sm">{s.description}</Text> : <Dash />}</Table.Td>
                      <Table.Td>
                        {s.used_by.length ? (
                          <Text size="sm" className="mono">
                            {s.used_by.join(', ')}
                          </Text>
                        ) : (
                          <Dash />
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4} justify="flex-end" wrap="nowrap">
                          {s.missing ? (
                            <Button
                              size="compact-sm"
                              variant="subtle"
                              leftSection={<IconKey size={16} />}
                              onClick={() => setDialog({ kind: 'new', name: s.name })}
                            >
                              Cargar valor
                            </Button>
                          ) : (
                            <>
                              <Button
                                size="compact-sm"
                                variant="subtle"
                                onClick={() => setDialog({ kind: 'replace', secret: s })}
                              >
                                Reemplazar valor
                              </Button>
                              <Tooltip label="Borrar" withArrow>
                                <ActionIcon
                                  variant="subtle"
                                  color="red"
                                  aria-label={`Borrar ${s.name}`}
                                  onClick={() => void del(s)}
                                >
                                  <IconTrash size={16} />
                                </ActionIcon>
                              </Tooltip>
                            </>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          );
        }}
      </QueryState>
      {dialog && <SecretModal agentId={agentId} dialog={dialog} onClose={() => setDialog(null)} />}
    </Stack>
  );
}
