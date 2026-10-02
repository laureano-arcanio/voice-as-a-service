import {
  ActionIcon,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  type NumberInputProps,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { ApiError } from '@/api/errors';
import type { Tier } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatLimit } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { numberErrorTitle } from '@/features/numbers/errors';
import { useDeleteTier, useSaveTier, useTiers } from './api';

type Limit = number | '';

const toLimit = (v: Limit): number | null => (v === '' ? null : v);

function LimitInput(props: NumberInputProps) {
  return (
    <NumberInput
      placeholder="Ilimitado"
      description="Vacío = ilimitado"
      min={0}
      allowDecimal={false}
      allowNegative={false}
      thousandSeparator="."
      decimalSeparator=","
      {...props}
    />
  );
}

function TierModal({ tier, onClose }: { tier: Tier | null; onClose: () => void }) {
  const save = useSaveTier();
  const form = useForm<{
    name: string;
    description: string;
    max_concurrent_calls: Limit;
    inbound_minutes: Limit;
    outbound_minutes: Limit;
    max_phone_numbers: Limit;
  }>({
    initialValues: {
      name: tier?.name ?? '',
      description: tier?.description ?? '',
      max_concurrent_calls: tier?.max_concurrent_calls ?? '',
      inbound_minutes: tier?.inbound_minutes ?? '',
      outbound_minutes: tier?.outbound_minutes ?? '',
      max_phone_numbers: tier?.max_phone_numbers ?? '',
    },
    validate: { name: (v) => (v.trim() ? null : 'Poné un nombre') },
  });

  return (
    <Modal opened onClose={onClose} title={tier ? `Editar tier ${tier.name}` : 'Nuevo tier'}>
      <form
        onSubmit={form.onSubmit((v) =>
          save.mutate(
            {
              id: tier?.id,
              body: {
                name: v.name.trim(),
                description: v.description.trim(),
                max_concurrent_calls: toLimit(v.max_concurrent_calls),
                inbound_minutes: toLimit(v.inbound_minutes),
                outbound_minutes: toLimit(v.outbound_minutes),
                max_phone_numbers: toLimit(v.max_phone_numbers),
              },
            },
            {
              onSuccess: () => {
                notifySuccess(tier ? 'Tier actualizado. Aplica desde ya al mes en curso.' : 'Tier creado.');
                onClose();
              },
              onError: (e) => notifyError(e, numberErrorTitle(e)),
            },
          ),
        )}
      >
        <Stack>
          <TextInput label="Nombre" maxLength={64} data-autofocus {...form.getInputProps('name')} />
          <Textarea label="Descripción" autosize minRows={1} {...form.getInputProps('description')} />
          <LimitInput label="Llamadas simultáneas" {...form.getInputProps('max_concurrent_calls')} />
          <LimitInput label="Minutos entrantes por mes" {...form.getInputProps('inbound_minutes')} />
          <LimitInput label="Minutos salientes por mes" {...form.getInputProps('outbound_minutes')} />
          <LimitInput label="Números" {...form.getInputProps('max_phone_numbers')} />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={save.isPending}>
              Guardar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function TiersPage() {
  const tiers = useTiers();
  const del = useDeleteTier();
  const [editing, setEditing] = useState<Tier | 'new' | null>(null);

  const remove = async (t: Tier) => {
    if (
      !(await confirmAction({
        title: 'Borrar tier',
        message: `Se borra "${t.name}".`,
        confirmLabel: 'Borrar',
        danger: true,
      }))
    )
      return;
    del.mutate(t.id, {
      onSuccess: () => notifySuccess('Tier borrado.'),
      onError: (e) =>
        notifyError(
          e,
          e instanceof ApiError && e.status === 409 ? 'Tiene clientes: pasalos a otro tier antes' : undefined,
        ),
    });
  };

  return (
    <>
      <PageHeader
        title="Tiers"
        description="Límites por cliente: llamadas simultáneas, minutos entrantes y salientes por mes y números."
        actions={
          <Button leftSection={<IconPlus size={18} />} onClick={() => setEditing('new')}>
            Nuevo tier
          </Button>
        }
      />
      <Card>
        <QueryState query={tiers}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState>No hay tiers.</EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={720}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th ta="right">Simultáneas</Table.Th>
                      <Table.Th ta="right">Min. entrantes/mes</Table.Th>
                      <Table.Th ta="right">Min. salientes/mes</Table.Th>
                      <Table.Th ta="right">Números</Table.Th>
                      <Table.Th ta="right">Clientes</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((t) => (
                      <Table.Tr key={t.id}>
                        <Table.Td>
                          <Text size="sm" fw={600}>
                            {t.name}
                          </Text>
                          {t.description && (
                            <Text size="xs" c="dimmed">
                              {t.description}
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td ta="right">{formatLimit(t.max_concurrent_calls)}</Table.Td>
                        <Table.Td ta="right">{formatLimit(t.inbound_minutes)}</Table.Td>
                        <Table.Td ta="right">{formatLimit(t.outbound_minutes)}</Table.Td>
                        <Table.Td ta="right">{formatLimit(t.max_phone_numbers)}</Table.Td>
                        <Table.Td ta="right">{t.clients_count ?? 0}</Table.Td>
                        <Table.Td>
                          <Group gap={4} justify="flex-end" wrap="nowrap">
                            <Tooltip label="Editar">
                              <ActionIcon
                                variant="subtle"
                                color="gray"
                                onClick={() => setEditing(t)}
                                aria-label="Editar tier"
                              >
                                <IconPencil size={16} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label={t.clients_count ? 'Tiene clientes asignados' : 'Borrar'}>
                              <ActionIcon
                                variant="subtle"
                                color="red"
                                onClick={() => void remove(t)}
                                aria-label="Borrar tier"
                              >
                                <IconTrash size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      {editing && (
        <TierModal
          key={editing === 'new' ? 'new' : editing.id}
          tier={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}
