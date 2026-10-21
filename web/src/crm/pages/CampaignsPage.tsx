import {
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { Dash } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCampaigns, useCreateCampaign } from '../api';
import { CAMPAIGN_STATUS, fmtDate, todayIso } from '../format';

function NewCampaignModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const create = useCreateCampaign();
  const form = useForm({
    initialValues: {
      slug: '',
      name: '',
      segment: '',
      from_addr: '',
      started_at: todayIso() as string | null,
      notes: '',
    },
    validate: {
      slug: (v) =>
        /^[a-z0-9_-]+$/.test(v) ? null : 'Minúsculas, números, - o _ (va en el link como utm_campaign)',
      name: (v) => (v.trim() ? null : 'Falta el nombre'),
    },
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Nueva campaña">
      <form
        onSubmit={form.onSubmit((v) =>
          create.mutate(
            {
              slug: v.slug,
              name: v.name.trim(),
              segment: v.segment.trim() || null,
              from_addr: v.from_addr.trim() || null,
              started_at: v.started_at,
              notes: v.notes.trim() || null,
            },
            {
              onSuccess: () => {
                notifySuccess('Campaña creada.');
                form.reset();
                onClose();
              },
              onError: (e) => notifyError(e),
            },
          ),
        )}
      >
        <Stack gap="sm">
          <TextInput label="Nombre" required {...form.getInputProps('name')} />
          <TextInput
            label="Slug"
            description="utm_campaign de los links, único"
            required
            {...form.getInputProps('slug')}
          />
          <Textarea
            label="Segmento"
            description="A quién va y por qué"
            autosize
            minRows={2}
            {...form.getInputProps('segment')}
          />
          <TextInput
            label="Remitente"
            placeholder="Si queda vacío, el del .env (CRM_MAIL_FROM)"
            {...form.getInputProps('from_addr')}
          />
          <DateInput label="Empieza" valueFormat="D/M/YYYY" clearable {...form.getInputProps('started_at')} />
          <Textarea label="Notas" autosize minRows={2} {...form.getInputProps('notes')} />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending}>
              Crear
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

const num = (n: number | undefined) => (n ? n : <Dash />);

export function CampaignsPage() {
  const campaigns = useCampaigns();
  const [open, setOpen] = useState(false);
  return (
    <>
      <PageHeader
        title="Campañas"
        description="Cada tanda es una campaña: qué se mandó, a quién y cuándo."
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={() => setOpen(true)}>
            Nueva campaña
          </Button>
        }
      />
      <Card withBorder p={0}>
        <QueryState query={campaigns}>
          {(items) =>
            items.length === 0 ? (
              <EmptyState>Todavía no hay campañas.</EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={980}>
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th pl="md">Campaña</Table.Th>
                      <Table.Th>Empieza</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th ta="right">Leads</Table.Th>
                      <Table.Th ta="right">Primeros</Table.Th>
                      <Table.Th ta="right">Seguim.</Table.Th>
                      <Table.Th ta="right">Borradores</Table.Th>
                      <Table.Th ta="right">En cola</Table.Th>
                      <Table.Th ta="right">Rebotes</Table.Th>
                      <Table.Th ta="right">Respuestas</Table.Th>
                      <Table.Th ta="right">Usuarios GA</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {items.map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td pl="md" maw={320}>
                          <Anchor component={Link} to={`/campanas/${c.id}`} size="sm" fw={600}>
                            {c.name}
                          </Anchor>
                          <Text size="xs" c="dimmed" className="mono">
                            {c.slug}
                          </Text>
                        </Table.Td>
                        <Table.Td>{fmtDate(c.started_at)}</Table.Td>
                        <Table.Td>
                          <Badge color={CAMPAIGN_STATUS[c.status]?.color ?? 'gray'}>
                            {CAMPAIGN_STATUS[c.status]?.label ?? c.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {num(c.stats.leads)}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {num(c.stats.first_sent)}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {num(c.stats.follow_up_sent)}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {num(c.stats.drafts)}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {num(c.stats.queued)}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {c.stats.bounced ? (
                            <Text span c="red" inherit>
                              {c.stats.bounced}
                            </Text>
                          ) : (
                            <Dash />
                          )}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {num(c.stats.replies)}
                        </Table.Td>
                        <Table.Td ta="right" className="mono">
                          {num(c.stats.ga_users)}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      <NewCampaignModal opened={open} onClose={() => setOpen(false)} />
    </>
  );
}
