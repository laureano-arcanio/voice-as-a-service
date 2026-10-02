import {
  Badge,
  Button,
  Group,
  Modal,
  Radio,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useNavigate } from 'react-router';
import { useClients } from '@/features/clients/api';
import { SLUG_RE, slugify } from '@/lib/format';
import { ENGINE } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAgentTemplates, useCreateAgent } from './api';

export function NewAgentModal({
  opened,
  onClose,
  clientId,
  lockClient = false,
}: {
  opened: boolean;
  onClose: () => void;
  /** Cliente elegido de entrada. */
  clientId?: string;
  /** Sin poder cambiar el cliente (alta desde la ficha del cliente). */
  lockClient?: boolean;
}) {
  const clients = useClients(opened);
  const templates = useAgentTemplates(opened);
  const create = useCreateAgent();
  const navigate = useNavigate();
  const form = useForm({
    initialValues: { client_id: clientId ?? '', name: '', slug: '', description: '', template_id: '' },
    validate: {
      client_id: (v) => (v ? null : 'Elegí un cliente'),
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      slug: (v) => (!v || SLUG_RE.test(v) ? null : 'Minúsculas, números y _ (hasta 64)'),
      template_id: (v) => (v ? null : 'Elegí una plantilla'),
    },
  });
  const slugPreview = form.values.slug || slugify(form.values.name) || 'agente';

  return (
    <Modal opened={opened} onClose={onClose} title="Nuevo agente" size="xl">
      <form
        onSubmit={form.onSubmit((v) =>
          create.mutate(
            {
              client_id: v.client_id,
              name: v.name.trim(),
              slug: v.slug || null,
              description: v.description.trim(),
              template_id: v.template_id,
            },
            {
              onSuccess: (agent) => {
                notifySuccess(`Agente ${agent.name} creado.`);
                onClose();
                form.reset();
                void navigate(`/agents/${agent.id}?tab=definicion`);
              },
              onError: (e) => notifyError(e, 'No se pudo crear el agente'),
            },
          ),
        )}
      >
        <Stack>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <Select
              label="Cliente"
              data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
              searchable
              disabled={lockClient}
              {...form.getInputProps('client_id')}
            />
            <TextInput label="Nombre" maxLength={128} data-autofocus {...form.getInputProps('name')} />
            <TextInput
              label="Slug"
              description={`Identificador del agente en el cliente. Queda: ${slugPreview}`}
              placeholder={slugify(form.values.name) || 'se arma del nombre'}
              {...form.getInputProps('slug')}
              onChange={(e) => form.setFieldValue('slug', e.currentTarget.value.toLowerCase())}
            />
            <Textarea label="Descripción" autosize minRows={1} {...form.getInputProps('description')} />
          </SimpleGrid>
          <Radio.Group
            label="Plantilla de partida"
            description="Después editás la definición a gusto."
            {...form.getInputProps('template_id')}
          >
            <ScrollArea.Autosize mah={340} mt="xs" type="auto">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
                {(templates.data ?? []).map((t) => (
                  <Radio.Card key={t.id} value={t.id} p="sm">
                    <Group wrap="nowrap" align="flex-start" gap="sm">
                      <Radio.Indicator />
                      <Stack gap={2} style={{ minWidth: 0 }}>
                        <Text size="sm" fw={600} className="mono">
                          {t.id}
                        </Text>
                        <Text size="xs">{t.agent}</Text>
                        <Group gap={4}>
                          <Badge color="gray">{ENGINE[t.engine] ?? t.engine}</Badge>
                          <Badge color="gray">voz {t.voice ?? 'predeterminada'}</Badge>
                        </Group>
                        <Text size="xs" c="dimmed" lineClamp={3}>
                          {t.objective}
                        </Text>
                      </Stack>
                    </Group>
                  </Radio.Card>
                ))}
              </SimpleGrid>
            </ScrollArea.Autosize>
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
