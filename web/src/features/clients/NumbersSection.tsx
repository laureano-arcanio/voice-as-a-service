import {
  ActionIcon,
  Button,
  Card,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconPencil, IconPlus, IconUnlink } from '@tabler/icons-react';
import { useState } from 'react';
import type { PhoneNumber } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { EmptyState, QueryState } from '@/components/QueryState';
import { NumberAgentSelect } from '@/features/numbers/AgentSelect';
import { useAssignNumber, usePhoneNumbers, useReleaseNumber } from '@/features/numbers/api';
import { numberErrorTitle } from '@/features/numbers/errors';
import { EditNumberModal } from '@/features/numbers/NumberModals';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';

/** Elegir uno de los numeros libres del inventario para este cliente. */
function AssignFromInventoryModal({ clientId, onClose }: { clientId: string; onClose: () => void }) {
  const free = usePhoneNumbers({ status: 'free' });
  const assign = useAssignNumber();
  const [numberId, setNumberId] = useState<string | null>(null);
  const options = (free.data ?? []).map((n) => ({
    value: n.id,
    label: `${n.e164}${n.label ? ` · ${n.label}` : ''}${n.provider ? ` (${n.provider})` : ''}`,
  }));
  return (
    <Modal opened onClose={onClose} title="Asignar número">
      <Stack>
        <Select
          label="Número libre del inventario"
          placeholder={
            free.isPending ? 'Cargando…' : options.length ? 'Buscá por número' : 'No hay números libres'
          }
          data={options}
          value={numberId}
          onChange={setNumberId}
          searchable
          nothingFoundMessage="Ningún número libre coincide"
          disabled={!options.length}
          data-autofocus
        />
        <Text size="xs" c="dimmed">
          Después elegí qué agente atiende las entrantes a ese número.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            disabled={!numberId}
            loading={assign.isPending}
            onClick={() =>
              numberId &&
              assign.mutate(
                { id: numberId, clientId },
                {
                  onSuccess: (n) => {
                    notifySuccess(`${n.e164} asignado.`);
                    onClose();
                  },
                  onError: (e) => notifyError(e, numberErrorTitle(e) ?? 'No se pudo asignar'),
                },
              )
            }
          >
            Asignar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/**
 * Numeros de un cliente: agente y etiqueta editables (admin y el propio cliente);
 * asignar desde el inventario y liberar, solo admin.
 */
export function NumbersSection({ clientId, canAssign }: { clientId: string; canAssign: boolean }) {
  const numbers = usePhoneNumbers({ clientId });
  const release = useReleaseNumber();
  const [assigning, setAssigning] = useState(false);
  const [editing, setEditing] = useState<PhoneNumber | null>(null);

  const doRelease = async (n: PhoneNumber) => {
    if (
      await confirmAction({
        title: `Liberar ${n.e164}`,
        message: 'Vuelve al inventario sin cliente ni agente: las llamadas a este número dejan de atenderse.',
        confirmLabel: 'Liberar',
        danger: true,
      })
    ) {
      release.mutate(n.id, {
        onSuccess: () => notifySuccess(`${n.e164} volvió al inventario.`),
        onError: (e) => notifyError(e, numberErrorTitle(e)),
      });
    }
  };

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Números</Title>
        {canAssign && (
          <Button size="xs" leftSection={<IconPlus size={16} />} onClick={() => setAssigning(true)}>
            Asignar número
          </Button>
        )}
      </Group>
      <QueryState query={numbers}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>Sin números asignados.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={640}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Número</Table.Th>
                    <Table.Th>Etiqueta</Table.Th>
                    <Table.Th>Atiende</Table.Th>
                    {canAssign && <Table.Th>Asignado el</Table.Th>}
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((n) => (
                    <Table.Tr key={n.id}>
                      <Table.Td className="mono">{n.e164}</Table.Td>
                      <Table.Td>
                        {n.label || (
                          <Text span inherit c="dimmed">
                            –
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <NumberAgentSelect number={n} />
                      </Table.Td>
                      {canAssign && (
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>
                          {n.assigned_at ? formatDateTime(n.assigned_at) : '–'}
                        </Table.Td>
                      )}
                      <Table.Td>
                        <Group gap={4} justify="flex-end" wrap="nowrap">
                          <Tooltip label="Editar etiqueta">
                            <ActionIcon
                              variant="subtle"
                              color="gray"
                              onClick={() => setEditing(n)}
                              aria-label={`Editar ${n.e164}`}
                            >
                              <IconPencil size={16} />
                            </ActionIcon>
                          </Tooltip>
                          {canAssign && (
                            <Tooltip label="Liberar">
                              <ActionIcon
                                variant="subtle"
                                color="red"
                                onClick={() => void doRelease(n)}
                                aria-label={`Liberar ${n.e164}`}
                              >
                                <IconUnlink size={16} />
                              </ActionIcon>
                            </Tooltip>
                          )}
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
      {assigning && <AssignFromInventoryModal clientId={clientId} onClose={() => setAssigning(false)} />}
      {editing && <EditNumberModal key={editing.id} number={editing} onClose={() => setEditing(null)} />}
    </Card>
  );
}
