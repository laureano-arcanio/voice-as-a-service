import {
  Badge,
  Button,
  Divider,
  Group,
  Modal,
  NumberInput,
  Radio,
  Select,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { ApiError } from '@/api/errors';
import type { TeamMember } from '@/api/types';
import { notifyError, notifyInvalid, notifySuccess } from '@/lib/notify';
import { type AreaRow, useAreaDefaults, useSaveArea } from './api';
import { AreaWhatsapp } from './AreaWhatsapp';
import {
  DELIVERY_OPTIONS,
  MESSAGE_FIELDS,
  type MessageField,
  messageFieldsFor,
  preAcceptError,
  preAcceptNote,
  returnDigitsError,
  ringSecondsError,
  STRATEGY_HELP,
  STRATEGY_OPTIONS,
} from './labels';
import { MemberPicker } from './MemberPicker';
import { ScheduleFields } from './ScheduleFields';
import { type ScheduleDraft, scheduleError, toDraft, toSchedule } from './schedule';
import { fromWhatsappDraft, toWhatsappDraft, type WhatsappDraft, whatsappError } from './whatsappDraft';

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
  delivery: 'call' | 'whatsapp';
  after_hours_area_id: string | null;
  no_answer_area_id: string | null;
  whatsapp: WhatsappDraft;
}

/** Los mensajes que se ven según cómo entrega el área, si rota por WhatsApp de texto y qué hace al cortar la persona. */
function shownMessageFields(
  v: Pick<AreaValues, 'delivery' | 'on_person_hangup' | 'whatsapp'>,
): MessageField[] {
  const rotation = v.delivery !== 'whatsapp' && !!v.whatsapp.template;
  return messageFieldsFor(v.delivery, rotation).filter(
    (f) =>
      (f.key !== 'resume' || v.on_person_hangup === 'resume') &&
      (f.key !== 'goodbye' || v.on_person_hangup === 'end'),
  );
}

/** Lleva el scroll al primer campo con error: el modal es largo y el error puede quedar fuera de la vista. */
function scrollToFirstError() {
  requestAnimationFrame(() =>
    document
      .querySelector('[data-area-modal] [aria-invalid="true"], [data-area-modal] [data-area-error]')
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
  );
}

/** Alta o edicion de un area: personas en orden, horario, timbre, vuelta a la IA y mensajes. */
export function AreaModal({
  area,
  members,
  areas = [],
  onClose,
}: {
  area: AreaRow | null;
  /** Las personas del equipo del cliente del area. */
  members: TeamMember[];
  /** Las áreas del cliente: a cuáles puede pasar fuera de horario o si nadie acepta. */
  areas?: AreaRow[];
  onClose: () => void;
}) {
  const save = useSaveArea();
  const defaults = useAreaDefaults();
  // Los mensajes que salen antes de aceptar admiten pocas variables: la lista viene de la API.
  const preAcceptKeys = defaults.data?.pre_accept_messages ?? [];
  const preAcceptVars = defaults.data?.pre_accept_variables ?? [];
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
      delivery: area?.delivery === 'whatsapp' ? 'whatsapp' : 'call',
      after_hours_area_id: area?.after_hours_area_id ?? null,
      no_answer_area_id: area?.no_answer_area_id ?? null,
      whatsapp: toWhatsappDraft(area?.whatsapp),
    },
    // Solo se valida lo que se ve: según cómo se avisa, el timbre, la tecla y varios mensajes no están en pantalla.
    validate: {
      name: (v) => (v.trim() ? null : 'Poné un nombre'),
      ring_seconds: (v, values) => (values.delivery === 'whatsapp' ? null : ringSecondsError(v)),
      return_digits: (v, values) => (values.delivery === 'whatsapp' ? null : returnDigitsError(v.trim())),
      schedule: (v) => scheduleError(v),
      whatsapp: (v, values) => whatsappError(v, values.delivery),
      messages: Object.fromEntries(
        preAcceptKeys.map((key) => [
          key,
          (text: string | undefined, values: AreaValues) =>
            shownMessageFields(values).some((f) => f.key === key)
              ? preAcceptError(text ?? '', preAcceptVars)
              : null,
        ]),
      ),
    },
  });

  const v = form.values;
  const setMembers = (ids: string[]) => form.setFieldValue('member_ids', ids);

  const setMessage = (key: string, text: string) => {
    form.setFieldValue('messages', { ...form.getValues().messages, [key]: text });
    form.clearFieldError(`messages.${key}`);
  };
  const resetMessage = (key: string) => {
    const next = { ...form.getValues().messages };
    delete next[key];
    form.setFieldValue('messages', next);
    form.clearFieldError(`messages.${key}`);
  };

  const submit = (values: AreaValues) => {
    const defaultsText = defaults.data?.messages ?? {};
    const saved = area?.messages ?? {};
    const shown = new Set(shownMessageFields(values).map((f) => f.key));
    // Lo que no se ve según cómo se avisa no se valida, pero tampoco se guarda con un valor inválido: queda lo
    // que ya tenía el área. Lo oculto que está bien se manda igual, para no perder lo editado.
    const hidden = (key: string, text: string) =>
      !shown.has(key) && preAcceptKeys.includes(key) && !!preAcceptError(text, preAcceptVars);
    const messages = Object.fromEntries(
      Object.entries(values.messages)
        .map(([k, t]) => [k, hidden(k, t.trim()) ? (saved[k] ?? '') : t.trim()] as const)
        .filter(([k, t]) => t && t !== defaultsText[k]),
    );
    const notice = values.delivery === 'whatsapp';
    const ringSeconds =
      notice && ringSecondsError(values.ring_seconds) ? (area?.ring_seconds ?? 20) : values.ring_seconds;
    const returnDigits =
      notice && returnDigitsError(values.return_digits.trim())
        ? (area?.return_digits ?? '2')
        : values.return_digits.trim();
    save.mutate(
      {
        id: area?.id,
        body: {
          name: values.name.trim(),
          description: values.description.trim(),
          active: values.active,
          member_ids: values.member_ids,
          strategy: values.strategy,
          ring_seconds: Number(ringSeconds),
          schedule: toSchedule(values.schedule),
          on_person_hangup: values.on_person_hangup,
          return_digits: returnDigits,
          messages,
          delivery: values.delivery,
          after_hours_area_id: values.after_hours_area_id,
          no_answer_area_id: values.no_answer_area_id,
          whatsapp: fromWhatsappDraft(values.whatsapp, values.delivery),
        },
      },
      {
        onSuccess: () => {
          notifySuccess(area ? 'Área guardada.' : 'Área creada.');
          onClose();
        },
        onError: (e) => {
          if (e instanceof ApiError && e.code === 'area_name_taken') {
            form.setFieldError('name', e.message);
            return;
          }
          // Un mensaje rechazado por el servidor: se marca el campo, con su nombre, y se lleva el scroll a él.
          const shown = shownMessageFields(form.getValues());
          const fields = (e instanceof ApiError ? e.errors : []).flatMap((x) => {
            const f = shown.find((m) => `messages.${m.key}` === x.path);
            return f ? [{ path: x.path, label: f.label, message: x.message }] : [];
          });
          if (!fields.length) return notifyError(e, 'No se pudo guardar');
          for (const f of fields) form.setFieldError(f.path, f.message);
          notifyInvalid(`${fields[0]!.label}: ${fields[0]!.message}`, 'No se pudo guardar el área');
          scrollToFirstError();
        },
      },
    );
  };

  // El guardado fue rechazado por la validacion: el modal es largo y el error puede quedar fuera de la
  // vista, asi que se avisa con una notificacion y se lleva el scroll al primer campo con error.
  const invalid = (errors: Record<string, unknown>) => {
    const [path, first] = Object.entries(errors).find(([, e]) => typeof e === 'string' && e) ?? [];
    if (typeof first === 'string') {
      const label = MESSAGE_FIELDS.find((f) => `messages.${f.key}` === path)?.label;
      notifyInvalid(label ? `${label}: ${first}` : first, 'No se pudo guardar el área');
    }
    scrollToFirstError();
  };

  const notice = v.delivery === 'whatsapp';
  const shownMessages = shownMessageFields(v);
  // A cuales puede pasar: las de este cliente, menos ella misma.
  const routeOptions = areas
    .filter((a) => a.id !== area?.id && (!area || a.client_id === area.client_id))
    .map((a) => ({ value: a.id, label: a.name }));
  const whatsappOn = !!v.whatsapp.accountId;
  const helpFor = (f: { key: string; help: string }) =>
    preAcceptKeys.includes(f.key) && preAcceptVars.length
      ? `${f.help} ${preAcceptNote(preAcceptVars)}.`
      : f.help;

  return (
    <Modal opened onClose={onClose} title={area ? `Editar área ${area.name}` : 'Nueva área'} size="lg">
      <form data-area-modal onSubmit={form.onSubmit(submit, invalid)}>
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
          <Stack gap={4}>
            <Text size="sm" fw={600}>
              Cómo se avisa
            </Text>
            <SegmentedControl
              aria-label="Cómo se avisa"
              data={DELIVERY_OPTIONS}
              {...form.getInputProps('delivery')}
              onChange={(d) => {
                form.setFieldValue('delivery', d === 'whatsapp' ? 'whatsapp' : 'call');
                form.clearFieldError('whatsapp');
              }}
            />
            <Text size="xs" c="dimmed">
              {notice
                ? 'Solo manda un aviso por WhatsApp a una persona, sin esperar que acepte. El agente le dice a la persona que ya avisó.'
                : 'Se llama a las personas del área y atiende quien acepta. Con una plantilla de WhatsApp, además se les avisa por texto.'}
            </Text>
          </Stack>

          <Divider label="Personas" labelPosition="left" mt="xs" />
          <Text size="xs" c="dimmed">
            {notice
              ? 'Recibe el aviso la primera persona activa con teléfono y «Recibe WhatsApp»; si no se le puede enviar, la siguiente.'
              : 'Se las llama en este orden. Solo reciben llamadas las activas con teléfono.'}
          </Text>
          <MemberPicker
            members={members}
            value={v.member_ids}
            onChange={setMembers}
            addLabel="Agregar persona al área"
            removeLabel="Quitar del área"
            detail={(m) =>
              m?.phone ? (
                <Group gap="xs" wrap="nowrap">
                  <Text className="mono" c="dimmed" visibleFrom="xs">
                    {m.phone}
                  </Text>
                  {(notice || whatsappOn) && !m.whatsapp_notify && (
                    <Badge color="gray" title="Activalo en su ficha para avisarle por WhatsApp">
                      No recibe WhatsApp
                    </Badge>
                  )}
                </Group>
              ) : (
                <Badge color="yellow">Sin teléfono</Badge>
              )
            }
          />
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
            {!notice && (
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
            )}
          </Group>

          <Divider label="Horario" labelPosition="left" mt="xs" />
          <ScheduleFields
            value={v.schedule}
            onChange={(next) => {
              form.setFieldValue('schedule', next);
              form.clearFieldError('schedule');
            }}
            error={form.errors.schedule}
          />

          <Divider label="Si no se puede" labelPosition="left" mt="xs" />
          <Text size="xs" c="dimmed">
            En vez de tomar el mensaje, el agente puede pasar a otra área.
          </Text>
          <Group align="flex-start" grow>
            <Select
              label="Fuera de horario, pasa a"
              description="Cuando el área está cerrada. Vacío: lo que dice el mensaje «Fuera de horario»."
              placeholder="Ninguna"
              data={routeOptions}
              clearable
              searchable
              nothingFoundMessage="No hay otras áreas"
              {...form.getInputProps('after_hours_area_id')}
            />
            <Select
              label="Si nadie acepta, pasa a"
              description="Si nadie atiende, no hay personas o no se puede llamar. Vacío: toma el mensaje."
              placeholder="Ninguna"
              data={routeOptions}
              clearable
              searchable
              nothingFoundMessage="No hay otras áreas"
              {...form.getInputProps('no_answer_area_id')}
            />
          </Group>

          <Divider label="WhatsApp" labelPosition="left" mt="xs" />
          <AreaWhatsapp
            value={v.whatsapp}
            delivery={v.delivery}
            onChange={(next) => {
              form.setFieldValue('whatsapp', next);
              form.clearFieldError('whatsapp');
            }}
          />
          {form.errors.whatsapp && (
            <Text size="sm" c="red" role="alert" data-area-error>
              {form.errors.whatsapp}
            </Text>
          )}

          {!notice && (
            <>
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
            </>
          )}

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
                  description={helpFor(f)}
                  placeholder={defaults.data?.messages[f.key]}
                  autosize
                  minRows={1}
                  maxLength={500}
                  value={text}
                  error={form.errors[`messages.${f.key}`]}
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
