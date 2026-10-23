import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Chip,
  Group,
  Menu,
  Modal,
  SegmentedControl,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
  Tooltip,
} from '@mantine/core';
import { DateInput, TimeInput } from '@mantine/dates';
import { IconBell, IconCalendarEvent, IconDots, IconPhone } from '@tabler/icons-react';
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { EmptyState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  useCancelReminder,
  useCreateReminder,
  usePatchReminder,
  useReminderDone,
  useReminders,
} from '../api';
import { parseUtc, todayIso, toIsoDay } from '../format';
import type { Lead, Person, Reminder, ReminderKind } from '../types';

const KIND_LABEL: Record<ReminderKind, string> = { reminder: 'Recordatorio', meeting: 'Reunión' };
const DURATIONS = ['15', '30', '45', '60', '90'].map((v) => ({ value: v, label: `${v} min` }));
const WEEKDAYS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];

const pad = (n: number) => String(n).padStart(2, '0');
const hhmm = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

function addDays(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return toIsoDay(d)!;
}

/** El próximo lunes (si hoy es lunes, el de la semana que viene). */
function nextMonday(): string {
  const d = new Date();
  return addDays((8 - d.getDay()) % 7 || 7);
}

const QUICK = [
  { label: 'Hoy', day: () => todayIso() },
  { label: 'Mañana', day: () => addDays(1) },
  { label: 'El lunes', day: nextMonday },
  { label: 'En una semana', day: () => addDays(7) },
];

/** "hoy 10:00", "mañana 11:30", "lun 27/10 11:00". */
function fmtWhen(iso: string): string {
  const d = parseUtc(iso)!;
  const day = toIsoDay(d);
  const label =
    day === todayIso()
      ? 'hoy'
      : day === addDays(1)
        ? 'mañana'
        : `${WEEKDAYS[d.getDay()]} ${pad(d.getDate())}/${pad(d.getMonth() + 1)}`;
  return `${label} ${hhmm(d)}`;
}

function isOverdue(r: Reminder): boolean {
  return r.status === 'pending' && parseUtc(r.starts_at)!.getTime() < Date.now();
}

/** Crear (con `leadId`) o reprogramar (con `reminder`) un recordatorio o una reunión. */
export function ReminderModal({
  opened,
  onClose,
  leadId,
  people = [],
  kind: initialKind = 'reminder',
  reminder,
}: {
  opened: boolean;
  onClose: () => void;
  leadId: number;
  people?: Person[];
  kind?: ReminderKind;
  reminder?: Reminder | null;
}) {
  const create = useCreateReminder();
  const patch = usePatchReminder();
  const start = reminder ? parseUtc(reminder.starts_at)! : null;
  const [kind, setKind] = useState<ReminderKind>(reminder?.kind ?? initialKind);
  const [title, setTitle] = useState(reminder?.title ?? '');
  const [day, setDay] = useState<string | null>(start ? toIsoDay(start) : null);
  const [time, setTime] = useState(start ? hhmm(start) : '');
  const [duration, setDuration] = useState<string | null>(String(reminder?.duration_min ?? 30));
  const [personId, setPersonId] = useState<string | null>(
    reminder?.person_id ? String(reminder.person_id) : null,
  );
  const [location, setLocation] = useState(reminder?.location ?? '');
  const [notes, setNotes] = useState(reminder?.notes ?? '');

  const meeting = kind === 'meeting';
  const ready = !!day && (!meeting || !!time);
  const pending = create.isPending || patch.isPending;

  const submit = () => {
    if (!day) return;
    const body = {
      starts_at: time ? `${day}T${time}` : day,
      title: title.trim() || null,
      person_id: personId ? Number(personId) : null,
      location: meeting ? location.trim() || null : null,
      notes,
      ...(meeting ? { duration_min: Number(duration) } : {}),
    };
    const opts = {
      onSuccess: (r: Reminder) => {
        const where = r.gcal_state === 'ok' ? ' y en tu Calendar' : '';
        notifySuccess(`${KIND_LABEL[r.kind]} para ${fmtWhen(r.starts_at)}: quedó en el CRM${where}.`);
        onClose();
      },
      onError: (e: unknown) => notifyError(e),
    };
    if (reminder) patch.mutate({ id: reminder.id, ...body }, opts);
    else create.mutate({ leadId, kind, ...body }, opts);
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={reminder ? `Reprogramar: ${reminder.title}` : meeting ? 'Agendar reunión' : 'Recordatorio'}
    >
      <Stack gap="sm">
        {!reminder && (
          <SegmentedControl
            value={kind}
            onChange={(v) => setKind(v as ReminderKind)}
            data={[
              { value: 'reminder', label: 'Recordatorio' },
              { value: 'meeting', label: 'Reunión' },
            ]}
          />
        )}
        <Chip.Group>
          <Group gap={6}>
            {QUICK.map((q) => (
              <Chip key={q.label} size="xs" checked={day === q.day()} onChange={() => setDay(q.day())}>
                {q.label}
              </Chip>
            ))}
          </Group>
        </Chip.Group>
        <Group grow align="flex-start">
          <DateInput label="Día" value={day} onChange={setDay} valueFormat="D/M/YYYY" minDate={todayIso()} />
          <TimeInput
            label="Hora"
            description={meeting ? undefined : 'Sin hora: a las 10'}
            value={time}
            onChange={(e) => setTime(e.currentTarget.value)}
          />
        </Group>
        {meeting && (
          <Select
            label="Duración"
            data={DURATIONS}
            value={duration}
            onChange={setDuration}
            allowDeselect={false}
          />
        )}
        {people.length > 0 && (
          <Select
            label="Con quién"
            data={people.map((p) => ({
              value: String(p.id),
              label: p.title ? `${p.name} (${p.title})` : p.name,
            }))}
            value={personId}
            onChange={setPersonId}
            clearable
            placeholder="Con la empresa"
          />
        )}
        <TextInput
          label="Título"
          placeholder={meeting ? 'Reunión: <empresa>' : 'Llamar a <persona> (<empresa>)'}
          value={title}
          onChange={(e) => setTitle(e.currentTarget.value)}
        />
        {meeting && (
          <TextInput
            label="Dónde"
            placeholder="Link de Meet o Zoom, teléfono o dirección"
            value={location}
            onChange={(e) => setLocation(e.currentTarget.value)}
          />
        )}
        <Textarea
          label="Notas"
          autosize
          minRows={2}
          value={notes}
          onChange={(e) => setNotes(e.currentTarget.value)}
        />
        <Text size="xs" c="dimmed">
          Va a tu Google Calendar (calendario Atentina) con aviso {meeting ? '30 minutos antes' : 'a la hora'}
          , y queda como próxima acción del lead.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={!ready} loading={pending}>
            {reminder ? 'Reprogramar' : 'Guardar'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function DoneModal({ reminder, onClose }: { reminder: Reminder | null; onClose: () => void }) {
  const done = useReminderDone();
  const [outcome, setOutcome] = useState('');
  const [noShow, setNoShow] = useState(false);
  const close = () => {
    setOutcome('');
    setNoShow(false);
    onClose();
  };
  return (
    <Modal opened={!!reminder} onClose={close} title={reminder ? `Hecho: ${reminder.title}` : ''}>
      <Stack gap="sm">
        <Textarea
          label="Qué pasó"
          description="Queda en la línea de tiempo del lead"
          placeholder={
            reminder?.kind === 'meeting'
              ? 'Quieren un piloto; mandar propuesta'
              : 'Atendió, pidió info por mail'
          }
          autosize
          minRows={3}
          value={outcome}
          onChange={(e) => setOutcome(e.currentTarget.value)}
          data-autofocus
        />
        {reminder?.kind === 'meeting' && (
          <Checkbox
            label="No se presentó"
            checked={noShow}
            onChange={(e) => setNoShow(e.currentTarget.checked)}
          />
        )}
        <Text size="xs" c="dimmed">
          Si hay que volver a llamar, creá otro recordatorio desde la ficha.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={close}>
            Volver
          </Button>
          <Button
            loading={done.isPending}
            onClick={() =>
              reminder &&
              done.mutate(
                { id: reminder.id, outcome, no_show: noShow },
                {
                  onSuccess: () => {
                    notifySuccess('Listo.');
                    close();
                  },
                  onError: (e) => notifyError(e),
                },
              )
            }
          >
            Marcar hecho
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function CalendarBadge({ r }: { r: Reminder }) {
  if (r.gcal_state === 'ok') return null;
  const label =
    r.gcal_state === 'off' ? 'solo en el CRM' : r.gcal_state === 'error' ? 'sin Calendar' : 'subiendo';
  return (
    <Tooltip
      label={r.gcal_error ?? 'Se reintenta solo cada minuto'}
      withArrow
      disabled={r.gcal_state === 'pending'}
    >
      <Badge color={r.gcal_state === 'error' ? 'yellow' : 'gray'}>{label}</Badge>
    </Tooltip>
  );
}

/** Una fila de la agenda, con hecho, reprogramar y cancelar. */
export function AgendaRow({
  r,
  showLead = false,
  people,
}: {
  r: Reminder;
  showLead?: boolean;
  people?: Person[];
}) {
  const cancel = useCancelReminder();
  const [doneOpen, setDoneOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const Icon = r.kind === 'meeting' ? IconCalendarEvent : IconPhone;
  return (
    <Group justify="space-between" wrap="nowrap" align="flex-start" gap="xs">
      <Group gap="xs" wrap="nowrap" align="flex-start" style={{ minWidth: 0 }}>
        <Icon size={16} style={{ marginTop: 2, flexShrink: 0 }} />
        <Stack gap={0} style={{ minWidth: 0 }}>
          <Text size="sm" fw={600} c={isOverdue(r) ? 'red' : undefined}>
            {fmtWhen(r.starts_at)} · {r.title}
          </Text>
          <Group gap={6}>
            {showLead && (
              <Anchor component={Link} to={`/leads/${r.lead_id}`} size="xs">
                {r.lead_name}
              </Anchor>
            )}
            {r.location && (
              <Text size="xs" c="dimmed" lineClamp={1}>
                {r.location}
              </Text>
            )}
            {r.created_by === 'sistema' && (
              <Text size="xs" c="dimmed">
                de una respuesta
              </Text>
            )}
            <CalendarBadge r={r} />
          </Group>
        </Stack>
      </Group>
      <Group gap={4} wrap="nowrap">
        <Button size="compact-xs" variant="default" onClick={() => setDoneOpen(true)}>
          Hecho
        </Button>
        <Menu position="bottom-end">
          <Menu.Target>
            <ActionIcon variant="subtle" color="gray" aria-label="Más">
              <IconDots size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item onClick={() => setEditOpen(true)}>Reprogramar o editar</Menu.Item>
            <Menu.Item
              color="red"
              onClick={() =>
                cancel.mutate(r.id, {
                  onSuccess: () => notifySuccess('Cancelado: se borró del Calendar.'),
                  onError: (e) => notifyError(e),
                })
              }
            >
              Cancelar
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>
      <DoneModal reminder={doneOpen ? r : null} onClose={() => setDoneOpen(false)} />
      {editOpen && (
        <ReminderModal
          opened
          onClose={() => setEditOpen(false)}
          leadId={r.lead_id}
          people={people}
          reminder={r}
        />
      )}
    </Group>
  );
}

function AgendaGroup({
  title,
  items,
  showLead,
}: {
  title: string;
  items: Reminder[];
  showLead: boolean;
}): ReactNode {
  if (!items.length) return null;
  return (
    <Stack gap="xs">
      <Text className="label">{title}</Text>
      {items.map((r) => (
        <AgendaRow key={r.id} r={r} showLead={showLead} />
      ))}
    </Stack>
  );
}

/** Tablero: vencidos, hoy y los próximos 7 días. */
export function AgendaCard({ items }: { items: Reminder[] }) {
  const today = todayIso();
  const dayOf = (r: Reminder) => toIsoDay(parseUtc(r.starts_at)!)!;
  const overdue = items.filter((r) => isOverdue(r) && dayOf(r) < today);
  const todays = items.filter((r) => dayOf(r) === today);
  const later = items.filter((r) => dayOf(r) > today);
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Agenda
      </Title>
      {items.length === 0 ? (
        <EmptyState>
          Nada agendado para los próximos 7 días. Se agenda desde la ficha de cada lead.
        </EmptyState>
      ) : (
        <Stack gap="md">
          <AgendaGroup title={`Vencidos (${overdue.length})`} items={overdue} showLead />
          <AgendaGroup title={`Hoy (${todays.length})`} items={todays} showLead />
          <AgendaGroup title={`Próximos 7 días (${later.length})`} items={later} showLead />
        </Stack>
      )}
    </Card>
  );
}

/** Ficha del lead: lo pendiente, con los botones para agendar. */
export function LeadAgenda({ lead }: { lead: Lead }) {
  const reminders = useReminders(lead.id);
  const [open, setOpen] = useState<ReminderKind | null>(null);
  const items = reminders.data ?? [];
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Title order={4}>Agenda</Title>
        <Group gap="xs">
          <Button
            size="compact-sm"
            variant="default"
            leftSection={<IconBell size={14} />}
            onClick={() => setOpen('reminder')}
          >
            Recordatorio
          </Button>
          <Button
            size="compact-sm"
            variant="default"
            leftSection={<IconCalendarEvent size={14} />}
            onClick={() => setOpen('meeting')}
          >
            Agendar reunión
          </Button>
        </Group>
      </Group>
      {items.length === 0 ? (
        <Text size="sm" c="dimmed">
          Nada pendiente. "Llamame el lunes": un recordatorio; va a tu Calendar.
        </Text>
      ) : (
        <Stack gap="xs">
          {items.map((r) => (
            <AgendaRow key={r.id} r={r} people={lead.people} />
          ))}
        </Stack>
      )}
      {open && (
        <ReminderModal
          opened
          onClose={() => setOpen(null)}
          leadId={lead.id}
          people={lead.people}
          kind={open}
        />
      )}
    </Card>
  );
}

const STATUS_LABEL: Record<Reminder['status'], string> = {
  pending: 'pendiente',
  done: 'hecho',
  no_show: 'no se presentó',
  canceled: 'cancelado',
};

/** Entrada de la línea de tiempo. */
export function ReminderEntry({ r }: { r: Reminder }) {
  return (
    <Stack gap={0}>
      <Group gap={6}>
        <Text size="sm" fw={600}>
          {KIND_LABEL[r.kind]}: {r.title}
        </Text>
        <Badge color={r.status === 'pending' ? 'blue' : r.status === 'done' ? 'green' : 'gray'}>
          {STATUS_LABEL[r.status]}
        </Badge>
        <Text size="xs" c="dimmed" ml="auto">
          {fmtWhen(r.starts_at)}
        </Text>
      </Group>
      {r.outcome && <Text size="sm">{r.outcome}</Text>}
      {r.notes && (
        <Text size="xs" c="dimmed" lineClamp={2}>
          {r.notes}
        </Text>
      )}
    </Stack>
  );
}
