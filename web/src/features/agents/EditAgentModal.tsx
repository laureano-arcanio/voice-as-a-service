import { Button, Group, Modal, Stack, Textarea, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { AgentDetail } from '@/api/types';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateAgent } from './api';

export function EditAgentModal({
  agent,
  opened,
  onClose,
}: {
  agent: AgentDetail;
  opened: boolean;
  onClose: () => void;
}) {
  const update = useUpdateAgent(agent.id);
  const form = useForm({
    initialValues: { name: agent.name, description: agent.description },
    validate: { name: (v) => (v.trim() ? null : 'Poné un nombre') },
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Editar agente">
      <form
        onSubmit={form.onSubmit((v) =>
          update.mutate(
            { name: v.name.trim(), description: v.description.trim() },
            {
              onSuccess: () => {
                notifySuccess('Agente actualizado.');
                onClose();
              },
              onError: (e) => notifyError(e),
            },
          ),
        )}
      >
        <Stack>
          <TextInput label="Nombre" maxLength={128} data-autofocus {...form.getInputProps('name')} />
          <Textarea label="Descripción" autosize minRows={2} {...form.getInputProps('description')} />
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
