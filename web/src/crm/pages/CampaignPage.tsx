import {
  ActionIcon,
  Anchor,
  Button,
  Card,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { IconArrowLeft, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { PageHeader } from '@/components/PageHeader';
import { QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCampaign, usePatchCampaign, useTemplates } from '../api';
import { MessagesTable } from '../components/MessagesTable';
import { CAMPAIGN_STATUS_OPTIONS } from '../format';
import type { Campaign, CampaignStep } from '../types';

const STATS: { key: keyof Campaign['stats']; label: string }[] = [
  { key: 'leads', label: 'Leads' },
  { key: 'first_sent', label: 'Primeros enviados' },
  { key: 'follow_up_sent', label: 'Seguimientos' },
  { key: 'drafts', label: 'Borradores' },
  { key: 'queued', label: 'En cola' },
  { key: 'bounced', label: 'Rebotes' },
  { key: 'replies', label: 'Respuestas' },
  { key: 'ga_users', label: 'Usuarios GA' },
];

function CampaignForm({ c }: { c: Campaign }) {
  const patch = usePatchCampaign();
  const form = useForm({
    initialValues: {
      name: c.name,
      status: c.status as string,
      segment: c.segment ?? '',
      from_addr: c.from_addr ?? '',
      started_at: c.started_at,
      notes: c.notes ?? '',
    },
  });
  return (
    <Card withBorder>
      <form
        onSubmit={form.onSubmit((v) =>
          patch.mutate(
            {
              id: c.id,
              name: v.name.trim(),
              status: v.status as Campaign['status'],
              segment: v.segment.trim() || null,
              from_addr: v.from_addr.trim() || null,
              started_at: v.started_at,
              notes: v.notes.trim() || null,
            },
            {
              onSuccess: () => {
                notifySuccess('Guardado.');
                form.resetDirty();
              },
              onError: (e) => notifyError(e),
            },
          ),
        )}
      >
        <Group justify="space-between" mb="xs">
          <Title order={4}>Datos</Title>
          <Button size="compact-sm" type="submit" disabled={!form.isDirty()} loading={patch.isPending}>
            Guardar
          </Button>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput label="Nombre" {...form.getInputProps('name')} />
          <Select
            label="Estado"
            data={CAMPAIGN_STATUS_OPTIONS}
            allowDeselect={false}
            {...form.getInputProps('status')}
          />
          <TextInput label="Remitente" placeholder="CRM_MAIL_FROM" {...form.getInputProps('from_addr')} />
          <DateInput label="Empieza" valueFormat="D/M/YYYY" clearable {...form.getInputProps('started_at')} />
          <Textarea label="Segmento" autosize minRows={2} {...form.getInputProps('segment')} />
          <Textarea label="Notas" autosize minRows={2} {...form.getInputProps('notes')} />
        </SimpleGrid>
      </form>
    </Card>
  );
}

function SequenceCard({ c }: { c: Campaign }) {
  const patch = usePatchCampaign();
  const templates = useTemplates();
  const [steps, setSteps] = useState<CampaignStep[]>(c.sequence);
  const dirty = JSON.stringify(steps) !== JSON.stringify(c.sequence);
  const options = (templates.data ?? [])
    .filter((t) => t.kind !== 'first')
    .map((t) => ({ value: String(t.id), label: t.name }));
  const set = (i: number, p: Partial<CampaignStep>) =>
    setSteps((s) => s.map((x, j) => (j === i ? { ...x, ...p } : x)));

  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Secuencia de seguimientos</Title>
        <Button
          size="compact-sm"
          disabled={!dirty}
          loading={patch.isPending}
          onClick={() =>
            patch.mutate(
              { id: c.id, sequence: steps },
              { onSuccess: () => notifySuccess('Secuencia guardada.'), onError: (e) => notifyError(e) },
            )
          }
        >
          Guardar
        </Button>
      </Group>
      <Text size="sm" c="dimmed" mb="sm">
        Cada seguimiento sale en el hilo, los días hábiles indicados después del último mail, si el lead no
        respondió. Con plantilla, el CRM arma el borrador solo (campaña activa) y queda en Hoy para aprobar.
        {steps.length === 0 &&
          ' Sin secuencia: un seguimiento a los 4 días hábiles, con la plantilla que elijas al armarlo.'}
      </Text>
      <Stack gap="xs">
        {steps.map((st, i) => (
          <Group key={i} align="flex-end" gap="sm">
            <Text size="sm" fw={600} w={110} pb={8}>
              Seguimiento {i + 1}
            </Text>
            <NumberInput
              label="Días hábiles"
              min={1}
              max={60}
              w={110}
              value={st.days}
              onChange={(v) => set(i, { days: Number(v) || 1 })}
            />
            <Select
              label="Plantilla"
              data={options}
              value={st.template_id ? String(st.template_id) : null}
              onChange={(v) => set(i, { template_id: v ? Number(v) : null })}
              clearable
              placeholder="Elegirla al armarlo"
              style={{ flex: 1, minWidth: 200 }}
            />
            <ActionIcon
              variant="subtle"
              color="gray"
              mb={4}
              aria-label={`Quitar el seguimiento ${i + 1}`}
              onClick={() => setSteps((s) => s.filter((_, j) => j !== i))}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
        ))}
        <Group>
          <Button
            size="compact-sm"
            variant="default"
            leftSection={<IconPlus size={14} />}
            onClick={() => setSteps((s) => [...s, { days: s.length ? 5 : 4, template_id: null }])}
          >
            Agregar seguimiento
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

export function CampaignPage() {
  const id = Number(useParams().id);
  const campaign = useCampaign(id);
  return (
    <QueryState query={campaign}>
      {(c) => (
        <>
          <PageHeader
            title={c.name}
            description={<span className="mono">utm_campaign={c.slug}</span>}
            above={
              <Anchor component={Link} to="/campanas" size="sm">
                <Group gap={4}>
                  <IconArrowLeft size={14} /> Campañas
                </Group>
              </Anchor>
            }
          />
          <Stack gap="md">
            <SimpleGrid cols={{ base: 2, sm: 4, lg: 8 }}>
              {STATS.map((s) => (
                <Card withBorder key={s.key} p="sm">
                  <Text className="label">{s.label}</Text>
                  <Text className="metric" c={s.key === 'bounced' && c.stats.bounced ? 'red' : undefined}>
                    {c.stats[s.key] ?? 0}
                  </Text>
                </Card>
              ))}
            </SimpleGrid>
            <CampaignForm key={c.id} c={c} />
            <SequenceCard key={`seq-${c.id}`} c={c} />
            <Title order={3}>Mensajes</Title>
            <MessagesTable campaignId={c.id} />
          </Stack>
        </>
      )}
    </QueryState>
  );
}
