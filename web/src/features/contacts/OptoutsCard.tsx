import {
  ActionIcon,
  Button,
  Card,
  Group,
  Select,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { OptoutChannel } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAddOptout, useOptouts, useRemoveOptout } from './api';
import { OPTOUT_CHANNEL, OPTOUT_SOURCE } from './labels';

const CHANNEL_OPTIONS = (Object.keys(OPTOUT_CHANNEL) as OptoutChannel[]).map((value) => ({
  value,
  label: OPTOUT_CHANNEL[value],
}));

/** Numeros que pidieron no ser contactados (por WhatsApp, en una llamada o cargados a mano), por canal. */
export function OptoutsCard() {
  const optouts = useOptouts();
  const add = useAddOptout();
  const remove = useRemoveOptout();
  const [phone, setPhone] = useState('');
  const [channel, setChannel] = useState<OptoutChannel>('all');

  const doRemove = async (p: string, cid: string, ch: OptoutChannel) => {
    const ok = await confirmAction({
      title: `Sacar ${p} de las bajas`,
      message:
        'Las próximas campañas le van a volver a escribir o llamar. Hacelo solo si pidió que lo contacten.',
      confirmLabel: 'Sacar',
      danger: true,
    });
    if (ok)
      remove.mutate(
        { phone: p, clientId: cid, channel: ch },
        { onSuccess: () => notifySuccess('Número sacado de las bajas.'), onError: (e) => notifyError(e) },
      );
  };

  return (
    <Card>
      <Group justify="space-between" mb="sm" gap="sm">
        <Title order={4}>Bajas</Title>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate(
              { phone, channel },
              {
                onSuccess: (o) => {
                  notifySuccess(
                    `${o.phone} no va a ser contactado (${OPTOUT_CHANNEL[o.channel].toLowerCase()}).`,
                  );
                  setPhone('');
                },
                onError: (err) => notifyError(err, 'No se pudo cargar la baja'),
              },
            );
          }}
        >
          <Group gap="xs">
            <TextInput
              placeholder="351 555-1234"
              aria-label="Teléfono a dar de baja"
              value={phone}
              onChange={(e) => setPhone(e.currentTarget.value)}
              w={170}
            />
            <Select
              aria-label="Canal de la baja"
              data={CHANNEL_OPTIONS}
              value={channel}
              onChange={(v) => setChannel((v ?? 'all') as OptoutChannel)}
              allowDeselect={false}
              w={170}
            />
            <Button type="submit" variant="default" disabled={!phone.trim()} loading={add.isPending}>
              Dar de baja
            </Button>
          </Group>
        </form>
      </Group>
      <Text size="sm" c="dimmed" mb="sm">
        Ninguna campaña de ese canal les escribe ni los llama. Se suman solos cuando alguien responde a una
        campaña con "No me interesa" o "Baja", o cuando una llamada termina en un resultado de "no volver a
        llamar".
      </Text>
      <QueryState query={optouts}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>Nadie pidió la baja.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={560} mah={320}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Teléfono</Table.Th>
                    <Table.Th>Canal</Table.Th>
                    <Table.Th>Origen</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((o) => (
                    <Table.Tr key={`${o.client_id}-${o.phone}-${o.channel}`}>
                      <Table.Td className="mono">{o.phone}</Table.Td>
                      <Table.Td>{OPTOUT_CHANNEL[o.channel]}</Table.Td>
                      <Table.Td>{OPTOUT_SOURCE[o.source] ?? o.source}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(o.created_at)}</Table.Td>
                      <Table.Td>
                        <Group justify="flex-end">
                          <Tooltip label="Sacar de las bajas" withArrow>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              aria-label={`Sacar ${o.phone} de las bajas`}
                              onClick={() => void doRemove(o.phone, o.client_id, o.channel)}
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
