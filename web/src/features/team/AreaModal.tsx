import {
  ActionIcon,
  Badge,
  Button,
  Divider,
  Group,
  Modal,
  NumberInput,
  Radio,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { DatePickerInput, TimeInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { IconArrowDown, IconArrowUp, IconPlus, IconX } from '@tabler/icons-react';
import { ApiError } from '@/api/errors';
import type { TeamMember } from '@/api/types';
import { notifyError, notifySuccess } from '@/lib/notify';
import { type AreaRow, useAreaDefaults, useSaveArea } from './api';
import { MESSAGE_FIELDS, returnDigitsError, STRATEGY_HELP, STRATEGY_OPTIONS } from './labels';
import {
  DAY_LABEL,
  DAYS,
  type Day,
  type Range,
  type ScheduleDraft,
  scheduleError,
  toDraft,
  toSchedule,
} from './schedule';

interface AreaValues {
  name: string;
  description: string;
  active: boolean;
  member_ids: string[];
  strategy: 'sequential' | 'round_robin';
  ring_seconds: number | string;
  schedule: ScheduleDraft;
  on_person_hangup: 'resume' | 'end';
  return_digits: string;
  messages: Record<string, string>;
}

/** Alta o edicion de un area: personas en orden, horario, timbre, vuelta a la IA y mensajes. */
export function AreaModal({
  area,
  members,
  onClose,
}: {
  area: AreaRow | null;
  /** Las personas del equipo del cliente del area. */
  members: TeamMember[];
  onClose: () => void;
}) {
  const save = useSaveArea();
  const defaults = useAreaDefaults();
  const form = useForm<AreaValues>({
    initialValues: {
      name: area?.name ?? '',
      description: area?.description ?? '',
      active: area?.active ?? true,
      member_ids: area?.member_ids ?? [],
      strategy: area?.strategy === 'round_robin' ? 'round_robin' : 'sequential',
      ring_seconds: area?.ring_seconds ?? 20,
      schedule: toDraft(area ? area.schedule : null),
      on_person_hangup: area?.on_person_hangup === 'end' ? 'end' : 'resume',
      return_digits: area?.return_digits ?? '2',
      messages: { ...(area?.messages ?? {}) },
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      ring_seconds: (v) => (typeof v === 'number' && v >= 5 && v <= 60 ? null : 'Entre 5 y 60 segundos'),
      return_digits: (v) => returnDigitsError(v.trim()),
      schedule: (v) => scheduleError(v),
    },
  });

  const v = form.values;
  const byId = new Map(members.map((m) => [m.id, m]));
  const available = members.filter((m) => !v.member_ids.includes(m.id));

  const setMembers = (ids: string[]) => form.setFieldValue('member_ids', ids);
  const move = (i: number, d: -1 | 1) => {
    const ids = [...v.member_ids];
    [ids[i], ids[i + d]] = [ids[i + d], ids[i]];
    setMembers(ids);
  };

  const setSchedule = (next: Partial<ScheduleDraft>) => {
    form.setFieldValue('schedule', { ...form.getValues().schedule, ...next });
    form.clearFieldError('schedule');
  };
  const setDay = (day: Day, ranges: Range[]) =>
    setSchedule({ week: { ...form.getValues().schedule.week, [day]: ranges } });

  const setMessage = (key: string, text: string) =>
    form.setFieldValue('messages', { ...form.getValues().messages, [key]: text });
  const resetMessage = (key: string) => {
    const next = { ...form.getValues().messages };
    delete next[key];
    form.setFieldValue('messages', next);
  };

  const submit = (values: AreaValues) => {
    const defaultsText = defaults.data?.messages ?? {};
    const messages = Object.fromEntries(
      Object.entries(values.messages)
        .map(([k, t]) => [k, t.trim()] as const)
        .filter(([k, t]) => t && t !== defaultsText[k]),
    );
    save.mutate(
      {
        id: area?.id,
        body: {
          name: values.name.trim(),
          description: values.description.trim(),
          active: values.active,
          member_ids: values.member_ids,
          strategy: values.strategy,
          ring_seconds: Number(values.ring_seconds),
          schedule: toSchedule(values.schedule),
          on_person_hangup: values.on_person_hangup,
          return_digits: values.return_digits.trim(),
          messages,
        },
      },
      {
        onSuccess: () => {
          notifySuccess(area ? 'Área guardada.' : 'Área creada.');
          onClose();
        },
        onError: (e) => {
          if (e instanceof ApiError && e.code === 'area_name_taken') form.setFieldError('name', e.message);
          else notifyError(e, 'No se pudo guardar');
        },
      },
    );
  };

  const shownMessages = MESSAGE_FIELDS.filter(
    (f) =>
      (f.key !== 'resume' || v.on_person_hangup === 'resume') &&
      (f.key !== 'goodbye' || v.on_person_hangup === 'end'),
  );

  return (
    <Modal opened onClose={onClose} title={area ? `Editar área ${area.name}` : 'Nueva área'} size="lg">
      <form onSubmit={form.onSubmit(submit)}>
        <Stack>
          <TextInput
            label="Nombre"
            placeholder="Ventas"
            maxLength={80}
            data-autofocus
            {...form.getInputProps('name')}
          />
          <Textarea
            label="Qué atiende"
            description="Lo lee el agente para decidir a qué área pasar la llamada o el chat."
            placeholder="Precios, presupuestos y visitas al showroom"
            autosize
            minRows={2}
            maxLength={1000}
            {...form.getInputProps('description')}
          />
          <Switch
            label="Activa"
            description="Un área inactiva no recibe derivaciones."
            {...form.getInputProps('active', { type: 'checkbox' })}
          />

          <Divider label="Personas" labelPosition="left" mt="xs" />
          <Text size="xs" c="dimmed">
            Se las llama en este orden. Solo reciben llamadas las activas con teléfono.
          </Text>
          {v.member_ids.length > 0 && (
            <Stack gap={6}>
              {v.member_ids.map((id, i) => {
                const m = byId.get(id);
                const name = m?.name ?? 'Persona borrada';
                return (
                  <Group key={id} className="def-item" justify="space-between" wrap="nowrap" gap="xs">
                    <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                      <Text className="mono" c="dimmed" w={18} ta="right">
                        {i + 1}
                      </Text>
                      <Text size="sm" fw={600} truncate>
                        {name}
                      </Text>
                      {m?.phone ? (
                        <Text className="mono" c="dimmed" visibleFrom="xs">
                          {m.phone}
                        </Text>
                      ) : (
                        <Badge color="yellow">Sin teléfono</Badge>
                      )}
                      {m && !m.active && <Badge color="gray">Inactiva</Badge>}
                    </Group>
                    <Group gap={4} wrap="nowrap">
                      <Tooltip label="Subir" withArrow>
                        <ActionIcon
                          variant="default"
                          aria-label={`Subir a ${name}`}
                          disabled={i === 0}
                          onClick={() => move(i, -1)}
                        >
                          <IconArrowUp size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Bajar" withArrow>
                        <ActionIcon
                          variant="default"
                          aria-label={`Bajar a ${name}`}
                          disabled={i === v.member_ids.length - 1}
                          onClick={() => move(i, 1)}
                        >
                          <IconArrowDown size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Quitar del área" withArrow>
                        <ActionIcon
                          variant="default"
                          aria-label={`Quitar a ${name}`}
                          onClick={() => setMembers(v.member_ids.filter((x) => x !== id))}
                        >
                          <IconX size={16} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Group>
                );
              })}
            </Stack>
          )}
          {members.length === 0 ? (
            <Text size="sm" c="dimmed">
              Todavía no hay personas en el equipo: cargalas primero en la sección Personas.
            </Text>
          ) : (
            available.length > 0 && (
              <Select
                aria-label="Agregar persona al área"
                placeholder="Agregar persona"
                data={available.map((m) => ({ value: m.id, label: m.name }))}
                value={null}
                onChange={(id) => id && setMembers([...v.member_ids, id])}
                searchable
                leftSection={<IconPlus size={16} />}
              />
            )
          )}
          <Group align="flex-start" grow>
            <Stack gap={4}>
              <Text size="sm" fw={600}>
                A quién se llama primero
              </Text>
              <SegmentedControl
                aria-label="A quién se llama primero"
                data={STRATEGY_OPTIONS}
                {...form.getInputProps('strategy')}
              />
              <Text size="xs" c="dimmed">
                {STRATEGY_HELP[v.strategy]}
              </Text>
            </Stack>
            <NumberInput
              label="Timbre por persona"
              description="Segundos antes de pasar a la siguiente. El buzón de Claro atiende a los ~33 s."
              min={5}
              max={60}
              suffix=" s"
              allowDecimal={false}
              allowNegative={false}
              {...form.getInputProps('ring_seconds')}
            />
          </Group>

          <Divider label="Horario" labelPosition="left" mt="xs" />
          <Switch
            label="Atiende siempre"
            description="Sin horario: todos los días, a toda hora."
            checked={v.schedule.always}
            onChange={(e) => setSchedule({ always: e.currentTarget.checked })}
          />
          {!v.schedule.always && (
            <>
              <Stack gap={6}>
                {DAYS.map((d) => (
                  <DayRanges key={d} day={d} ranges={v.schedule.week[d]} onChange={(r) => setDay(d, r)} />
                ))}
              </Stack>
              <DatePickerInput
                type="multiple"
                label="Días cerrados"
                description="Feriados o días sin atención, aunque tengan horario."
                placeholder="Ninguno"
                valueFormat="DD/MM/YYYY"
                value={v.schedule.closed}
                onChange={(dates) => setSchedule({ closed: dates.map(String) })}
                clearable
              />
            </>
          )}
          {form.errors.schedule && (
            <Text size="sm" c="red" role="alert">
              {form.errors.schedule}
            </Text>
          )}

          <Divider label="Durante la llamada" labelPosition="left" mt="xs" />
          <Radio.Group label="Si la persona corta" {...form.getInputProps('on_person_hangup')}>
            <Stack gap={6} mt={6}>
              <Radio value="resume" label="El agente vuelve: «¿Te puedo ayudar con algo más?»" />
              <Radio value="end" label="Se despide y corta" />
            </Stack>
          </Radio.Group>
          <TextInput
            label="Tecla para devolverle la llamada a la IA"
            description="La marca la persona del equipo para que el agente retome. Sin * y distinta de 1."
            maxLength={4}
            w={{ base: '100%', xs: 320 }}
            classNames={{ input: 'mono' }}
            {...form.getInputProps('return_digits')}
          />

          <Divider label="Mensajes" labelPosition="left" mt="xs" />
          <Text size="xs" c="dimmed">
            Vacío usa el texto por defecto.
            {defaults.data?.variables.length
              ? ` Podés usar ${defaults.data.variables.map((x) => `{{${x}}}`).join(', ')}.`
              : ''}
          </Text>
          {shownMessages.map((f) => {
            const text = v.messages[f.key] ?? '';
            return (
              <Stack key={f.key} gap={4}>
                <Textarea
                  label={f.label}
                  description={f.help}
                  placeholder={defaults.data?.messages[f.key]}
                  autosize
                  minRows={1}
                  maxLength={500}
                  value={text}
                  onChange={(e) => setMessage(f.key, e.currentTarget.value)}
                />
                {text && (
                  <Group justify="flex-end">
                    <Button
                      variant="subtle"
                      size="compact-sm"
                      aria-label={`Volver al default: ${f.label}`}
                      onClick={() => resetMessage(f.key)}
                    >
                      Volver al default
                    </Button>
                  </Group>
                )}
              </Stack>
            );
          })}

          <Group justify="flex-end" mt="xs">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={save.isPending}>
              {area ? 'Guardar cambios' : 'Crear área'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

/** Las franjas de un dia; sin ninguna, el dia esta cerrado. */
function DayRanges({ day, ranges, onChange }: { day: Day; ranges: Range[]; onChange: (r: Range[]) => void }) {
  const label = DAY_LABEL[day];
  const set = (i: number, j: 0 | 1, value: string) =>
    onChange(ranges.map((r, k) => (k === i ? (j === 0 ? [value, r[1]] : [r[0], value]) : r)));
  return (
    <Group align="flex-start" gap="xs" wrap="nowrap">
      <Text size="sm" fw={600} w={86} pt={6} style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Stack gap={6} style={{ flex: 1 }}>
        {ranges.length === 0 && (
          <Text size="sm" c="dimmed" pt={6}>
            Cerrado
          </Text>
        )}
        {ranges.map(([from, to], i) => (
          <Group key={i} gap={6} wrap="nowrap">
            <TimeInput
              aria-label={`${label}, franja ${i + 1}, desde`}
              value={from}
              onChange={(e) => set(i, 0, e.currentTarget.value)}
              w={110}
            />
            <Text size="sm" c="dimmed">
              a
            </Text>
            <TimeInput
              aria-label={`${label}, franja ${i + 1}, hasta`}
              value={to}
              onChange={(e) => set(i, 1, e.currentTarget.value)}
              w={110}
            />
            <Tooltip label="Quitar franja" withArrow>
              <ActionIcon
                variant="subtle"
                color="gray"
                aria-label={`Quitar franja ${i + 1} del ${label.toLowerCase()}`}
                onClick={() => onChange(ranges.filter((_, k) => k !== i))}
              >
                <IconX size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
        ))}
      </Stack>
      <Tooltip label="Agregar franja" withArrow>
        <ActionIcon
          variant="default"
          aria-label={`Agregar franja el ${label.toLowerCase()}`}
          onClick={() => onChange([...ranges, ranges.length ? ['', ''] : ['09:00', '18:00']])}
        >
          <IconPlus size={16} />
        </ActionIcon>
      </Tooltip>
    </Group>
  );
}
