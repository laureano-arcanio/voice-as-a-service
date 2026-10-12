import {
  ActionIcon,
  Button,
  Card,
  Group,
  Modal,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { WaAccount, WaOperator } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useAgents } from '@/features/agents/api';
import { useClients } from '@/features/clients/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCreateWaOperator, useDeleteWaOperator, useUpdateWaOperator, useWaOperators } from './api';

export const WA_ID_RE = /^\d{8,15}$/;

function OperatorAgentSelect({ op }: { op: WaOperator }) {
  const agents = useAgents(op.client_id, false);
  const update = useUpdateWaOperator();
  const data = (agents.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  if (!data.some((o) => o.value === op.agent_id)) {
    data.push({ value: op.agent_id, label: `${op.agent_name ?? 'Agente'} (archivado)` });
  }
  return (
    <Select
      size="xs"
      w={200}
      data={data}
      value={op.agent_id}
      searchable
      allowDeselect={false}
      disabled={update.isPending}
      aria-label={`Agente de ${op.name || op.wa_id}`}
      onChange={(agentId) =>
        agentId &&
        agentId !== op.agent_id &&
        update.mutate(
          { id: op.id, body: { agent_id: agentId } },
          {
            onSuccess: (o) =>
              notifySuccess(`${o.name || o.wa_id} ahora habla con ${o.agent_name ?? 'el agente'}.`),
            onError: (e) => notifyError(e, 'No se pudo cambiar el agente'),
          },
        )
      }
    />
  );
}

function NewOperatorModal({ accounts, onClose }: { accounts: WaAccount[]; onClose: () => void }) {
  const clients = useClients();
  const create = useCreateWaOperator();
  const form = useForm({
    initialValues: { account_id: accounts[0]?.id ?? '', wa_id: '', client_id: '', agent_id: '', name: '' },
    validate: {
      account_id: (v) => (v ? null : 'Elegí el número'),
      wa_id: (v) => (WA_ID_RE.test(v.trim()) ? null : 'Solo dígitos, sin +: 5493511234567'),
      client_id: (v) => (v ? null : 'Elegí el cliente'),
      agent_id: (v) => (v ? null : 'Elegí el agente'),
    },
  });
  const agents = useAgents(form.values.client_id || undefined, false, !!form.values.client_id);
  const submit = form.onSubmit((v) =>
    create.mutate(
      { ...v, wa_id: v.wa_id.trim(), name: v.name.trim() },
      {
        onSuccess: (o) => {
          notifySuccess(`${o.name || o.wa_id} quedó como operador.`);
          onClose();
        },
        onError: (e) => notifyError(e, 'No se pudo crear el operador'),
      },
    ),
  );
  return (
    <Modal opened onClose={onClose} title="Nuevo operador">
      <form onSubmit={submit}>
        <Stack>
          <Select
            label="Número de WhatsApp"
            description="Al que le escribe el operador (el número compartido)."
            data={accounts.map((a) => ({
              value: a.id,
              label: `${a.display_phone_number} · ${a.name || a.client_name || ''}`,
            }))}
            allowDeselect={false}
            {...form.getInputProps('account_id')}
          />
          <TextInput
            label="Contacto"
            description="El WhatsApp del operador como lo manda Meta, sin + (con el 9 de celular)."
            placeholder="5493511234567"
            className="mono"
            {...form.getInputProps('wa_id')}
          />
          <TextInput label="Nombre" placeholder="Dueño de SUGYM" {...form.getInputProps('name')} />
          <Select
            label="Cliente"
            data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            searchable
            {...form.getInputProps('client_id')}
            onChange={(v) => {
              form.setFieldValue('client_id', v ?? '');
              form.setFieldValue('agent_id', '');
            }}
          />
          <Select
            label="Agente"
            description="Normalmente uno con motor asistente."
            data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
            disabled={!form.values.client_id}
            searchable
            {...form.getInputProps('agent_id')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending}>
              Crear operador
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

/** Operadores (solo admin): el dueño de un negocio que le habla a su asistente por un numero compartido. */
export function OperatorsCard({ accounts }: { accounts: WaAccount[] }) {
  const operators = useWaOperators();
  const update = useUpdateWaOperator();
  const del = useDeleteWaOperator();
  const [creating, setCreating] = useState(false);

  const doDelete = async (op: WaOperator) => {
    const ok = await confirmAction({
      title: `Borrar el operador ${op.name || op.wa_id}`,
      message: 'Sus mensajes los vuelve a atender el agente del número. Las conversaciones se conservan.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      del.mutate(op.id, {
        onSuccess: () => notifySuccess('Operador borrado.'),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  return (
    <Card mt="md">
      <Group justify="space-between" mb={4}>
        <Title order={4}>Operadores</Title>
        <Button
          variant="default"
          size="compact-sm"
          leftSection={<IconPlus size={16} />}
          onClick={() => setCreating(true)}
          disabled={!accounts.length}
        >
          Agregar operador
        </Button>
      </Group>
      <Text size="sm" c="dimmed" mb="md">
        Los mensajes de este contacto a este número los atiende el agente del operador, de su cliente, no el
        agente del número.
      </Text>
      <QueryState query={operators}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>No hay operadores.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={900}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Número</Table.Th>
                    <Table.Th>Contacto</Table.Th>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Cliente</Table.Th>
                    <Table.Th>Agente</Table.Th>
                    <Table.Th>Activo</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((op) => (
                    <Table.Tr key={op.id}>
                      <Table.Td className="mono" style={{ whiteSpace: 'nowrap' }}>
                        {op.account_number ?? '–'}
                      </Table.Td>
                      <Table.Td className="mono">{op.wa_id}</Table.Td>
                      <Table.Td>
                        {op.name || (
                          <Text span c="dimmed">
                            –
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>{op.client_name ?? '–'}</Table.Td>
                      <Table.Td>
                        <OperatorAgentSelect op={op} />
                      </Table.Td>
                      <Table.Td>
                        <Switch
                          checked={op.active}
                          aria-label={`Activo ${op.name || op.wa_id}`}
                          onChange={(e) =>
                            update.mutate(
                              { id: op.id, body: { active: e.currentTarget.checked } },
                              { onError: (err) => notifyError(err, 'No se pudo cambiar') },
                            )
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <Tooltip label="Borrar operador" withArrow>
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            aria-label={`Borrar ${op.name || op.wa_id}`}
                            onClick={() => void doDelete(op)}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      {creating && <NewOperatorModal accounts={accounts} onClose={() => setCreating(false)} />}
    </Card>
  );
}
