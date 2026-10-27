import { ActionIcon, Button, Card, Group, Table, Text, TextInput, Title, Tooltip } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { confirmAction } from '@/components/confirm';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useBlockedNumbers, useBlockNumber, useUnblockNumber } from './api';

/** Numeros cuyas llamadas entrantes no se atienden (bromas, acoso). Las salientes no cambian: eso son las bajas. */
export function BlockedNumbersCard() {
  const blocked = useBlockedNumbers();
  const block = useBlockNumber();
  const unblock = useUnblockNumber();
  const [phone, setPhone] = useState('');
  const [note, setNote] = useState('');

  const doUnblock = async (p: string, cid: string) => {
    const ok = await confirmAction({
      title: `Desbloquear ${p}`,
      message: 'Sus próximas llamadas se vuelven a atender.',
      confirmLabel: 'Desbloquear',
      danger: true,
    });
    if (ok)
      unblock.mutate(
        { phone: p, clientId: cid },
        { onSuccess: () => notifySuccess(`${p} desbloqueado.`), onError: (e) => notifyError(e) },
      );
  };

  return (
    <Card>
      <Group justify="space-between" mb="sm" gap="sm">
        <Title order={4}>Números bloqueados</Title>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            block.mutate(
              { phone, note },
              {
                onSuccess: (b) => {
                  notifySuccess(`${b.phone} bloqueado: sus llamadas no se atienden.`);
                  setPhone('');
                  setNote('');
                },
                onError: (err) => notifyError(err, 'No se pudo bloquear'),
              },
            );
          }}
        >
          <Group gap="xs">
            <TextInput
              placeholder="351 555-1234"
              aria-label="Teléfono a bloquear"
              value={phone}
              onChange={(e) => setPhone(e.currentTarget.value)}
              w={170}
            />
            <TextInput
              placeholder="Motivo (opcional)"
              aria-label="Motivo del bloqueo"
              value={note}
              onChange={(e) => setNote(e.currentTarget.value)}
              w={200}
            />
            <Button type="submit" variant="default" disabled={!phone.trim()} loading={block.isPending}>
              Bloquear
            </Button>
          </Group>
        </form>
      </Group>
      <Text size="sm" c="dimmed" mb="sm">
        Sus llamadas entrantes, por la línea o por WhatsApp, se cortan sin atender y quedan como rechazadas.
        Para no llamarlos en una campaña están las bajas.
      </Text>
      <QueryState query={blocked}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>No hay números bloqueados.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={560} mah={320}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Teléfono</Table.Th>
                    <Table.Th>Motivo</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((b) => (
                    <Table.Tr key={`${b.client_id}-${b.phone}`}>
                      <Table.Td className="mono">{b.phone}</Table.Td>
                      <Table.Td>{b.note || '–'}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(b.created_at)}</Table.Td>
                      <Table.Td>
                        <Group justify="flex-end">
                          <Tooltip label="Desbloquear" withArrow>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              aria-label={`Desbloquear ${b.phone}`}
                              onClick={() => void doUnblock(b.phone, b.client_id)}
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
  );
}
