import { Button, Group, Modal, PasswordInput, SegmentedControl, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCreateClientSecret, useCreateSecret, useUpdateClientSecret, useUpdateSecret } from './api';
import { SECRET_RE } from './draft';

export type SecretScope = 'client' | 'agent';

export type SecretDialog = {
  /** Nombre fijo (cargar uno que falta o reemplazar); vacio: lo escribe la persona. */
  name?: string;
  /** Reemplazar el valor de uno que ya esta (con su descripcion). */
  replace?: { description: string };
  /** Donde se guarda. Con agentId y sin lockScope, la persona elige. */
  scope: SecretScope;
  lockScope?: boolean;
};

/**
 * Cargar o reemplazar un secreto, del cliente (para todos sus agentes) o de un agente (pisa al del cliente).
 * onSaved: el nombre guardado (para insertarlo en un campo, por ejemplo).
 */
export function SecretModal({
  clientId,
  agentId,
  dialog,
  onClose,
  onSaved,
}: {
  clientId: string;
  agentId?: string;
  dialog: SecretDialog;
  onClose: () => void;
  onSaved?: (name: string) => void;
}) {
  const createClient = useCreateClientSecret(clientId);
  const updateClient = useUpdateClientSecret(clientId);
  const createAgent = useCreateSecret(agentId ?? '');
  const updateAgent = useUpdateSecret(agentId ?? '');
  const replacing = !!dialog.replace;
  const form = useForm({
    initialValues: {
      name: dialog.name ?? '',
      value: '',
      description: dialog.replace?.description ?? '',
      scope: agentId ? dialog.scope : ('client' as SecretScope),
    },
    validate: {
      name: (v) => (SECRET_RE.test(v) ? null : 'Mayúsculas, números y _ (ej. CRM_TOKEN)'),
      value: (v) => (v ? null : 'Escribí el valor'),
    },
  });
  const fixedName = !!dialog.name;
  const scope = form.values.scope;
  const pending =
    createClient.isPending || updateClient.isPending || createAgent.isPending || updateAgent.isPending;
  const title = replacing
    ? `Reemplazar ${dialog.name}`
    : dialog.name
      ? `Cargar ${dialog.name}`
      : 'Nuevo secreto';

  return (
    <Modal opened onClose={onClose} title={title}>
      <form
        onSubmit={form.onSubmit((v) => {
          const done = {
            onSuccess: () => {
              notifySuccess(replacing ? 'Valor reemplazado.' : 'Secreto guardado.');
              onSaved?.(v.name);
              onClose();
            },
            onError: (e: unknown) => notifyError(e, 'No se pudo guardar'),
          };
          const body = { value: v.value, description: v.description.trim() };
          if (v.scope === 'agent') {
            if (replacing) updateAgent.mutate({ name: v.name, body }, done);
            else createAgent.mutate({ name: v.name, ...body }, done);
          } else if (replacing) updateClient.mutate({ name: v.name, body }, done);
          else createClient.mutate({ name: v.name, ...body }, done);
        })}
      >
        <Stack>
          {agentId && !dialog.lockScope && (
            <div>
              <SegmentedControl
                fullWidth
                aria-label="Dónde se guarda"
                data={[
                  { value: 'client', label: 'Para todos los agentes' },
                  { value: 'agent', label: 'Solo este agente' },
                ]}
                {...form.getInputProps('scope')}
              />
              <Text size="xs" c="dimmed" mt={4}>
                {scope === 'client'
                  ? 'Lo usan todos los agentes del cliente. Es lo habitual: un token de tu sistema se carga una vez.'
                  : 'Solo este agente usa este valor, aunque el cliente tenga otro con el mismo nombre.'}
              </Text>
            </div>
          )}
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
            <Button type="submit" loading={pending}>
              {replacing ? 'Reemplazar valor' : 'Guardar secreto'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
