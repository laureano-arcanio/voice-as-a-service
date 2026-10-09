import { Button, Group, Modal, Select, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useNavigate } from 'react-router';
import { useTiers } from '@/features/tiers/api';
import { SLUG_RE, slugify } from '@/lib/format';
import { notifyError, notifyInvite, notifySuccess } from '@/lib/notify';
import { useCreateClient } from './api';

export function NewClientModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const tiers = useTiers(opened);
  const create = useCreateClient();
  const navigate = useNavigate();
  const form = useForm({
    initialValues: { name: '', slug: '', slugEdited: false, tier_id: '', owner_email: '', owner_name: '' },
    validate: {
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      slug: (v) =>
        SLUG_RE.test(v) ? null : 'Minúsculas, números y _ (empieza con letra o número, hasta 64)',
      tier_id: (v) => (v ? null : 'Elegí un tier'),
      owner_email: (v) => (/^\S+@\S+\.\S+$/.test(v.trim()) ? null : 'Ingresá un email válido'),
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title="Nuevo cliente">
      <form
        onSubmit={form.onSubmit((v) =>
          create.mutate(
            {
              name: v.name.trim(),
              slug: v.slug,
              tier_id: v.tier_id,
              active: true,
              owner_email: v.owner_email.trim(),
              owner_name: v.owner_name.trim(),
            },
            {
              onSuccess: (c) => {
                if (c.invite) notifyInvite(c.invite, `Cliente ${c.name} creado. `);
                else notifySuccess(`Cliente ${c.name} creado.`);
                onClose();
                void navigate(`/clients/${c.id}`);
              },
              onError: (e) => notifyError(e, 'No se pudo crear el cliente'),
            },
          ),
        )}
      >
        <Stack>
          <TextInput
            label="Nombre"
            maxLength={128}
            data-autofocus
            {...form.getInputProps('name')}
            onChange={(e) => {
              const name = e.currentTarget.value;
              form.setFieldValue('name', name);
              if (!form.values.slugEdited) form.setFieldValue('slug', slugify(name));
            }}
          />
          <TextInput
            label="Slug"
            description="Identificador corto y único. Se arma del nombre; lo podés cambiar."
            {...form.getInputProps('slug')}
            onChange={(e) => {
              form.setFieldValue('slug', e.currentTarget.value.toLowerCase());
              form.setFieldValue('slugEdited', true);
            }}
          />
          <Select
            label="Tier"
            placeholder={tiers.isPending ? 'Cargando…' : 'Elegí un tier'}
            data={(tiers.data ?? []).map((t) => ({ value: t.id, label: t.name }))}
            {...form.getInputProps('tier_id')}
          />
          <TextInput
            label="Email del primer usuario"
            description="Le mandamos un email con el plan y el link para crear su clave."
            type="email"
            autoComplete="off"
            placeholder="persona@empresa.com"
            {...form.getInputProps('owner_email')}
          />
          <TextInput
            label="Nombre del usuario"
            description="Opcional: el saludo del email."
            maxLength={128}
            {...form.getInputProps('owner_name')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending}>
              Crear cliente
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
