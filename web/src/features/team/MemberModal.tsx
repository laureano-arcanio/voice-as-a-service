import { Button, Group, Modal, Select, Stack, Switch, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { ApiError } from '@/api/errors';
import type { TeamMember } from '@/api/types';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useMemberPresence, useSaveMember } from './api';

/** Alta o edicion de una persona del equipo. */
export function MemberModal({ member, onClose }: { member: TeamMember | null; onClose: () => void }) {
  const save = useSaveMember();
  const users = useMemberPresence();
  const form = useForm({
    initialValues: {
      name: member?.name ?? '',
      phone: member?.phone ?? '',
      whatsapp: member?.whatsapp ?? '',
      user_id: member?.user_id ?? '',
      active: member?.active ?? true,
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      phone: (v, values) =>
        v.trim() || values.whatsapp.trim() || values.user_id
          ? null
          : 'Cargá un teléfono, un WhatsApp o un usuario del panel',
    },
  });

  // Un usuario del panel es de una sola persona: se ofrecen los libres y el de esta.
  const userOptions = (users.data ?? [])
    .filter((u) => !u.team_member_id || u.team_member_id === member?.id)
    .map((u) => ({ value: u.user_id, label: u.name }));
  if (member?.user_id && !userOptions.some((o) => o.value === member.user_id)) {
    userOptions.push({ value: member.user_id, label: 'Usuario del panel' });
  }

  return (
    <Modal opened onClose={onClose} title={member ? `Editar a ${member.name}` : 'Nueva persona del equipo'}>
      <form
        onSubmit={form.onSubmit((v) =>
          save.mutate(
            {
              id: member?.id,
              body: {
                name: v.name.trim(),
                phone: v.phone.trim() || null,
                whatsapp: v.whatsapp.trim() || null,
                user_id: v.user_id || null,
                active: v.active,
              },
            },
            {
              onSuccess: (m) => {
                notifySuccess(member ? 'Persona guardada.' : `${m.name} se sumó al equipo.`);
                onClose();
              },
              onError: (e) => {
                if (e instanceof ApiError && e.code === 'whatsapp_taken')
                  form.setFieldError('whatsapp', e.message);
                else if (e instanceof ApiError && e.code === 'team_members_limit')
                  notifyError(e, 'Tope de personas del plan');
                else notifyError(e, 'No se pudo guardar');
              },
            },
          ),
        )}
      >
        <Stack>
          <TextInput label="Nombre" maxLength={120} data-autofocus {...form.getInputProps('name')} />
          <TextInput
            label="Teléfono"
            description="Para pasarle llamadas. Por ahora, solo de Argentina."
            placeholder="351 555-1234"
            maxLength={32}
            {...form.getInputProps('phone')}
          />
          <TextInput
            label="WhatsApp"
            description="Para pasarle conversaciones de WhatsApp. No se puede repetir en el equipo."
            placeholder="+54 9 351 555-1234"
            maxLength={32}
            {...form.getInputProps('whatsapp')}
          />
          <Select
            label="Usuario del panel"
            description="Para que atienda llamadas desde el panel, con Disponible. Puede ser lo único que cargues."
            placeholder={users.isPending ? 'Cargando…' : 'Ninguno'}
            data={userOptions}
            clearable
            searchable
            nothingFoundMessage="No hay usuarios libres"
            value={form.values.user_id || null}
            onChange={(v) => form.setFieldValue('user_id', v ?? '')}
          />
          <Switch
            label="Activa"
            description="Una persona inactiva no recibe derivaciones, pero sigue en sus áreas."
            {...form.getInputProps('active', { type: 'checkbox' })}
          />
          <Group justify="flex-end" mt="xs">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={save.isPending}>
              {member ? 'Guardar cambios' : 'Agregar persona'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
