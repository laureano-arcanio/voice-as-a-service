import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
  Menu,
  Modal,
  SegmentedControl,
  Select,
  Stack,
  TagsInput,
  Text,
  TextInput,
  Textarea,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import {
  IconArrowLeft,
  IconChevronDown,
  IconExternalLink,
  IconMail,
  IconPlus,
  IconStar,
  IconStarFilled,
  IconTrash,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  type ActivityIn,
  useAddActivity,
  useAddContact,
  useAddPerson,
  useAddSource,
  useCampaigns,
  useCreateDraft,
  useDeleteContact,
  useDeletePerson,
  useInbound,
  useLead,
  usePatchContact,
  usePatchLead,
  useTemplates,
  useTimeline,
} from '../api';
import {
  ACTIVITY_KIND,
  CONTACT_KIND,
  CONTACT_LABEL,
  LEAD_KIND_OPTIONS,
  MESSAGE_KIND_OPTIONS,
  STAGES,
  STAGE_OPTIONS,
  fmtDate,
  fmtDateTime,
  messageLabel,
} from '../format';
import { MessageStatusBadge, StageBadge } from '../components/Badges';
import { MessageModal } from '../components/MessageModal';
import type { ContactKind, ContactLabel, Lead, Message, MessageKind, Stage, TimelineItem } from '../types';

// --- Datos ---

function LeadFields({ lead }: { lead: Lead }) {
  const patch = usePatchLead();
  const form = useForm({
    initialValues: {
      name: lead.name,
      website: lead.website ?? '',
      legal_name: lead.legal_name ?? '',
      description: lead.description ?? '',
      kind: lead.kind ?? '',
      industry: lead.industry ?? '',
      tags: lead.tags,
      country: lead.country ?? '',
      province: lead.province ?? '',
      city: lead.city ?? '',
      notes: lead.notes ?? '',
    },
  });
  const empty = (s: string) => s.trim() || null;
  const save = form.onSubmit((v) =>
    patch.mutate(
      {
        id: lead.id,
        name: v.name.trim(),
        website: empty(v.website),
        legal_name: empty(v.legal_name),
        description: empty(v.description),
        kind: (v.kind || null) as Lead['kind'],
        industry: empty(v.industry),
        tags: v.tags,
        country: empty(v.country),
        province: empty(v.province),
        city: empty(v.city),
        notes: empty(v.notes),
      },
      {
        onSuccess: () => {
          notifySuccess('Guardado.');
          form.resetDirty();
        },
        onError: (e) => notifyError(e, 'No se pudo guardar'),
      },
    ),
  );
  return (
    <Card withBorder>
      <form onSubmit={save}>
        <Group justify="space-between" mb="xs">
          <Title order={4}>Datos</Title>
          <Button size="compact-sm" type="submit" disabled={!form.isDirty()} loading={patch.isPending}>
            Guardar
          </Button>
        </Group>
        <Stack gap="xs">
          <TextInput label="Empresa" {...form.getInputProps('name')} />
          <TextInput
            label="Sitio"
            {...form.getInputProps('website')}
            rightSection={
              lead.website ? (
                <ActionIcon
                  component="a"
                  href={lead.website}
                  target="_blank"
                  rel="noreferrer"
                  variant="subtle"
                  aria-label="Abrir sitio"
                >
                  <IconExternalLink size={16} />
                </ActionIcon>
              ) : undefined
            }
          />
          <TextInput label="Razón social" {...form.getInputProps('legal_name')} />
          <Textarea label="Rubro" autosize minRows={2} {...form.getInputProps('description')} />
          <Group grow>
            <Select label="Tipo" data={LEAD_KIND_OPTIONS} clearable {...form.getInputProps('kind')} />
            <TextInput label="Industria" {...form.getInputProps('industry')} />
          </Group>
          <TagsInput label="Tags" {...form.getInputProps('tags')} />
          <Group grow>
            <TextInput label="Ciudad" {...form.getInputProps('city')} />
            <TextInput label="Provincia" {...form.getInputProps('province')} />
            <TextInput label="País" {...form.getInputProps('country')} />
          </Group>
          <Textarea label="Notas" autosize minRows={2} maxRows={10} {...form.getInputProps('notes')} />
          <Text size="xs" c="dimmed">
            Slug (utm_content): <span className="mono">{lead.slug}</span> · alta {fmtDate(lead.created_at)}{' '}
            por {lead.created_by}
            {lead.legacy_ref ? ` · #${lead.legacy_ref} del seguimiento viejo` : ''}
          </Text>
        </Stack>
      </form>
    </Card>
  );
}

function StageCard({ lead }: { lead: Lead }) {
  const patch = usePatchLead();
  const [action, setAction] = useState(lead.next_action ?? '');
  const [at, setAt] = useState<string | null>(lead.next_action_at);
  const dirty = action !== (lead.next_action ?? '') || at !== lead.next_action_at;
  const run = (body: Parameters<typeof patch.mutate>[0], msg: string) =>
    patch.mutate(body, { onSuccess: () => notifySuccess(msg), onError: (e) => notifyError(e) });
  return (
    <Card withBorder>
      <Stack gap="xs">
        <Select
          label="Etapa"
          data={STAGE_OPTIONS}
          value={lead.stage}
          allowDeselect={false}
          onChange={(v) =>
            v &&
            v !== lead.stage &&
            run({ id: lead.id, stage: v as Stage }, `Etapa: ${STAGES[v as Stage].label}.`)
          }
          description={`Desde ${fmtDate(lead.stage_changed_at)}`}
        />
        <Textarea
          label="Próxima acción"
          autosize
          minRows={1}
          value={action}
          onChange={(e) => setAction(e.currentTarget.value)}
        />
        <Group align="flex-end" gap="xs">
          <DateInput
            label="Para el"
            value={at}
            onChange={setAt}
            clearable
            valueFormat="D/M/YYYY"
            style={{ flex: 1 }}
          />
          <Button
            variant="default"
            disabled={!dirty}
            loading={patch.isPending}
            onClick={() =>
              run(
                { id: lead.id, next_action: action.trim() || null, next_action_at: at },
                'Próxima acción guardada.',
              )
            }
          >
            Guardar
          </Button>
        </Group>
        <Checkbox
          label="No contactar"
          checked={lead.do_not_contact}
          onChange={(e) =>
            run(
              { id: lead.id, do_not_contact: e.currentTarget.checked },
              e.currentTarget.checked ? 'Marcado: no contactar.' : 'Se puede contactar.',
            )
          }
        />
      </Stack>
    </Card>
  );
}

// --- Personas, contactos y fuentes ---

function PeopleCard({ lead }: { lead: Lead }) {
  const [open, setOpen] = useState(false);
  const del = useDeletePerson();
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Personas</Title>
        <Button
          size="compact-sm"
          variant="subtle"
          leftSection={<IconPlus size={14} />}
          onClick={() => setOpen(true)}
        >
          Agregar
        </Button>
      </Group>
      {lead.people.length === 0 ? (
        <EmptyState>Sin personas.</EmptyState>
      ) : (
        <Stack gap="xs">
          {lead.people.map((p) => (
            <Group key={p.id} justify="space-between" wrap="nowrap" align="flex-start">
              <Stack gap={0} style={{ minWidth: 0 }}>
                <Group gap={6}>
                  <Text size="sm" fw={600}>
                    {p.name}
                  </Text>
                  {p.is_decision_maker && <Badge color="blue">decide</Badge>}
                </Group>
                <Text size="xs" c="dimmed">
                  {p.title ?? '–'}
                  {p.linkedin_url && (
                    <>
                      {' · '}
                      <Anchor href={p.linkedin_url} target="_blank" rel="noreferrer" size="xs">
                        LinkedIn
                      </Anchor>
                    </>
                  )}
                </Text>
              </Stack>
              <ActionIcon
                variant="subtle"
                color="red"
                aria-label={`Borrar a ${p.name}`}
                onClick={async () => {
                  if (
                    await confirmAction({
                      title: `Borrar a ${p.name}`,
                      message: 'Sus contactos quedan, sin persona.',
                      danger: true,
                      confirmLabel: 'Borrar',
                    })
                  )
                    del.mutate(p.id, { onError: (e) => notifyError(e) });
                }}
              >
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}
        </Stack>
      )}
      <PersonModal leadId={lead.id} opened={open} onClose={() => setOpen(false)} />
    </Card>
  );
}

function PersonModal({ leadId, opened, onClose }: { leadId: number; opened: boolean; onClose: () => void }) {
  const add = useAddPerson();
  const form = useForm({
    initialValues: { name: '', title: '', is_decision_maker: false, linkedin_url: '', source_url: '' },
    validate: { name: (v) => (v.trim() ? null : 'Falta el nombre') },
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Agregar persona">
      <form
        onSubmit={form.onSubmit((v) =>
          add.mutate(
            {
              leadId,
              name: v.name.trim(),
              title: v.title.trim() || null,
              is_decision_maker: v.is_decision_maker,
              linkedin_url: v.linkedin_url.trim() || null,
              source_url: v.source_url.trim() || null,
            },
            {
              onSuccess: () => {
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
          <TextInput label="Cargo" {...form.getInputProps('title')} />
          <Checkbox
            label="Decide (dueño, socio, gerente)"
            {...form.getInputProps('is_decision_maker', { type: 'checkbox' })}
          />
          <TextInput label="LinkedIn" {...form.getInputProps('linkedin_url')} />
          <TextInput label="Fuente" placeholder="Página donde figura" {...form.getInputProps('source_url')} />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={add.isPending}>
              Agregar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function ContactsCard({ lead }: { lead: Lead }) {
  const [open, setOpen] = useState(false);
  const patch = usePatchContact();
  const del = useDeleteContact();
  const people = Object.fromEntries(lead.people.map((p) => [p.id, p.name]));
  const sources = Object.fromEntries(lead.sources.map((s) => [s.id, s.url]));
  const link = (kind: ContactKind, value: string) =>
    kind === 'linkedin' || kind === 'form' ? value : kind === 'email' ? `mailto:${value}` : null;
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Contactos</Title>
        <Button
          size="compact-sm"
          variant="subtle"
          leftSection={<IconPlus size={14} />}
          onClick={() => setOpen(true)}
        >
          Agregar
        </Button>
      </Group>
      {lead.contacts.length === 0 ? (
        <EmptyState>Sin contactos.</EmptyState>
      ) : (
        <Stack gap="xs">
          {lead.contacts.map((c) => {
            const href = link(c.kind, c.value);
            return (
              <Group key={c.id} justify="space-between" wrap="nowrap" align="flex-start">
                <Group gap={6} wrap="nowrap" align="flex-start" style={{ minWidth: 0 }}>
                  <Tooltip label={c.is_primary ? 'Destinatario (★)' : 'Marcar como destinatario'} withArrow>
                    <ActionIcon
                      variant="subtle"
                      color={c.is_primary ? 'blue' : 'gray'}
                      aria-label="Destinatario"
                      onClick={() =>
                        !c.is_primary &&
                        patch.mutate({ id: c.id, is_primary: true }, { onError: (e) => notifyError(e) })
                      }
                    >
                      {c.is_primary ? <IconStarFilled size={16} /> : <IconStar size={16} />}
                    </ActionIcon>
                  </Tooltip>
                  <Stack gap={0} style={{ minWidth: 0 }}>
                    <Text size="sm" className="mono" style={{ overflowWrap: 'anywhere' }}>
                      {href ? (
                        <Anchor href={href} target="_blank" rel="noreferrer" inherit>
                          {c.value}
                        </Anchor>
                      ) : (
                        c.value
                      )}
                    </Text>
                    <Group gap={6}>
                      <Text size="xs" c="dimmed">
                        {CONTACT_KIND[c.kind]}
                        {c.label ? ` · ${CONTACT_LABEL[c.label] ?? c.label}` : ''}
                        {c.person_id ? ` · ${people[c.person_id] ?? ''}` : ''}
                      </Text>
                      {c.status !== 'ok' && (
                        <Badge color={c.status === 'bounced' ? 'red' : 'yellow'}>
                          {c.status === 'bounced' ? 'rebotó' : c.status}
                        </Badge>
                      )}
                      {c.source_id && sources[c.source_id] && (
                        <Anchor href={sources[c.source_id]} target="_blank" rel="noreferrer" size="xs">
                          fuente
                        </Anchor>
                      )}
                    </Group>
                  </Stack>
                </Group>
                <ActionIcon
                  variant="subtle"
                  color="red"
                  aria-label={`Borrar ${c.value}`}
                  onClick={async () => {
                    if (
                      await confirmAction({
                        title: `Borrar ${c.value}`,
                        message: 'Los mails ya enviados quedan en el historial.',
                        danger: true,
                        confirmLabel: 'Borrar',
                      })
                    )
                      del.mutate(c.id, { onError: (e) => notifyError(e) });
                  }}
                >
                  <IconTrash size={16} />
                </ActionIcon>
              </Group>
            );
          })}
        </Stack>
      )}
      <ContactModal lead={lead} opened={open} onClose={() => setOpen(false)} />
    </Card>
  );
}

function ContactModal({ lead, opened, onClose }: { lead: Lead; opened: boolean; onClose: () => void }) {
  const add = useAddContact();
  const form = useForm({
    initialValues: {
      kind: 'email' as ContactKind,
      value: '',
      label: '' as ContactLabel | '',
      person: '',
      is_primary: false,
      source_url: '',
    },
    validate: { value: (v) => (v.trim() ? null : 'Falta el valor') },
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Agregar contacto">
      <form
        onSubmit={form.onSubmit((v) =>
          add.mutate(
            {
              leadId: lead.id,
              kind: v.kind,
              value: v.value.trim(),
              label: v.label || null,
              person: v.person || null,
              is_primary: v.is_primary,
              source_url: v.source_url.trim() || null,
            },
            {
              onSuccess: () => {
                form.reset();
                onClose();
              },
              onError: (e) => notifyError(e),
            },
          ),
        )}
      >
        <Stack gap="sm">
          <Select
            label="Tipo"
            data={Object.entries(CONTACT_KIND).map(([value, label]) => ({ value, label }))}
            allowDeselect={false}
            {...form.getInputProps('kind')}
          />
          <TextInput label="Valor" required {...form.getInputProps('value')} />
          <Group grow>
            <Select
              label="De quién"
              data={[
                { value: 'persona', label: 'Persona' },
                { value: 'area', label: 'Área' },
                { value: 'atencion', label: 'Atención' },
              ]}
              clearable
              {...form.getInputProps('label')}
            />
            <Select
              label="Persona"
              data={lead.people.map((p) => p.name)}
              clearable
              {...form.getInputProps('person')}
            />
          </Group>
          <TextInput label="Fuente" placeholder="Página donde figura" {...form.getInputProps('source_url')} />
          <Checkbox label="Destinatario (★)" {...form.getInputProps('is_primary', { type: 'checkbox' })} />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={add.isPending}>
              Agregar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function SourcesCard({ lead }: { lead: Lead }) {
  const add = useAddSource();
  const [url, setUrl] = useState('');
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Fuentes
      </Title>
      <Stack gap={6}>
        {lead.sources.length === 0 && <EmptyState>Sin fuentes.</EmptyState>}
        {lead.sources.map((s) => (
          <Stack key={s.id} gap={0}>
            <Anchor
              href={s.url}
              target="_blank"
              rel="noreferrer"
              size="sm"
              style={{ overflowWrap: 'anywhere' }}
            >
              {s.title || s.url}
            </Anchor>
            {(s.seen_at || s.note) && (
              <Text size="xs" c="dimmed">
                {[s.seen_at && `vista ${fmtDate(s.seen_at)}`, s.note].filter(Boolean).join(' · ')}
              </Text>
            )}
          </Stack>
        ))}
        <Group gap="xs" wrap="nowrap">
          <TextInput
            size="xs"
            placeholder="https://…"
            value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            style={{ flex: 1 }}
          />
          <Button
            size="compact-sm"
            variant="default"
            disabled={!url.trim()}
            loading={add.isPending}
            onClick={() =>
              add.mutate(
                { leadId: lead.id, url: url.trim() },
                { onSuccess: () => setUrl(''), onError: (e) => notifyError(e) },
              )
            }
          >
            Sumar
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

// --- Acciones ---

function ActivityModal({
  leadId,
  kind,
  onClose,
}: {
  leadId: number;
  kind: ActivityIn['kind'] | null;
  onClose: () => void;
}) {
  const add = useAddActivity();
  const [text, setText] = useState('');
  const [due, setDue] = useState<string | null>(null);
  const close = () => {
    setText('');
    setDue(null);
    onClose();
  };
  return (
    <Modal opened={!!kind} onClose={close} title={kind ? ACTIVITY_KIND[kind] : ''}>
      <Stack gap="sm">
        <Textarea
          label={kind === 'task' ? 'Qué hay que hacer' : 'Qué pasó'}
          autosize
          minRows={3}
          value={text}
          onChange={(e) => setText(e.currentTarget.value)}
          data-autofocus
        />
        {kind === 'task' && (
          <DateInput label="Para el" value={due} onChange={setDue} clearable valueFormat="D/M/YYYY" />
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={close}>
            Cancelar
          </Button>
          <Button
            disabled={!text.trim()}
            loading={add.isPending}
            onClick={() =>
              kind &&
              add.mutate(
                { leadId, kind, text: text.trim(), due_at: kind === 'task' ? due : null },
                { onSuccess: () => close(), onError: (e) => notifyError(e) },
              )
            }
          >
            Guardar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function InboundModal({ lead, opened, onClose }: { lead: Lead; opened: boolean; onClose: () => void }) {
  const inbound = useInbound();
  const form = useForm({
    initialValues: { from_addr: lead.primary_email ?? '', subject: '', text: '', auto_reply: false },
    validate: { from_addr: (v) => (v.trim() ? null : 'Falta quién respondió') },
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Registrar respuesta" size="lg">
      <form
        onSubmit={form.onSubmit((v) =>
          inbound.mutate(
            {
              leadId: lead.id,
              from_addr: v.from_addr.trim(),
              subject: v.subject,
              text: v.text,
              auto_reply: v.auto_reply,
            },
            {
              onSuccess: () => {
                notifySuccess(
                  v.auto_reply ? 'Autorespuesta guardada.' : 'Respuesta registrada: etapa Respondió.',
                );
                form.reset();
                onClose();
              },
              onError: (e) => notifyError(e),
            },
          ),
        )}
      >
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            Cambia la etapa a Respondió y cancela lo que estaba por salir a este lead.
          </Text>
          <TextInput label="De" required {...form.getInputProps('from_addr')} />
          <TextInput label="Asunto" {...form.getInputProps('subject')} />
          <Textarea label="Texto" autosize minRows={5} maxRows={16} {...form.getInputProps('text')} />
          <Checkbox
            label="Es una autorespuesta (fuera de la oficina): no cambia la etapa"
            {...form.getInputProps('auto_reply', { type: 'checkbox' })}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={inbound.isPending}>
              Registrar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function ComposeModal({ lead, opened, onClose }: { lead: Lead; opened: boolean; onClose: () => void }) {
  const campaigns = useCampaigns();
  const templates = useTemplates();
  const create = useCreateDraft();
  const [mode, setMode] = useState<'template' | 'free'>('template');
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [kind, setKind] = useState<MessageKind>('first');
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [text, setText] = useState('');
  const emails = lead.contacts.filter((c) => c.kind === 'email').map((c) => c.value);

  const submit = () =>
    create.mutate(
      {
        lead_id: lead.id,
        campaign_id: campaignId ? Number(campaignId) : null,
        kind,
        template_id: mode === 'template' && templateId ? Number(templateId) : null,
        subject: mode === 'free' ? subject : null,
        text: mode === 'free' ? text : null,
        to: to || null,
      },
      {
        onSuccess: () => {
          notifySuccess('Borrador creado: aprobalo en Hoy o en la línea de tiempo.');
          onClose();
        },
        onError: (e) => notifyError(e, 'No se pudo crear'),
      },
    );

  return (
    <Modal opened={opened} onClose={onClose} title="Redactar mail" size="lg">
      <Stack gap="sm">
        <Text size="xs" c="dimmed">
          Queda como borrador: no sale hasta que lo apruebes.
        </Text>
        <Group grow>
          <Select
            label="Campaña"
            data={(campaigns.data ?? []).map((c) => ({ value: String(c.id), label: c.slug }))}
            value={campaignId}
            onChange={setCampaignId}
            clearable
            searchable
            placeholder="Sin campaña"
          />
          <Select
            label="Tipo"
            data={MESSAGE_KIND_OPTIONS}
            value={kind}
            onChange={(v) => setKind((v as MessageKind) ?? 'first')}
            allowDeselect={false}
          />
        </Group>
        <Select
          label="Para"
          data={emails}
          value={to || null}
          onChange={(v) => setTo(v ?? '')}
          clearable
          placeholder={kind === 'follow_up' ? 'La dirección del hilo' : 'El destinatario (★)'}
        />
        <SegmentedControl
          value={mode}
          onChange={(v) => setMode(v as 'template' | 'free')}
          data={[
            { value: 'template', label: 'Con plantilla' },
            { value: 'free', label: 'Texto libre' },
          ]}
        />
        {mode === 'template' ? (
          <Select
            label="Plantilla"
            data={(templates.data ?? [])
              .filter((t) => t.kind === kind || t.kind === 'other')
              .map((t) => ({ value: String(t.id), label: t.name }))}
            value={templateId}
            onChange={setTemplateId}
            searchable
          />
        ) : (
          <>
            <TextInput
              label="Asunto"
              value={subject}
              onChange={(e) => setSubject(e.currentTarget.value)}
              description={
                kind === 'follow_up' ? 'Se reemplaza por "Re: <asunto del primer mail>"' : undefined
              }
            />
            <Textarea
              label="Texto"
              autosize
              minRows={6}
              value={text}
              onChange={(e) => setText(e.currentTarget.value)}
            />
          </>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={submit}
            loading={create.isPending}
            disabled={mode === 'template' ? !templateId : !subject.trim() || !text.trim()}
          >
            Crear borrador
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

// --- Linea de tiempo ---

const DOT: Record<string, string> = {
  out: 'var(--mantine-color-blue-6)',
  in: 'var(--mantine-color-green-6)',
  visit: 'var(--mantine-color-yellow-6)',
  stage_change: 'var(--mantine-color-gray-5)',
  activity: 'var(--mantine-color-gray-7)',
};

function TimelineEntry({ item, onOpen }: { item: TimelineItem; onOpen: (m: Message) => void }) {
  if (item.type === 'message') {
    const m = item.data;
    return (
      <div className="crm-timeline-item" style={{ ['--dot' as string]: DOT[m.direction] }}>
        <UnstyledButton onClick={() => onOpen(m)} w="100%">
          <Group gap={6} wrap="wrap">
            <Text size="sm" fw={600}>
              {messageLabel(m)}
            </Text>
            <MessageStatusBadge status={m.status} error={m.error} />
            {m.campaign_slug && (
              <Text size="xs" c="dimmed" className="mono">
                {m.campaign_slug}
              </Text>
            )}
            <Text size="xs" c="dimmed" ml="auto">
              {fmtDateTime(item.at)}
            </Text>
          </Group>
          <Text size="sm" lineClamp={1}>
            {m.subject}
          </Text>
          <Text size="xs" c="dimmed" className="mono">
            {m.direction === 'in' ? `de ${m.from_addr}` : `a ${m.to_addr}`}
          </Text>
        </UnstyledButton>
      </div>
    );
  }
  if (item.type === 'visit') {
    const v = item.data;
    return (
      <div className="crm-timeline-item" style={{ ['--dot' as string]: DOT.visit }}>
        <Group gap={6}>
          <Text size="sm" fw={600}>
            Visitó la web
          </Text>
          <Text size="xs" c="dimmed" className="mono">
            {v.utm_campaign}
          </Text>
          <Text size="xs" c="dimmed" ml="auto">
            {fmtDate(v.date)}
          </Text>
        </Group>
        <Text size="xs" c="dimmed">
          {v.active_users} usuarios · {v.sessions} sesiones · {v.events} eventos
          {v.follow_up ? ' · desde el seguimiento' : ''}
        </Text>
      </div>
    );
  }
  const a = item.data;
  const isStage = a.kind === 'stage_change';
  return (
    <div
      className="crm-timeline-item"
      style={{ ['--dot' as string]: isStage ? DOT.stage_change : DOT.activity }}
    >
      <Group gap={6}>
        <Text size="sm" fw={600}>
          {ACTIVITY_KIND[a.kind] ?? a.kind}
        </Text>
        {isStage && typeof a.data.to === 'string' && <StageBadge stage={a.data.to as Stage} />}
        {a.kind === 'task' && (
          <Badge color={a.done ? 'green' : 'yellow'}>{a.done ? 'hecha' : `para ${fmtDate(a.due_at)}`}</Badge>
        )}
        <Text size="xs" c="dimmed" ml="auto">
          {fmtDateTime(item.at)} · {a.created_by}
        </Text>
      </Group>
      {!isStage && (
        <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
          {a.text}
        </Text>
      )}
    </div>
  );
}

function Timeline({ lead }: { lead: Lead }) {
  const timeline = useTimeline(lead.id);
  const [open, setOpen] = useState<Message | null>(null);
  const [activity, setActivity] = useState<ActivityIn['kind'] | null>(null);
  const [dialog, setDialog] = useState<'inbound' | 'compose' | null>(null);
  return (
    <Card withBorder>
      <Group justify="space-between" mb="md">
        <Title order={4}>Línea de tiempo</Title>
        <Group gap="xs">
          <Button size="compact-sm" leftSection={<IconMail size={14} />} onClick={() => setDialog('compose')}>
            Redactar mail
          </Button>
          <Button size="compact-sm" variant="default" onClick={() => setDialog('inbound')}>
            Registrar respuesta
          </Button>
          <Menu position="bottom-end">
            <Menu.Target>
              <Button size="compact-sm" variant="default" rightSection={<IconChevronDown size={14} />}>
                Anotar
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              {(['note', 'call', 'meeting', 'linkedin', 'task'] as const).map((k) => (
                <Menu.Item key={k} onClick={() => setActivity(k)}>
                  {ACTIVITY_KIND[k]}
                </Menu.Item>
              ))}
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>
      <QueryState query={timeline}>
        {(items) =>
          items.length === 0 ? (
            <EmptyState>Todavía no pasó nada con este lead.</EmptyState>
          ) : (
            <Stack gap="md">
              {items.map((it) => (
                <TimelineEntry
                  key={`${it.type}-${'id' in it.data ? it.data.id : it.data.date + it.data.utm_campaign}`}
                  item={it}
                  onOpen={setOpen}
                />
              ))}
            </Stack>
          )
        }
      </QueryState>
      <MessageModal message={open} onClose={() => setOpen(null)} />
      <ActivityModal leadId={lead.id} kind={activity} onClose={() => setActivity(null)} />
      <InboundModal lead={lead} opened={dialog === 'inbound'} onClose={() => setDialog(null)} />
      <ComposeModal lead={lead} opened={dialog === 'compose'} onClose={() => setDialog(null)} />
    </Card>
  );
}

export function LeadPage() {
  const id = Number(useParams().id);
  const lead = useLead(id);
  return (
    <QueryState query={lead}>
      {(l) => (
        <>
          <PageHeader
            title={l.name}
            description={
              <>
                {l.primary_email ? <span className="mono">{l.primary_email}</span> : 'Sin email'}
                {l.ga_users ? ` · ${l.ga_users} usuarios desde los mails` : ''}
              </>
            }
            above={
              <Anchor component={Link} to="/leads" size="sm">
                <Group gap={4}>
                  <IconArrowLeft size={14} /> Leads
                </Group>
              </Anchor>
            }
            actions={
              <Group gap="xs">
                <StageBadge stage={l.stage} />
                {l.do_not_contact && <Badge color="red">no contactar</Badge>}
                {l.website ? (
                  <Anchor href={l.website} target="_blank" rel="noreferrer" size="sm">
                    {l.domain}
                  </Anchor>
                ) : (
                  <Dash />
                )}
              </Group>
            }
          />
          <Grid gutter="md">
            <Grid.Col span={{ base: 12, lg: 7 }}>
              <Timeline lead={l} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, lg: 5 }}>
              <Stack gap="md">
                <StageCard key={`${l.stage}-${l.next_action}-${l.next_action_at}`} lead={l} />
                <ContactsCard lead={l} />
                <PeopleCard lead={l} />
                <LeadFields key={l.id} lead={l} />
                <SourcesCard lead={l} />
              </Stack>
            </Grid.Col>
          </Grid>
        </>
      )}
    </QueryState>
  );
}
