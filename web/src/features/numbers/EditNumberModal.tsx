import {
  Badge,
  Button,
  Divider,
  Group,
  Modal,
  NumberInput,
  Radio,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import type { PhoneNumber, TeamMember } from '@/api/types';
import { PlanAlert } from '@/components/PlanGate';
import { useAgents } from '@/features/agents/api';
import { useFeatureLock } from '@/features/billing/features';
import { useTeam } from '@/features/team/api';
import { STRATEGY_OPTIONS } from '@/features/team/labels';
import { MemberPicker } from '@/features/team/MemberPicker';
import { type NoAnswerDestination, NoAnswerField } from '@/features/team/NoAnswerField';
import { ScheduleFields } from '@/features/team/ScheduleFields';
import { scheduleError } from '@/features/team/schedule';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateNumber } from './api';
import {
  type AnsweringDraft,
  CONNECT_ON_ANSWER_HELP,
  CONNECT_ON_ANSWER_PANEL_HELP,
  HOLD_MUSIC_HELP,
  FALLBACK_LABELS,
  FALLBACK_MESSAGE_DEFAULTS,
  MESSAGE_MAX,
  RECORD_FULL_CALL_HELP,
  RETRY_HELP,
  RETRY_INTERVAL_DEFAULT,
  RETRY_INTERVAL_HELP,
  RETRY_MESSAGE_DEFAULT,
  RETRY_MESSAGE_HELP,
  retryIntervalOptions,
  retryOptions,
  RING_FIRST_HELP,
  RING_FIRST_OPTIONS,
  RING_SECONDS_HELP,
  RING_SECONDS_RETRY_HELP,
  STRATEGY_HELP,
  toAnsweringBody,
  toAnsweringDraft,
} from './answering';
import { answeringErrorField, numberErrorTitle } from './errors';

/** Por dónde le suena a una persona: lo que tiene cargado en el equipo. */
function reach(m: TeamMember | undefined) {
  if (!m) return null;
  if (m.phone)
    return (
      <>
        <Text className="mono" c="dimmed" visibleFrom="xs">
          {m.phone}
        </Text>
        {!m.user_id && <Badge color="gray">Solo en el teléfono</Badge>}
      </>
    );
  if (m.user_id) return <Badge color="gray">Solo en el panel</Badge>;
  return <Badge color="yellow">No le puede sonar</Badge>;
}

/** Etiqueta de un número y, asignado, quién atiende las entrantes: el equipo o el agente. */
export function EditNumberModal({
  number,
  startInTeam = false,
  onClose,
}: {
  number: PhoneNumber;
  /** Abre con el equipo elegido: el toggle de la fila lo usa para pasar a Equipo un número sin personas. */
  startInTeam?: boolean;
  onClose: () => void;
}) {
  const update = useUpdateNumber();
  const assigned = !!number.client_id;
  const clientId = number.client_id ?? undefined;
  const agents = useAgents(clientId, false, assigned);
  const team = useTeam(clientId, assigned);
  const lock = useFeatureLock('direct_calls');
  const teamMode = (all: AnsweringDraft) => assigned && all.answer_mode === 'team';
  const form = useForm<AnsweringDraft>({
    initialValues: { ...toAnsweringDraft(number), ...(startInTeam && { answer_mode: 'team' as const }) },
    validate: {
      label: (v) => (v.length <= 64 ? null : 'Hasta 64 caracteres'),
      ring_seconds: (v, all) =>
        teamMode(all) && !(typeof v === 'number' && v >= 5 && v <= 60) ? 'Entre 5 y 60 segundos' : null,
      schedule: (v, all) => (teamMode(all) ? scheduleError(v) : null),
      member_ids: (v, all) => (teamMode(all) && v.length === 0 ? 'Elegí al menos una persona' : null),
      agent_id: (v, all) =>
        teamMode(all) && all.team_fallback === 'agent' && !v
          ? 'Elegí el agente que atiende si nadie del equipo lo hace'
          : null,
      team_fallback_member_id: (v, all) =>
        teamMode(all) && all.team_fallback === 'member' && !v ? 'Elegí la persona a la que se llama' : null,
      team_retry_message: (v) => (v.length <= MESSAGE_MAX ? null : `Hasta ${MESSAGE_MAX} caracteres`),
      team_fallback_message: (v) => (v.length <= MESSAGE_MAX ? null : `Hasta ${MESSAGE_MAX} caracteres`),
    },
  });
  const v = form.values;

  const agentOptions = (agents.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  if (number.agent_id && !agentOptions.some((o) => o.value === number.agent_id)) {
    agentOptions.push({ value: number.agent_id, label: `${number.agent_name ?? 'Agente'} (archivado)` });
  }
  // Con el plan sin llamadas directas no se puede elegir el equipo (si ya lo tenía, se puede pasar al agente).
  const teamLocked = lock.locked && number.answer_mode !== 'team';

  const submit = (values: AnsweringDraft) =>
    update.mutate(
      { id: number.id, body: assigned ? toAnsweringBody(values) : { label: values.label.trim() } },
      {
        onSuccess: () => {
          notifySuccess('Número actualizado.');
          onClose();
        },
        onError: (e) => {
          const field = answeringErrorField(e);
          if (field) form.setFieldError(field, (e as Error).message);
          else notifyError(e, numberErrorTitle(e));
        },
      },
    );

  // A quién se puede llamar si nadie atiende: con teléfono, activas y fuera del número (la guardada se conserva).
  const personOptions = (team.data ?? [])
    .filter(
      (m) => m.id === v.team_fallback_member_id || (m.phone && m.active && !v.member_ids.includes(m.id)),
    )
    .map((m) => ({ value: m.id, label: m.phone ? `${m.name} · ${m.phone}` : m.name }));
  const message = (kind: 'voicemail' | 'hangup'): NoAnswerDestination['detail'] => ({
    type: 'text',
    label: 'Mensaje',
    description: 'Lo dice antes de cortar o de grabar. Vacío usa el de siempre.',
    placeholder: FALLBACK_MESSAGE_DEFAULTS[kind],
    value: v.team_fallback_message,
    onChange: (text) => form.setFieldValue('team_fallback_message', text),
    maxLength: MESSAGE_MAX,
    error: form.errors.team_fallback_message,
  });
  const fallbackDestinations: NoAnswerDestination[] = [
    {
      value: 'agent',
      label: FALLBACK_LABELS.agent,
      detail: {
        type: 'select',
        label: 'Agente de respaldo',
        description: 'Atiende con su apertura, sabiendo que nadie del equipo contestó.',
        placeholder: 'Elegí un agente',
        options: agentOptions,
        value: v.agent_id || null,
        onChange: (id) => form.setFieldValue('agent_id', id ?? ''),
        error: form.errors.agent_id,
      },
    },
    {
      value: 'member',
      label: FALLBACK_LABELS.member,
      clear: () => form.setFieldValue('team_fallback_member_id', null),
      detail: {
        type: 'select',
        label: 'Persona',
        description: 'Se la llama una vez a su teléfono, como a las personas del número. Si no atiende, toma el mensaje.',
        placeholder: 'Elegí una persona',
        options: personOptions,
        value: v.team_fallback_member_id,
        onChange: (id) => {
          form.setFieldValue('team_fallback_member_id', id);
          form.clearFieldError('team_fallback_member_id');
        },
        nothingFound: 'No hay personas con teléfono fuera del número',
        error: form.errors.team_fallback_member_id,
      },
    },
    { value: 'voicemail', label: FALLBACK_LABELS.voicemail, detail: message('voicemail') },
    { value: 'hangup', label: FALLBACK_LABELS.hangup, detail: message('hangup') },
  ];

  return (
    <Modal opened onClose={onClose} title={`Editar ${number.e164}`} size="lg">
      <form onSubmit={form.onSubmit(submit)}>
        <Stack>
          <TextInput label="Etiqueta" maxLength={64} data-autofocus {...form.getInputProps('label')} />

          {assigned && (
            <>
              <Divider label="Quién atiende las entrantes" labelPosition="left" mt="xs" />
              {lock.locked && (
                <PlanAlert
                  feature="direct_calls"
                  what="que atienda el equipo"
                  hint="Con tu plan atiende el agente."
                />
              )}
              <Radio.Group
                aria-label="Atiende"
                value={v.answer_mode}
                onChange={(mode) => {
                  form.setFieldValue('answer_mode', mode === 'team' ? 'team' : 'agent');
                  form.clearFieldError('answer_mode');
                }}
                error={form.errors.answer_mode}
              >
                <Stack gap="xs">
                  <Radio
                    value="team"
                    label="El equipo"
                    description="Suena en el teléfono o en el panel de las personas que elijas. Estas llamadas se graban."
                    disabled={teamLocked}
                  />
                  <Radio
                    value="agent"
                    label="El agente"
                    description="Atiende el agente, que puede derivar al equipo con sus áreas."
                  />
                </Stack>
              </Radio.Group>

              {v.answer_mode === 'agent' && (
                <Select
                  label="Agente que atiende"
                  placeholder="Ninguno (no atiende)"
                  data={agentOptions}
                  clearable
                  searchable
                  value={v.agent_id || null}
                  onChange={(id) => form.setFieldValue('agent_id', id ?? '')}
                />
              )}

              {v.answer_mode === 'team' && (
                <>
                  <Divider label="Personas" labelPosition="left" mt="xs" />
                  <Text size="xs" c="dimmed">
                    Suenan en este orden. Solo reciben llamadas las activas, con teléfono o usuario del panel.
                  </Text>
                  <MemberPicker
                    members={team.data ?? []}
                    value={v.member_ids}
                    onChange={(ids) => {
                      form.setFieldValue('member_ids', ids);
                      form.clearFieldError('member_ids');
                    }}
                    addLabel="Agregar persona al número"
                    removeLabel="Quitar del número"
                    detail={reach}
                  />
                  {form.errors.member_ids && (
                    <Text size="sm" c="red" role="alert">
                      {form.errors.member_ids}
                    </Text>
                  )}

                  <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="md">
                    <Stack gap="sm">
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
                      <Stack gap={4}>
                        <Text size="sm" fw={600}>
                          Suena primero
                        </Text>
                        <SegmentedControl
                          aria-label="Suena primero"
                          data={RING_FIRST_OPTIONS}
                          {...form.getInputProps('ring_first')}
                        />
                        <Text size="xs" c="dimmed">
                          {RING_FIRST_HELP[v.ring_first]}
                        </Text>
                      </Stack>
                      <Switch
                        label="Conectar al atender"
                        description={
                          v.ring_first === 'panel'
                            ? `${CONNECT_ON_ANSWER_HELP} ${CONNECT_ON_ANSWER_PANEL_HELP}`
                            : CONNECT_ON_ANSWER_HELP
                        }
                        {...form.getInputProps('team_connect_on_answer', { type: 'checkbox' })}
                      />
                      <Switch
                        label="Música mientras suena"
                        description={HOLD_MUSIC_HELP}
                        {...form.getInputProps('team_hold_music', { type: 'checkbox' })}
                      />
                    </Stack>
                    <NumberInput
                      label="Timbre por persona"
                      description={
                        v.team_retry_seconds > 0 && !v.team_connect_on_answer
                          ? RING_SECONDS_RETRY_HELP
                          : RING_SECONDS_HELP
                      }
                      min={5}
                      max={60}
                      suffix=" s"
                      allowDecimal={false}
                      allowNegative={false}
                      {...form.getInputProps('ring_seconds')}
                    />
                  </SimpleGrid>

                  <Divider label="Horario (opcional)" labelPosition="left" mt="xs" />
                  <ScheduleFields
                    value={v.schedule}
                    onChange={(next) => {
                      form.setFieldValue('schedule', next);
                      form.clearFieldError('schedule');
                    }}
                    error={form.errors.schedule}
                  />

                  <Divider label="Si nadie atiende" labelPosition="left" mt="xs" />
                  <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="md">
                    <Select
                      label="Volver a intentar"
                      description={RETRY_HELP}
                      allowDeselect={false}
                      data={retryOptions(v.team_retry_seconds)}
                      value={String(v.team_retry_seconds)}
                      onChange={(sec) => form.setFieldValue('team_retry_seconds', Number(sec ?? 0))}
                      error={form.errors.team_retry_seconds}
                    />
                    {v.team_retry_seconds > 0 && (
                      <Select
                        label="Cada"
                        description={RETRY_INTERVAL_HELP}
                        allowDeselect={false}
                        data={retryIntervalOptions(v.team_retry_interval_seconds)}
                        value={String(v.team_retry_interval_seconds)}
                        onChange={(sec) =>
                          form.setFieldValue('team_retry_interval_seconds', Number(sec ?? RETRY_INTERVAL_DEFAULT))
                        }
                        error={form.errors.team_retry_interval_seconds}
                      />
                    )}
                  </SimpleGrid>
                  {v.team_retry_seconds > 0 && (
                    <Textarea
                      label="Aviso de espera"
                      description={RETRY_MESSAGE_HELP}
                      placeholder={RETRY_MESSAGE_DEFAULT}
                      maxLength={MESSAGE_MAX}
                      autosize
                      minRows={2}
                      maxRows={4}
                      {...form.getInputProps('team_retry_message')}
                    />
                  )}

                  <Divider
                    label={
                      v.team_retry_seconds > 0
                        ? 'Si sigue sin atender, o fuera de horario'
                        : 'Si nadie atiende o es fuera de horario'
                    }
                    labelPosition="left"
                    mt="xs"
                  />
                  <NoAnswerField
                    value={v.team_fallback}
                    onChange={(f) => {
                      if (f === 'agent' || f === 'member' || f === 'voicemail' || f === 'hangup')
                        form.setFieldValue('team_fallback', f);
                    }}
                    destinations={fallbackDestinations}
                  />
                </>
              )}
              <Divider label="Grabación" labelPosition="left" mt="xs" />
              <Switch
                label="Grabar la llamada completa"
                description={RECORD_FULL_CALL_HELP}
                {...form.getInputProps('record_full_call', { type: 'checkbox' })}
              />
            </>
          )}

          <Group justify="flex-end" mt="xs">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={update.isPending}>
              Guardar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
