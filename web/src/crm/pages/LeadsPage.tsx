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
  Popover,
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
import {
  LEADS_PAGE,
  api,
  useApprove,
  useCampaigns,
  useCancelMessages,
  useLeads,
  useMessages,
  useUpsertLead,
} from '../api';
import { LEAD_KIND_OPTIONS, STAGE_OPTIONS, fmtAgo, fmtDate } from '../format';
import { BulkDraftsModal } from '../components/BulkDraftsModal';
import { StageBadge } from '../components/Badges';
import { MessageModal } from '../components/MessageModal';
import { useQueryClient } from '@tanstack/react-query';
import type { LeadFilters } from '../api';
import type { LeadKind, LeadSummary, Message, Stage } from '../types';

const PENDING_OPTIONS = [
  { value: 'draft', label: 'Con borrador' },
  { value: 'follow_up', label: 'Le toca seguimiento' },
  { value: 'queued', label: 'En cola' },
];

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

/** Lo que el lead tiene pendiente: borrador (abre la vista previa), en cola o seguimiento vencido. */
function Pending({ lead, onOpen }: { lead: LeadSummary; onOpen: (id: number) => void }) {
  if (!lead.draft_ids.length && !lead.queued && !lead.follow_up_step) return <Dash />;
  return (
    <Group gap={4} wrap="nowrap">
      {lead.draft_ids.map((id) => (
        <Badge key={id} color="gray" style={{ cursor: 'pointer' }} onClick={() => onOpen(id)}>
          Borrador
        </Badge>
      ))}
      {lead.queued > 0 && <Badge color="blue">En cola</Badge>}
      {lead.follow_up_step && <Badge color="yellow">Toca seguimiento {lead.follow_up_step}</Badge>}
    </Group>
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
  const [pending, setPending] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  // Por id, con el lead: la seleccion sobrevive al cambio de pagina y las acciones saben que tiene pendiente
  const [selected, setSelected] = useState<Map<number, LeadSummary>>(new Map());
  const [dialog, setDialog] = useState<'new' | 'drafts' | 'followups' | 'stage' | null>(null);
  const [preview, setPreview] = useState<Message | null>(null);
  const campaigns = useCampaigns();
  const approve = useApprove();
  const discard = useCancelMessages();
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  // Los borradores, para verlos antes de aprobar (son pocos: los que esperan aprobacion)
  const drafts = useMessages({ status: 'draft', limit: 500 });
  const draftById = new Map((drafts.data?.items ?? []).map((m) => [m.id, m]));

  const leads = useLeads({
    q: q || undefined,
    stage: stages.join(',') || undefined,
    tag: tag.trim() || undefined,
    industry: industry.trim() || undefined,
    kind: kind ?? undefined,
    campaign_id: campaign ? Number(campaign) : undefined,
    has_clicks: clicks === null ? undefined : clicks === 'si',
    pending: (pending as LeadFilters['pending']) ?? undefined,
    limit: LEADS_PAGE,
    offset: (page - 1) * LEADS_PAGE,
  });

  const restart =
    <T,>(set: (v: T) => void) =>
    (v: T) => {
      set(v);
      setPage(1);
      setSelected(new Map());
    };

  const items: LeadSummary[] = leads.data?.items ?? [];
  const total = leads.data?.total ?? 0;
  const all = items.length > 0 && items.every((l) => selected.has(l.id));
  const chosen = [...selected.values()];
  const names = Object.fromEntries(chosen.map((l) => [l.id, l.name]));
  const draftIds = chosen.flatMap((l) => l.draft_ids);
  const dueIds = chosen.filter((l) => l.follow_up_step).map((l) => l.id);

  const toggle = (l: LeadSummary) =>
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(l.id)) next.delete(l.id);
      else next.set(l.id, l);
      return next;
    });
  const toggleAll = () =>
    setSelected((prev) => {
      const next = new Map(prev);
      for (const l of items) {
        if (all) next.delete(l.id);
        else next.set(l.id, l);
      }
      return next;
    });

  const approveDrafts = () =>
    approve.mutate(draftIds, {
      onSuccess: (r) => {
        notifySuccess(`${r.length} aprobados: salen por la cola (uno cada ~2 min, en horario hábil).`);
        setSelected(new Map());
      },
      onError: (e) => notifyError(e, 'No se pudo aprobar'),
    });

  const discardDrafts = () =>
    discard.mutate(draftIds, {
      onSuccess: (r) => {
        notifySuccess(`${r.length} borradores descartados.`);
        setConfirmDiscard(false);
        setSelected(new Map());
      },
      onError: (e) => notifyError(e, 'No se pudieron descartar'),
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
          <Select
            label="Pendiente"
            data={PENDING_OPTIONS}
            value={pending}
            onChange={restart(setPending)}
            clearable
            w={170}
            placeholder="Todos"
          />
        </Group>
      </Card>

      {selected.size > 0 && (
        <Group mb="sm" gap="xs">
          <Text size="sm" fw={600}>
            {selected.size} elegidos
          </Text>
          <Button
            size="compact-sm"
            disabled={draftIds.length === 0}
            loading={approve.isPending}
            onClick={approveDrafts}
          >
            Aprobar borradores ({draftIds.length})
          </Button>
          <Popover opened={confirmDiscard} onChange={setConfirmDiscard} withArrow shadow="md">
            <Popover.Target>
              <Button
                size="compact-sm"
                variant="default"
                color="red"
                disabled={draftIds.length === 0}
                onClick={() => setConfirmDiscard((o) => !o)}
              >
                Descartar borradores ({draftIds.length})
              </Button>
            </Popover.Target>
            <Popover.Dropdown>
              <Stack gap="xs" maw={260}>
                <Text size="sm">
                  Se descartan {draftIds.length} borradores. Si le toca seguimiento, el lead vuelve a aparecer
                  para armarlo de nuevo.
                </Text>
                <Group justify="flex-end" gap="xs">
                  <Button size="compact-sm" variant="default" onClick={() => setConfirmDiscard(false)}>
                    Volver
                  </Button>
                  <Button size="compact-sm" color="red" loading={discard.isPending} onClick={discardDrafts}>
                    Descartar
                  </Button>
                </Group>
              </Stack>
            </Popover.Dropdown>
          </Popover>
          <Button
            size="compact-sm"
            variant="default"
            disabled={dueIds.length === 0}
            onClick={() => setDialog('followups')}
          >
            Armar seguimientos ({dueIds.length})
          </Button>
          <Button size="compact-sm" variant="default" onClick={() => setDialog('drafts')}>
            Armar primer mail
          </Button>
          <Button size="compact-sm" variant="default" onClick={() => setDialog('stage')}>
            Cambiar etapa
          </Button>
          <Button size="compact-sm" variant="subtle" onClick={() => setSelected(new Map())}>
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
                          onChange={toggleAll}
                        />
                      </Table.Th>
                      <Table.Th>Lead</Table.Th>
                      <Table.Th>Etapa</Table.Th>
                      <Table.Th>Pendiente</Table.Th>
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
                            onChange={() => toggle(l)}
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
                        <Table.Td>
                          <Pending lead={l} onOpen={(id) => setPreview(draftById.get(id) ?? null)} />
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
          if (done) setSelected(new Map());
        }}
        leadIds={[...selected.keys()]}
        names={names}
      />
      <BulkDraftsModal
        opened={dialog === 'followups'}
        onClose={(done) => {
          setDialog(null);
          if (done) setSelected(new Map());
        }}
        leadIds={dueIds}
        followUps
        names={names}
      />
      <StageModal
        ids={dialog === 'stage' ? [...selected.keys()] : []}
        onClose={(done) => {
          setDialog(null);
          if (done) setSelected(new Map());
        }}
      />
      <MessageModal message={preview} onClose={() => setPreview(null)} />
    </>
  );
}
