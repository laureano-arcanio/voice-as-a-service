import { ActionIcon, Anchor, Badge, Button, Group, Stack, Table, Text, Tooltip } from '@mantine/core';
import { IconArrowUp, IconKey, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { useAgentSecrets, useClientSecrets, useDeleteSecret, usePromoteSecret } from '@/features/tools/api';
import { type SecretDialog, SecretModal } from '@/features/tools/SecretModal';
import { notifyError, notifySuccess } from '@/lib/notify';

type Row = {
  name: string;
  description: string;
  last4: string;
  used_by: string[];
  /** agent: valor propio del agente; client: usa el del cliente; null: falta. */
  source: 'agent' | 'client' | null;
  overrides: boolean;
};

/**
 * Los secretos que usan las herramientas del agente: los del cliente (para todos los agentes), los propios de este
 * agente (pisan a los del cliente) y los que faltan. needed: los que piden las herramientas elegidas en el formulario
 * (aunque no se haya guardado). Sin agentId (agente nuevo), solo se cargan en el cliente.
 */
export function SecretsSection({
  clientId,
  agentId,
  needed,
}: {
  clientId: string;
  agentId?: string;
  needed: Map<string, string[]>;
}) {
  const clientSecrets = useClientSecrets(clientId);
  const agentSecrets = useAgentSecrets(agentId);
  const remove = useDeleteSecret(agentId ?? '');
  const promote = usePromoteSecret(agentId ?? '');
  const [dialog, setDialog] = useState<SecretDialog | null>(null);

  const client = new Map((clientSecrets.data ?? []).filter((s) => !s.missing).map((s) => [s.name, s]));
  const own = (agentSecrets.data ?? []).filter((s) => s.source === 'agent');
  const ownNames = new Set(own.map((s) => s.name));
  const rows: Row[] = [
    ...own.map((s) => ({
      name: s.name,
      description: s.description,
      last4: s.last4,
      used_by: [...new Set([...s.used_by, ...(needed.get(s.name) ?? [])])],
      source: 'agent' as const,
      overrides: client.has(s.name),
    })),
    ...[...needed.entries()]
      .filter(([name]) => !ownNames.has(name))
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([name, tools]) => {
        const c = client.get(name);
        return {
          name,
          description: c?.description ?? '',
          last4: c?.last4 ?? '',
          used_by: tools,
          source: c ? ('client' as const) : null,
          overrides: false,
        };
      }),
  ];

  const del = async (s: Row) => {
    const ok = await confirmAction({
      title: s.overrides ? `¿Volver al ${s.name} del cliente?` : `¿Borrar el secreto ${s.name}?`,
      message: s.overrides
        ? 'Se borra el valor propio de este agente y pasa a usar el que cargaste en Secretos.'
        : 'Se borra el valor. Las herramientas que lo usan dejan de funcionar en este agente.',
      confirmLabel: s.overrides ? 'Volver al del cliente' : 'Borrar',
      danger: !s.overrides,
    });
    if (ok)
      remove.mutate(s.name, {
        onSuccess: () => notifySuccess(s.overrides ? 'Ahora usa el del cliente.' : 'Secreto borrado.'),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  const toClient = async (s: Row) => {
    const ok = await confirmAction({
      title: `¿Pasar ${s.name} al cliente?`,
      message:
        'Lo van a usar todos los agentes. Los otros agentes que tienen el mismo valor dejan de tener el suyo.',
      confirmLabel: 'Pasar al cliente',
    });
    if (ok)
      promote.mutate(s.name, {
        onSuccess: () => notifySuccess(`${s.name} ahora es del cliente.`),
        onError: (e) => notifyError(e, 'No se pudo pasar'),
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
            Los tokens y claves de las herramientas. Se cargan una vez en{' '}
            <Anchor component={Link} to={'/secrets'} inherit>
              Secretos
            </Anchor>{' '}
            y los usan todos los agentes; acá podés darle a este agente un valor propio. El agente nunca los
            ve.
          </Text>
        </div>
        {agentId && (
          <Button
            variant="default"
            size="xs"
            leftSection={<IconPlus size={16} />}
            onClick={() => setDialog({ scope: 'agent', lockScope: true })}
          >
            Valor propio
          </Button>
        )}
      </Group>
      {rows.length === 0 ? (
        <Text size="sm" c="dimmed">
          Las herramientas elegidas no usan secretos.
        </Text>
      ) : (
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
                    {s.source === null ? (
                      <Badge color="yellow">Falta</Badge>
                    ) : (
                      <Group gap={6} wrap="nowrap">
                        <Badge color={s.source === 'agent' ? 'blue' : 'gray'}>
                          {s.source === 'agent'
                            ? s.overrides
                              ? 'Propio (pisa al del cliente)'
                              : 'Propio'
                            : 'Del cliente'}
                        </Badge>
                        {s.last4 && (
                          <Text span className="mono" size="sm">
                            ••••{s.last4}
                          </Text>
                        )}
                      </Group>
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
                      {s.source === null && (
                        <Button
                          size="compact-sm"
                          variant="subtle"
                          leftSection={<IconKey size={16} />}
                          onClick={() => setDialog({ name: s.name, scope: 'client' })}
                        >
                          Cargar valor
                        </Button>
                      )}
                      {s.source === 'client' && agentId && (
                        <Button
                          size="compact-sm"
                          variant="subtle"
                          onClick={() => setDialog({ name: s.name, scope: 'agent', lockScope: true })}
                        >
                          Usar otro valor acá
                        </Button>
                      )}
                      {s.source === 'agent' && (
                        <>
                          <Button
                            size="compact-sm"
                            variant="subtle"
                            onClick={() =>
                              setDialog({
                                name: s.name,
                                scope: 'agent',
                                lockScope: true,
                                replace: { description: s.description },
                              })
                            }
                          >
                            Reemplazar valor
                          </Button>
                          {!s.overrides && (
                            <Tooltip label="Pasar al cliente (para todos los agentes)" withArrow>
                              <ActionIcon
                                variant="subtle"
                                aria-label={`Pasar ${s.name} al cliente`}
                                onClick={() => void toClient(s)}
                              >
                                <IconArrowUp size={16} />
                              </ActionIcon>
                            </Tooltip>
                          )}
                          <Tooltip label={s.overrides ? 'Volver al del cliente' : 'Borrar'} withArrow>
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
      )}
      {dialog && (
        <SecretModal clientId={clientId} agentId={agentId} dialog={dialog} onClose={() => setDialog(null)} />
      )}
    </Stack>
  );
}
