import { Button, Group, Modal, SegmentedControl, Stack, Switch, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { ApiError } from '@/api/errors';
import type { TeamMember } from '@/api/types';
import { useCurrentUser } from '@/features/auth/api';
import { notifyError, notifyInvite, notifySuccess } from '@/lib/notify';
import { useInviteMember, useSaveMember } from './api';

/** Alta o edicion de una persona del equipo. Con "Acceso al panel" crea su usuario y le manda la invitación. */
export function MemberModal({ member, onClose }: { member: TeamMember | null; onClose: () => void }) {
  const save = useSaveMember();
  const invite = useInviteMember();
  const me = useCurrentUser();
  const editing = !!member;
  const hasUser = !!member?.user_id;
  const self = member?.user_id === me.id;
  const form = useForm({
    initialValues: {
      name: member?.name ?? '',
      phone: member?.phone ?? '',
      active: member?.active ?? true,
      whatsapp_notify: member?.whatsapp_notify ?? false,
      panel_access: member?.panel_access ?? false,
      email: member?.email ?? '',
      role: (member?.role ?? 'user') as 'admin' | 'user',
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      phone: (v, values) =>
        v.trim() || values.panel_access || (editing && hasUser) ? null : 'Cargá un teléfono o dale acceso al panel',
      email: (v, values) =>
        !values.panel_access || hasUser || /^\S+@\S+\.\S+$/.test(v.trim()) ? null : 'Email inválido',
    },
  });

  const hasPhone = !!form.values.phone.trim();
  const showEmail = form.values.panel_access && !hasUser;

  const submit = form.onSubmit((v) => {
    const body: Record<string, unknown> = {
      name: v.name.trim(),
      phone: v.phone.trim() || null,
      active: v.active,
      whatsapp_notify: v.whatsapp_notify && hasPhone,
    };
    if (!editing) {
      if (v.panel_access) {
        body.email = v.email.trim();
        body.role = v.role;
      }
    } else if (hasUser) {
      body.role = v.role;
      body.panel_access = v.panel_access;
    } else if (v.panel_access) {
      body.email = v.email.trim();
      body.role = v.role;
    }
    save.mutate(
      { id: member?.id, body: body as never },
      {
        onSuccess: (m) => {
          if (m.invite) notifyInvite(m.invite);
          else notifySuccess(editing ? 'Persona guardada.' : `${m.name} se sumó al equipo.`);
          onClose();
        },
        onError: (e) => {
          if (e instanceof ApiError && e.code === 'team_members_limit')
            notifyError(e, 'Tope de personas del plan');
          else notifyError(e, 'No se pudo guardar');
        },
      },
    );
  });

  return (
    <Modal opened onClose={onClose} title={member ? `Editar a ${member.name}` : 'Nueva persona del equipo'}>
      <form onSubmit={submit}>
        <Stack>
          <TextInput label="Nombre" maxLength={120} data-autofocus {...form.getInputProps('name')} />
          <TextInput
            label="Teléfono"
            description="Para pasarle llamadas. Por ahora, solo de Argentina."
            placeholder="351 555-1234"
            maxLength={32}
            {...form.getInputProps('phone')}
          />
          <Switch
            label="Recibe WhatsApp"
            description={
              hasPhone
                ? 'Le avisamos por WhatsApp, a este mismo teléfono, de los pedidos de sus áreas. Los avisos salen con las plantillas de cada área.'
                : 'Cargá un teléfono para poder avisarle por WhatsApp.'
            }
            disabled={!hasPhone}
            checked={hasPhone && form.values.whatsapp_notify}
            onChange={(e) => form.setFieldValue('whatsapp_notify', e.currentTarget.checked)}
          />
          <Switch
            label="Acceso al panel"
            description={
              self
                ? 'Es tu usuario: no podés quitarte el acceso.'
                : hasUser
                  ? 'Apagado, no puede ingresar al panel; la persona y su lugar en el equipo quedan.'
                  : 'Le crea su usuario y le manda un email para que elija su clave.'
            }
            disabled={self}
            checked={form.values.panel_access}
            onChange={(e) => form.setFieldValue('panel_access', e.currentTarget.checked)}
          />
          {showEmail && (
            <>
              <TextInput
                label="Email"
                type="email"
                description="Con este email ingresa al panel."
                {...form.getInputProps('email')}
              />
              <Stack gap={4}>
                <Text size="sm" fw={500}>
                  Rol en el panel
                </Text>
                <SegmentedControl
                  data={[
                    { value: 'user', label: 'Usuario' },
                    { value: 'admin', label: 'Admin' },
                  ]}
                  {...form.getInputProps('role')}
                />
              </Stack>
            </>
          )}
          {editing && hasUser && (
            <>
              <TextInput label="Email" value={form.values.email} disabled description="Lo cambia en Perfil con un código." />
              <Stack gap={4}>
                <Text size="sm" fw={500}>
                  Rol en el panel
                </Text>
                <SegmentedControl
                  data={[
                    { value: 'user', label: 'Usuario' },
                    { value: 'admin', label: 'Admin' },
                  ]}
                  {...form.getInputProps('role')}
                />
              </Stack>
              {member.panel_access && !member.last_login_at && (
                <Button
                  variant="light"
                  loading={invite.isPending}
                  onClick={() =>
                    invite.mutate(member.id, {
                      onSuccess: (r) => notifyInvite(r),
                      onError: (e) => notifyError(e, 'No se pudo reenviar'),
                    })
                  }
                >
                  Reenviar invitación
                </Button>
              )}
            </>
          )}
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
