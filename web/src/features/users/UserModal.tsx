import {
  Button,
  Group,
  Modal,
  PasswordInput,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import type { Role, User } from '@/api/types';
import { useClients } from '@/features/clients/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCreateUser, useUpdateUser } from './api';

const MIN_PASSWORD = 10;

/** Alta (user = null) o edicion de un usuario. Con `clientId`, el alta es de ese cliente. */
export function UserModal({
  user,
  clientId,
  selfId,
  opened,
  onClose,
}: {
  user: User | null;
  clientId?: string;
  selfId: string;
  opened: boolean;
  onClose: () => void;
}) {
  const clients = useClients(opened && !clientId && !user);
  const create = useCreateUser();
  const update = useUpdateUser();
  const isSelf = user?.id === selfId;
  const form = useForm({
    initialValues: {
      email: user?.email ?? '',
      name: user?.name ?? '',
      role: (user?.role ?? (clientId ? 'client' : 'admin')) as Role,
      client_id: user?.client_id ?? clientId ?? '',
      password: '',
      active: user?.active ?? true,
    },
    validate: {
      email: (v) => (user || /^\S+@\S+\.\S+$/.test(v.trim()) ? null : 'Email inválido'),
      password: (v) =>
        !user && v.length < MIN_PASSWORD
          ? `Mínimo ${MIN_PASSWORD} caracteres`
          : user && v && v.length < MIN_PASSWORD
            ? `Mínimo ${MIN_PASSWORD} caracteres (o dejala vacía)`
            : null,
      client_id: (v, values) => (!user && values.role === 'client' && !v ? 'Elegí el cliente' : null),
    },
  });

  const submit = form.onSubmit((v) => {
    const opts = {
      onSuccess: () => {
        notifySuccess(user ? 'Usuario actualizado.' : 'Usuario creado.');
        onClose();
      },
      onError: (e: unknown) => notifyError(e),
    };
    if (user) {
      update.mutate(
        {
          id: user.id,
          body: {
            name: v.name.trim(),
            active: isSelf ? undefined : v.active,
            password: v.password || undefined,
          },
        },
        opts,
      );
    } else {
      create.mutate(
        {
          email: v.email.trim(),
          name: v.name.trim(),
          password: v.password,
          role: v.role,
          client_id: v.role === 'client' ? v.client_id : null,
        },
        opts,
      );
    }
  });

  return (
    <Modal opened={opened} onClose={onClose} title={user ? `Editar ${user.email}` : 'Nuevo usuario'}>
      <form onSubmit={submit}>
        <Stack>
          <TextInput
            label="Email"
            type="email"
            disabled={!!user}
            data-autofocus={!user}
            {...form.getInputProps('email')}
          />
          <TextInput label="Nombre" maxLength={128} {...form.getInputProps('name')} />
          {!user && !clientId && (
            <Stack gap={4}>
              <Text size="sm" fw={500}>
                Rol
              </Text>
              <SegmentedControl
                data={[
                  { value: 'admin', label: 'Administrador' },
                  { value: 'client', label: 'Usuario de cliente' },
                ]}
                {...form.getInputProps('role')}
              />
            </Stack>
          )}
          {!user && !clientId && form.values.role === 'client' && (
            <Select
              label="Cliente"
              data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
              searchable
              {...form.getInputProps('client_id')}
            />
          )}
          <PasswordInput
            label={user ? 'Clave nueva' : 'Clave'}
            description={user ? 'Dejala vacía para no cambiarla.' : `Mínimo ${MIN_PASSWORD} caracteres.`}
            autoComplete="new-password"
            {...form.getInputProps('password')}
          />
          {user && (
            <Switch
              label="Activo"
              description={isSelf ? 'No podés desactivar tu propio usuario.' : 'Inactivo: no puede ingresar.'}
              disabled={isSelf}
              {...form.getInputProps('active', { type: 'checkbox' })}
            />
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending || update.isPending}>
              {user ? 'Guardar' : 'Crear usuario'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
