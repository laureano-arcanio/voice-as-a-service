import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Code,
  Grid,
  Group,
  NavLink,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useDebouncedValue } from '@mantine/hooks';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { errorMessage } from '@/api/errors';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  previewTemplate,
  useCampaigns,
  useCreateTemplate,
  useLeads,
  usePatchTemplate,
  useTemplates,
} from '../api';
import { MESSAGE_KIND, MESSAGE_KIND_OPTIONS, TEMPLATE_VARS, fmtDate } from '../format';
import type { MessageKind, Preview, Template } from '../types';

function PreviewBox({ template }: { template: Template }) {
  const [search, setSearch] = useState('');
  const [q] = useDebouncedValue(search.trim(), 300);
  const leads = useLeads({ q: q || undefined, limit: 20 });
  const campaigns = useCampaigns();
  const [leadId, setLeadId] = useState<string | null>(null);
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [result, setResult] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!leadId) return;
    setLoading(true);
    setError(null);
    try {
      setResult(
        await previewTemplate(template.id, {
          lead_id: Number(leadId),
          campaign_id: campaignId ? Number(campaignId) : null,
          kind: template.kind,
        }),
      );
    } catch (e) {
      setResult(null);
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Vista previa
      </Title>
      <Text size="xs" c="dimmed" mb="sm">
        Muestra la versión guardada. Con un lead cuyo ★ es una persona, usa el texto tuteado.
      </Text>
      <Group align="flex-end" gap="xs" mb="sm">
        <Select
          label="Lead"
          searchable
          data={(leads.data?.items ?? []).map((l) => ({ value: String(l.id), label: l.name }))}
          value={leadId}
          onChange={setLeadId}
          onSearchChange={setSearch}
          searchValue={search}
          placeholder="Buscar…"
          style={{ flex: 1 }}
          nothingFoundMessage="Sin resultados"
        />
        <Select
          label="Campaña"
          data={(campaigns.data ?? []).map((c) => ({ value: String(c.id), label: c.slug }))}
          value={campaignId}
          onChange={setCampaignId}
          clearable
          w={160}
        />
        <Button variant="default" onClick={() => void run()} loading={loading} disabled={!leadId}>
          Ver
        </Button>
      </Group>
      {error && <Alert color="red">{error}</Alert>}
      {result && (
        <Stack gap={6}>
          <Text size="xs" c="dimmed">
            Para <span className="mono">{result.to ?? '–'}</span>
          </Text>
          <Text size="sm" fw={600}>
            {template.kind === 'follow_up' ? 'Re: <asunto del primer mail>' : result.subject}
          </Text>
          <Text size="sm" className="crm-mail">
            {result.text}
          </Text>
        </Stack>
      )}
    </Card>
  );
}

function Editor({ template, onSaved }: { template: Template | null; onSaved: (t: Template) => void }) {
  const create = useCreateTemplate();
  const patch = usePatchTemplate();
  const form = useForm({
    initialValues: {
      name: template?.name ?? '',
      kind: (template?.kind ?? 'first') as MessageKind,
      subject: template?.subject ?? '',
      body: template?.body ?? '{{saludo}}\n\n\n\n{{link}}\n\nSaludos,\nLaureano',
      body_personal: template?.body_personal ?? '',
      archived: template?.archived ?? false,
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Falta el nombre'),
      subject: (v) => (v.trim() ? null : 'Falta el asunto'),
      body: (v) => (v.trim() ? null : 'Falta el texto'),
    },
  });
  const save = form.onSubmit((v) => {
    const body = {
      ...v,
      name: v.name.trim(),
      body_personal: v.body_personal.trim() ? v.body_personal : null,
    };
    const opts = {
      onSuccess: (t: Template) => {
        notifySuccess('Plantilla guardada.');
        form.resetDirty();
        onSaved(t);
      },
      onError: (e: unknown) => notifyError(e, 'No se pudo guardar'),
    };
    if (template) patch.mutate({ id: template.id, ...body }, opts);
    else create.mutate(body, opts);
  });
  return (
    <Card withBorder>
      <form onSubmit={save}>
        <Group justify="space-between" mb="xs">
          <Title order={4}>{template ? 'Editar plantilla' : 'Nueva plantilla'}</Title>
          <Button
            size="compact-sm"
            type="submit"
            disabled={!!template && !form.isDirty()}
            loading={create.isPending || patch.isPending}
          >
            Guardar
          </Button>
        </Group>
        <Stack gap="sm">
          <Group grow>
            <TextInput label="Nombre" {...form.getInputProps('name')} />
            <Select
              label="Tipo"
              data={MESSAGE_KIND_OPTIONS}
              allowDeselect={false}
              {...form.getInputProps('kind')}
            />
          </Group>
          <TextInput
            label="Asunto"
            description={
              form.values.kind === 'follow_up'
                ? 'En un seguimiento no se usa: va "Re: <asunto del primer mail>", en el mismo hilo'
                : undefined
            }
            {...form.getInputProps('subject')}
          />
          <Textarea
            label="Texto (a ustedes)"
            description="Para casillas de área o atención"
            autosize
            minRows={7}
            maxRows={20}
            styles={{ input: { fontFamily: 'var(--mantine-font-family-monospace)', fontSize: 13 } }}
            {...form.getInputProps('body')}
          />
          <Textarea
            label="Texto tuteado (opcional)"
            description="Se usa cuando el destinatario es una persona con nombre"
            autosize
            minRows={4}
            maxRows={20}
            styles={{ input: { fontFamily: 'var(--mantine-font-family-monospace)', fontSize: 13 } }}
            {...form.getInputProps('body_personal')}
          />
          <Stack gap={2}>
            <Text className="label">Variables</Text>
            {TEMPLATE_VARS.map((v) => (
              <Text key={v.name} size="xs">
                <Code>{`{{${v.name}}}`}</Code>{' '}
                <Text span c="dimmed" inherit>
                  {v.help}
                </Text>
              </Text>
            ))}
          </Stack>
          {template && (
            <Checkbox
              label="Archivada (no aparece al armar borradores)"
              {...form.getInputProps('archived', { type: 'checkbox' })}
            />
          )}
        </Stack>
      </form>
    </Card>
  );
}

export function TemplatesPage() {
  const [showArchived, setShowArchived] = useState(false);
  const templates = useTemplates(showArchived);
  const [selected, setSelected] = useState<number | 'new' | null>(null);
  const list = templates.data ?? [];
  const current = typeof selected === 'number' ? (list.find((t) => t.id === selected) ?? null) : null;

  return (
    <>
      <PageHeader
        title="Plantillas"
        description="Textos de los mails, con variables. Cada mail guarda su texto final: cambiar una plantilla no toca lo enviado."
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={() => setSelected('new')}>
            Nueva plantilla
          </Button>
        }
      />
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder p="xs">
            <QueryState query={templates}>
              {(items) =>
                items.length === 0 ? (
                  <EmptyState>Todavía no hay plantillas.</EmptyState>
                ) : (
                  <Stack gap={2}>
                    {items.map((t) => (
                      <NavLink
                        key={t.id}
                        active={selected === t.id}
                        variant="light"
                        onClick={() => setSelected(t.id)}
                        label={t.name}
                        description={`${MESSAGE_KIND[t.kind]} · ${fmtDate(t.updated_at)}`}
                        rightSection={t.archived ? <Badge color="gray">archivada</Badge> : undefined}
                      />
                    ))}
                  </Stack>
                )
              }
            </QueryState>
            <Checkbox
              mt="sm"
              ml="xs"
              size="xs"
              label="Mostrar archivadas"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.currentTarget.checked)}
            />
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 8 }}>
          {selected === null ? (
            <Card withBorder>
              <EmptyState>Elegí una plantilla o creá una nueva.</EmptyState>
            </Card>
          ) : (
            <Stack gap="md">
              <Editor key={selected} template={current} onSaved={(t) => setSelected(t.id)} />
              {current && <PreviewBox key={current.id} template={current} />}
            </Stack>
          )}
        </Grid.Col>
      </Grid>
    </>
  );
}
