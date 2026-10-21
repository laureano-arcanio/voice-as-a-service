import {
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  MultiSelect,
  Pagination,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useDebouncedValue } from '@mantine/hooks';
import { IconPlus, IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { Dash } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { LEADS_PAGE, api, useCampaigns, useLeads, useUpsertLead } from '../api';
import { LEAD_KIND_OPTIONS, STAGE_OPTIONS, fmtAgo, fmtDate } from '../format';
import { BulkDraftsModal } from '../components/BulkDraftsModal';
import { StageBadge } from '../components/Badges';
import { useQueryClient } from '@tanstack/react-query';
import type { LeadKind, LeadSummary, Stage } from '../types';

function NewLeadModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const upsert = useUpsertLead();
  const navigate = useNavigate();
  const form = useForm({
    initialValues: {
      name: '',
      website: '',
      description: '',
      kind: '' as LeadKind | '',
      industry: '',
      email: '',
      email_label: 'atencion',
      person: '',
      person_title: '',
      source_url: '',
    },
    validate: { name: (v) => (v.trim() ? null : 'Falta el nombre') },
  });

  const submit = form.onSubmit((v) => {
    const src = v.source_url.trim() || null;
    upsert.mutate(
      {
        name: v.name.trim(),
        website: v.website.trim() || null,
        description: v.description.trim() || null,
        kind: v.kind || null,
        industry: v.industry.trim() || null,
        sources: src ? [{ url: src }] : undefined,
        people: v.person.trim()
          ? [{ name: v.person.trim(), title: v.person_title.trim() || null, source_url: src }]
          : undefined,
        contacts: v.email.trim()
          ? [
              {
                kind: 'email',
                value: v.email.trim(),
                label: v.email_label as 'persona' | 'area' | 'atencion',
                person: v.email_label === 'persona' && v.person.trim() ? v.person.trim() : null,
                is_primary: true,
                source_url: src,
              },
            ]
          : undefined,
      },
      {
        onSuccess: (r) => {
          notifySuccess(r.result === 'created' ? 'Lead creado.' : 'Ya existía: lo actualizamos.');
          form.reset();
          onClose();
          void navigate(`/leads/${r.lead.id}`);
        },
        onError: (e) => notifyError(e, 'No se pudo guardar'),
      },
    );
  });

  return (
    <Modal opened={opened} onClose={onClose} title="Nuevo lead" size="lg">
      <form onSubmit={submit}>
        <Stack gap="sm">
          <TextInput label="Empresa" required {...form.getInputProps('name')} />
          <TextInput
            label="Sitio"
            placeholder="https://empresa.com.ar"
            description="Si el dominio ya existe, se completa ese lead en vez de crear otro"
            {...form.getInputProps('website')}
          />
          <Textarea label="Rubro" autosize minRows={2} {...form.getInputProps('description')} />
          <Group grow>
            <Select label="Tipo" data={LEAD_KIND_OPTIONS} clearable {...form.getInputProps('kind')} />
            <TextInput label="Industria" {...form.getInputProps('industry')} />
          </Group>
          <Group grow>
            <TextInput label="Email ★" {...form.getInputProps('email')} />
            <Select
              label="De quién"
              data={[
                { value: 'persona', label: 'Persona' },
                { value: 'area', label: 'Área' },
                { value: 'atencion', label: 'Atención' },
              ]}
              allowDeselect={false}
              {...form.getInputProps('email_label')}
            />
          </Group>
          <Group grow>
            <TextInput label="Persona" {...form.getInputProps('person')} />
            <TextInput label="Cargo" {...form.getInputProps('person_title')} />
          </Group>
          <TextInput
            label="Fuente"
            placeholder="Página donde figura el email"
            {...form.getInputProps('source_url')}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={upsert.isPending}>
              Guardar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function StageModal({ ids, onClose }: { ids: number[]; onClose: (done: boolean) => void }) {
  const [stage, setStage] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const qc = useQueryClient();
  const run = async () => {
    if (!stage) return;
    setRunning(true);
    try {
      for (const id of ids) await api('PATCH', `/leads/${id}`, { stage });
      notifySuccess(`${ids.length} leads cambiados.`);
      onClose(true);
    } catch (e) {
      notifyError(e);
    } finally {
      setRunning(false);
      void qc.invalidateQueries({ queryKey: ['crm'] });
    }
  };
  return (
    <Modal opened={ids.length > 0} onClose={() => onClose(false)} title="Cambiar etapa">
      <Stack>
        <Select label="Etapa" data={STAGE_OPTIONS} value={stage} onChange={setStage} />
        <Group justify="flex-end">
          <Button variant="default" onClick={() => onClose(false)}>
            Cancelar
          </Button>
          <Button onClick={() => void run()} loading={running} disabled={!stage}>
            Cambiar {ids.length}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function LeadsPage() {
  const [search, setSearch] = useState('');
  const [q] = useDebouncedValue(search.trim(), 300);
  const [stages, setStages] = useState<string[]>([]);
  const [tag, setTag] = useState('');
  const [industry, setIndustry] = useState('');
  const [kind, setKind] = useState<string | null>(null);
  const [campaign, setCampaign] = useState<string | null>(null);
  const [clicks, setClicks] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [dialog, setDialog] = useState<'new' | 'drafts' | 'stage' | null>(null);
  const campaigns = useCampaigns();

  const leads = useLeads({
    q: q || undefined,
    stage: stages.join(',') || undefined,
    tag: tag.trim() || undefined,
    industry: industry.trim() || undefined,
    kind: kind ?? undefined,
    campaign_id: campaign ? Number(campaign) : undefined,
    has_clicks: clicks === null ? undefined : clicks === 'si',
    limit: LEADS_PAGE,
    offset: (page - 1) * LEADS_PAGE,
  });

  const restart =
    <T,>(set: (v: T) => void) =>
    (v: T) => {
      set(v);
      setPage(1);
      setSelected(new Set());
    };

  const items: LeadSummary[] = leads.data?.items ?? [];
  const total = leads.data?.total ?? 0;
  const all = items.length > 0 && items.every((l) => selected.has(l.id));
  const names = Object.fromEntries(items.map((l) => [l.id, l.name]));

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <>
      <PageHeader
        title="Leads"
        description={leads.data ? `${total} leads` : undefined}
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={() => setDialog('new')}>
            Nuevo lead
          </Button>
        }
      />
      <Card withBorder mb="md">
        <Group gap="xs" align="flex-end">
          <TextInput
            label="Buscar"
            placeholder="Nombre, dominio, email, rubro o #"
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(e) => {
              setSearch(e.currentTarget.value);
              setPage(1);
            }}
            w={230}
          />
          <MultiSelect
            label="Etapa"
            data={STAGE_OPTIONS}
            value={stages}
            onChange={restart(setStages)}
            clearable
            w={220}
            placeholder={stages.length ? undefined : 'Todas'}
          />
          <Select
            label="Campaña"
            data={(campaigns.data ?? []).map((c) => ({ value: String(c.id), label: c.slug }))}
            value={campaign}
            onChange={restart(setCampaign)}
            clearable
            searchable
            w={150}
            placeholder="Todas"
          />
          <Select
            label="Tipo"
            data={LEAD_KIND_OPTIONS}
            value={kind}
            onChange={restart(setKind)}
            clearable
            w={110}
            placeholder="Todos"
          />
          <TextInput
            label="Industria"
            value={industry}
            onChange={(e) => restart(setIndustry)(e.currentTarget.value)}
            w={120}
          />
          <TextInput
            label="Tag"
            value={tag}
            onChange={(e) => restart(setTag)(e.currentTarget.value)}
            w={100}
          />
          <Select
            label="Clics (GA)"
            data={[
              { value: 'si', label: 'Con clics' },
              { value: 'no', label: 'Sin clics' },
            ]}
            value={clicks}
            onChange={restart(setClicks)}
            clearable
            w={120}
            placeholder="Todos"
          />
        </Group>
      </Card>

      {selected.size > 0 && (
        <Group mb="sm" gap="xs">
          <Text size="sm" fw={600}>
            {selected.size} elegidos
          </Text>
          <Button size="compact-sm" onClick={() => setDialog('drafts')}>
            Armar borradores
          </Button>
          <Button size="compact-sm" variant="default" onClick={() => setDialog('stage')}>
            Cambiar etapa
          </Button>
          <Button size="compact-sm" variant="subtle" onClick={() => setSelected(new Set())}>
            Limpiar
          </Button>
        </Group>
      )}

      <Card withBorder p={0}>
        <QueryState query={leads}>
          {() =>
            items.length === 0 ? (
              <EmptyState>Ningún lead con estos filtros.</EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={980}>
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th w={36} pl="md">
                        <Checkbox
                          aria-label="Todos"
                          checked={all}
                          indeterminate={selected.size > 0 && !all}
                          onChange={() => setSelected(all ? new Set() : new Set(items.map((l) => l.id)))}
                        />
                      </Table.Th>
                      <Table.Th>Lead</Table.Th>
                      <Table.Th>Etapa</Table.Th>
                      <Table.Th>Email ★</Table.Th>
                      <Table.Th>Último envío</Table.Th>
                      <Table.Th>Respuesta</Table.Th>
                      <Table.Th ta="right">Clics</Table.Th>
                      <Table.Th>Próxima acción</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {items.map((l) => (
                      <Table.Tr key={l.id}>
                        <Table.Td pl="md">
                          <Checkbox
                            aria-label={`Elegir ${l.name}`}
                            checked={selected.has(l.id)}
                            onChange={() => toggle(l.id)}
                          />
                        </Table.Td>
                        <Table.Td maw={320}>
                          <Group gap={6} wrap="nowrap">
                            <Anchor component={Link} to={`/leads/${l.id}`} size="sm" fw={600}>
                              {l.name}
                            </Anchor>
                            {l.legacy_ref && (
                              <Text size="xs" c="dimmed" className="mono">
                                #{l.legacy_ref}
                              </Text>
                            )}
                            {l.do_not_contact && <Badge color="red">no contactar</Badge>}
                          </Group>
                          <Text size="xs" c="dimmed" lineClamp={1}>
                            {[l.kind, l.industry, l.city].filter(Boolean).join(' · ') || l.domain}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <StageBadge stage={l.stage as Stage} />
                        </Table.Td>
                        <Table.Td className="mono">{l.primary_email ?? <Dash />}</Table.Td>
                        <Table.Td>{l.last_out_at ? fmtAgo(l.last_out_at) : <Dash />}</Table.Td>
                        <Table.Td>{l.last_in_at ? fmtAgo(l.last_in_at) : <Dash />}</Table.Td>
                        <Table.Td ta="right" className="mono">
                          {l.ga_users || <Dash />}
                        </Table.Td>
                        <Table.Td maw={260}>
                          {l.next_action ? (
                            <>
                              <Text size="sm" lineClamp={1}>
                                {l.next_action}
                              </Text>
                              {l.next_action_at && (
                                <Text size="xs" c="dimmed">
                                  {fmtDate(l.next_action_at)}
                                </Text>
                              )}
                            </>
                          ) : (
                            <Dash />
                          )}
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
      {total > LEADS_PAGE && (
        <Group justify="center" mt="md">
          <Pagination total={Math.ceil(total / LEADS_PAGE)} value={page} onChange={setPage} />
        </Group>
      )}

      <NewLeadModal opened={dialog === 'new'} onClose={() => setDialog(null)} />
      <BulkDraftsModal
        opened={dialog === 'drafts'}
        onClose={(done) => {
          setDialog(null);
          if (done) setSelected(new Set());
        }}
        leadIds={[...selected]}
        names={names}
      />
      <StageModal
        ids={dialog === 'stage' ? [...selected] : []}
        onClose={(done) => {
          setDialog(null);
          if (done) setSelected(new Set());
        }}
      />
    </>
  );
}
