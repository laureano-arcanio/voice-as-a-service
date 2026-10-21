import {
  Anchor,
  Button,
  Card,
  Group,
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
import { IconArrowLeft } from '@tabler/icons-react';
import { Link, useParams } from 'react-router';
import { PageHeader } from '@/components/PageHeader';
import { QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCampaign, usePatchCampaign } from '../api';
import { MessagesTable } from '../components/MessagesTable';
import { CAMPAIGN_STATUS_OPTIONS } from '../format';
import type { Campaign } from '../types';

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
            <Title order={3}>Mensajes</Title>
            <MessagesTable campaignId={c.id} />
          </Stack>
        </>
      )}
    </QueryState>
  );
}
