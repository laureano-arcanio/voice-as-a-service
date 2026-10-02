import { Button, Checkbox, Group, Modal, PasswordInput, Select, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { WaAccount, WaAccountPatch } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { useClients } from '@/features/clients/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCreateWaAccount, useUpdateWaAccount } from './api';

const TOKEN_HELP =
  'Vacío: el del system user de nuestro portafolio (WA_ACCESS_TOKEN). Uno propio solo para números de otro portafolio. No se vuelve a mostrar.';

function agentOptions(agents: { id: string; name: string }[] | undefined, current?: WaAccount) {
  const data = (agents ?? []).map((a) => ({ value: a.id, label: a.name }));
  // El agente actual puede estar archivado: se sigue mostrando.
  if (current && !data.some((o) => o.value === current.agent_id)) {
    data.push({ value: current.agent_id, label: `${current.agent_name ?? 'Agente'} (archivado)` });
  }
  return data;
}

/** Alta manual (admin): numeros de nuestro portafolio. Los IDs salen de Meta (WhatsApp → Configuración de la API). */
export function NewWaAccountModal({ onClose }: { onClose: () => void }) {
  const clients = useClients();
  const create = useCreateWaAccount();
  const form = useForm({
    initialValues: {
      client_id: '',
      agent_id: '',
      phone_number_id: '',
      waba_id: '',
      display_phone_number: '',
      name: '',
      access_token: '',
    },
    validate: {
      client_id: (v) => (v ? null : 'Elegí el cliente'),
      agent_id: (v) => (v ? null : 'Elegí el agente'),
      phone_number_id: (v) => (/^\d{1,32}$/.test(v.trim()) ? null : 'Solo dígitos (el ID de Meta)'),
      waba_id: (v) => (v.trim() ? null : 'Requerido'),
      display_phone_number: (v) => (v.trim() ? null : 'Requerido'),
    },
  });
  const clientId = form.values.client_id;
  const agents = useAgents(clientId || undefined, false, !!clientId);

  return (
    <Modal opened onClose={onClose} title="Alta manual de un número de WhatsApp" size="lg">
      <form
        onSubmit={form.onSubmit((v) =>
          create.mutate(
            {
              client_id: v.client_id,
              agent_id: v.agent_id,
              phone_number_id: v.phone_number_id.trim(),
              waba_id: v.waba_id.trim(),
              display_phone_number: v.display_phone_number.trim(),
              name: v.name.trim(),
              access_token: v.access_token.trim() || null,
            },
            {
              onSuccess: (a) => {
                notifySuccess(`${a.display_phone_number} conectado; lo atiende ${a.agent_name}.`);
                onClose();
              },
              onError: (e) => notifyError(e, 'No se pudo conectar'),
            },
          ),
        )}
      >
        <Stack>
          <Group grow align="flex-start">
            <Select
              label="Cliente"
              data={(clients.data ?? []).map((c) => ({
                value: c.id,
                label: c.active ? c.name : `${c.name} (inactivo)`,
              }))}
              searchable
              data-autofocus
              {...form.getInputProps('client_id')}
              onChange={(v) => {
                form.setFieldValue('client_id', v ?? '');
                form.setFieldValue('agent_id', '');
              }}
            />
            <Select
              label="Agente que responde"
              placeholder={clientId ? undefined : 'Elegí primero el cliente'}
              data={agentOptions(agents.data)}
              disabled={!clientId}
              searchable
              {...form.getInputProps('agent_id')}
            />
          </Group>
          <Group grow align="flex-start">
            <TextInput
              label="Phone number ID"
              description="El ID del número en Meta, no el teléfono."
              classNames={{ input: 'mono' }}
              {...form.getInputProps('phone_number_id')}
            />
            <TextInput
              label="WABA ID"
              description="Cuenta de WhatsApp Business."
              classNames={{ input: 'mono' }}
              {...form.getInputProps('waba_id')}
            />
          </Group>
          <Group grow align="flex-start">
            <TextInput
              label="Número visible"
              placeholder="+54 351 555 0000"
              {...form.getInputProps('display_phone_number')}
            />
            <TextInput label="Nombre (opcional)" maxLength={128} {...form.getInputProps('name')} />
          </Group>
          <PasswordInput
            label="Token de acceso (opcional)"
            description={TOKEN_HELP}
            autoComplete="off"
            {...form.getInputProps('access_token')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending}>
              Conectar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

/** Agente, numero visible, nombre y token. Cliente e IDs de Meta no cambian. */
export function EditWaAccountModal({ account, onClose }: { account: WaAccount; onClose: () => void }) {
  const update = useUpdateWaAccount();
  const agents = useAgents(account.client_id, false);
  const form = useForm({
    initialValues: {
      agent_id: account.agent_id,
      display_phone_number: account.display_phone_number,
      name: account.name,
      access_token: '',
      clear_token: false,
    },
    validate: {
      agent_id: (v) => (v ? null : 'Elegí el agente'),
      display_phone_number: (v) => (v.trim() ? null : 'Requerido'),
    },
  });

  return (
    <Modal opened onClose={onClose} title={`Editar ${account.display_phone_number}`}>
      <form
        onSubmit={form.onSubmit((v) => {
          const body: WaAccountPatch = {
            agent_id: v.agent_id,
            display_phone_number: v.display_phone_number.trim(),
            name: v.name.trim(),
          };
          // Token: vacio no lo toca; "" en la API lo borra.
          if (v.clear_token) body.access_token = '';
          else if (v.access_token.trim()) body.access_token = v.access_token.trim();
          update.mutate(
            { id: account.id, body },
            {
              onSuccess: () => {
                notifySuccess('Número actualizado.');
                onClose();
              },
              onError: (e) => notifyError(e),
            },
          );
        })}
      >
        <Stack>
          <Select
            label="Agente que responde"
            description="Las conversaciones en curso siguen con su agente; el cambio vale para las nuevas."
            data={agentOptions(agents.data, account)}
            searchable
            data-autofocus
            {...form.getInputProps('agent_id')}
          />
          <TextInput label="Número visible" {...form.getInputProps('display_phone_number')} />
          <TextInput label="Nombre" maxLength={128} {...form.getInputProps('name')} />
          <PasswordInput
            label={account.has_token ? 'Reemplazar token propio' : 'Token propio (opcional)'}
            description={account.has_token ? 'Vacío: queda el que está.' : TOKEN_HELP}
            autoComplete="off"
            disabled={form.values.clear_token}
            {...form.getInputProps('access_token')}
          />
          {account.has_token && (
            <Checkbox
              label="Borrar el token propio (vuelve a WA_ACCESS_TOKEN)"
              {...form.getInputProps('clear_token', { type: 'checkbox' })}
            />
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={update.isPending}>
              Guardar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
