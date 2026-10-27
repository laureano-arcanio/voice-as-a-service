import { Button, Group, Modal, Radio, SimpleGrid, Stack, Text, Textarea, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { SLUG_RE, slugify } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAgentTemplates, useCreateAgent } from './api';

const BLANK = '';

function Choice({ value, title, children }: { value: string; title: string; children: ReactNode }) {
  return (
    <Radio.Card value={value} p="sm">
      <Group wrap="nowrap" align="flex-start" gap="sm">
        <Radio.Indicator />
        <Stack gap={2} style={{ minWidth: 0 }}>
          <Text size="sm" fw={600}>
            {title}
          </Text>
          <Text size="xs" c="dimmed">
            {children}
          </Text>
        </Stack>
      </Group>
    </Radio.Card>
  );
}

/** El agente se crea en el cliente de la sesión (el del usuario, o el que el admin tiene abierto en soporte). */
export function NewAgentModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const templates = useAgentTemplates(opened);
  const create = useCreateAgent();
  const navigate = useNavigate();
  const form = useForm({
    initialValues: {
      name: '',
      slug: '',
      description: '',
      template_id: 'asistente',
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      slug: (v) => (!v || SLUG_RE.test(v) ? null : 'Minúsculas, números y _ (hasta 64)'),
    },
  });
  const slugPreview = form.values.slug || slugify(form.values.name) || 'agente';

  return (
    <Modal opened={opened} onClose={onClose} title="Nuevo agente" size="lg">
      <form
        onSubmit={form.onSubmit((v) =>
          create.mutate(
            {
              client_id: null,
              name: v.name.trim(),
              slug: v.slug || null,
              description: v.description.trim(),
              template_id: v.template_id === BLANK ? null : v.template_id,
            },
            {
              onSuccess: (agent) => {
                notifySuccess(`Agente ${agent.name} creado.`);
                onClose();
                form.reset();
                void navigate(`/agents/${agent.id}?tab=conversacion`);
              },
              onError: (e) => notifyError(e, 'No se pudo crear el agente'),
            },
          ),
        )}
      >
        <Stack>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label="Nombre"
              description="Para reconocerlo en tus listas e informes."
              maxLength={128}
              data-autofocus
              {...form.getInputProps('name')}
            />
            <TextInput
              label="Slug"
              description={`Identificador del agente en tu cuenta. Queda: ${slugPreview}`}
              placeholder={slugify(form.values.name) || 'se arma del nombre'}
              {...form.getInputProps('slug')}
              onChange={(e) => form.setFieldValue('slug', e.currentTarget.value.toLowerCase())}
            />
            <Textarea
              label="Descripción"
              description="Opcional: para qué lo usás."
              autosize
              minRows={1}
              {...form.getInputProps('description')}
            />
          </SimpleGrid>
          <Radio.Group
            label="Punto de partida"
            description="Después completás cada parte en el formulario de la definición."
            {...form.getInputProps('template_id')}
          >
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs" mt="xs">
              {(templates.data ?? []).map((t) => (
                <Choice key={t.id} value={t.id} title={t.id === 'asistente' ? 'Asistente básico' : t.id}>
                  {t.objective}
                </Choice>
              ))}
              <Choice value={BLANK} title="En blanco">
                Solo lo mínimo para que sea válido: un dato a obtener y el resultado por defecto.
              </Choice>
            </SimpleGrid>
          </Radio.Group>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending}>
              Crear agente
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
