import { ActionIcon, Badge, Button, Group, Switch, Table, Text, Tooltip } from '@mantine/core';
import { IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { User } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useCurrentUser } from '@/features/auth/api';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useDeleteUser, useUpdateUser, useUsers } from './api';
import { UserModal } from './UserModal';

/** Usuarios (todos, o los de un cliente) con alta, edicion, activar y borrar. Solo admin. */
export function UsersTable({
  clientId,
  header,
}: {
  clientId?: string;
  header?: (addButton: React.ReactNode) => React.ReactNode;
}) {
  const me = useCurrentUser();
  const users = useUsers(clientId);
  const update = useUpdateUser();
  const del = useDeleteUser();
  const [editing, setEditing] = useState<User | 'new' | null>(null);

  const toggleActive = (u: User, active: boolean) =>
    update.mutate(
      { id: u.id, body: { active } },
      {
        onSuccess: () => notifySuccess(active ? 'Usuario activado.' : 'Usuario desactivado.'),
        onError: (e) => notifyError(e),
      },
    );

  const remove = async (u: User) => {
    if (
      await confirmAction({
        title: 'Borrar usuario',
        message: `Se borra ${u.email}. Si solo querés cortarle el acceso, desactivalo.`,
        confirmLabel: 'Borrar',
        danger: true,
      })
    ) {
      del.mutate(u.id, {
        onSuccess: () => notifySuccess('Usuario borrado.'),
        onError: (e) => notifyError(e),
      });
    }
  };

  const add = (
    <Button size="xs" leftSection={<IconPlus size={16} />} onClick={() => setEditing('new')}>
      Nuevo usuario
    </Button>
  );

  return (
    <>
      {header ? (
        header(add)
      ) : (
        <Group justify="flex-end" mb="sm">
          {add}
        </Group>
      )}
      <QueryState query={users}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>Sin usuarios.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={760}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Email</Table.Th>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Rol</Table.Th>
                    {!clientId && <Table.Th>Cliente</Table.Th>}
                    <Table.Th>Activo</Table.Th>
                    <Table.Th>Último ingreso</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((u) => {
                    const self = u.id === me.id;
                    return (
                      <Table.Tr key={u.id}>
                        <Table.Td>
                          {u.email}
                          {self && (
                            <Badge size="xs" ml={6} variant="outline">
                              vos
                            </Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          {u.name || (
                            <Text span inherit c="dimmed">
                              –
                            </Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Badge color={u.role === 'admin' ? 'amber' : 'navy'}>
                            {u.role === 'admin' ? 'Admin' : 'Cliente'}
                          </Badge>
                        </Table.Td>
                        {!clientId && <Table.Td>{u.client_name ?? '–'}</Table.Td>}
                        <Table.Td>
                          <Tooltip label="No podés desactivarte a vos" disabled={!self}>
                            <Switch
                              checked={u.active}
                              disabled={self}
                              onChange={(e) => toggleActive(u, e.currentTarget.checked)}
                              aria-label={u.active ? 'Desactivar' : 'Activar'}
                            />
                          </Tooltip>
                        </Table.Td>
                        <Table.Td>{u.last_login_at ? formatDateTime(u.last_login_at) : 'Nunca'}</Table.Td>
                        <Table.Td>
                          <Group gap={4} justify="flex-end" wrap="nowrap">
                            <Tooltip label="Editar">
                              <ActionIcon
                                variant="subtle"
                                onClick={() => setEditing(u)}
                                aria-label="Editar usuario"
                              >
                                <IconPencil size={16} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label={self ? 'No podés borrarte a vos' : 'Borrar'}>
                              <ActionIcon
                                variant="subtle"
                                color="red"
                                disabled={self}
                                onClick={() => void remove(u)}
                                aria-label="Borrar usuario"
                              >
                                <IconTrash size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      {editing && (
        <UserModal
          key={editing === 'new' ? 'new' : editing.id}
          user={editing === 'new' ? null : editing}
          clientId={clientId}
          selfId={me.id}
          opened
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}
