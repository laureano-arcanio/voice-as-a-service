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
import { MemberPicker } from '@/features/team/MemberPicker';
import { ScheduleFields } from '@/features/team/ScheduleFields';
import { scheduleError } from '@/features/team/schedule';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateNumber } from './api';
import {
  type AnsweringDraft,
  FALLBACK_MESSAGE_DEFAULTS,
  FALLBACK_OPTIONS,
  MESSAGE_MAX,
  RING_FIRST_HELP,
  RING_FIRST_OPTIONS,
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
        {!m.user_id && <Badge color="gray">Solo en el celular</Badge>}
      </>
    );
  if (m.user_id) return <Badge color="gray">Solo en el panel</Badge>;
  return <Badge color="yellow">No le puede sonar</Badge>;
}

/** Etiqueta de un número y, asignado, quién atiende las entrantes: el equipo o el agente. */
export function EditNumberModal({ number, onClose }: { number: PhoneNumber; onClose: () => void }) {
  const update = useUpdateNumber();
  const assigned = !!number.client_id;
  const clientId = number.client_id ?? undefined;
  const agents = useAgents(clientId, false, assigned);
  const team = useTeam(clientId, assigned);
  const lock = useFeatureLock('direct_calls');
  const teamMode = (all: AnsweringDraft) => assigned && all.answer_mode === 'team';
  const form = useForm<AnsweringDraft>({
    initialValues: toAnsweringDraft(number),
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

  const messageDefault =
    v.team_fallback === 'hangup' ? FALLBACK_MESSAGE_DEFAULTS.hangup : FALLBACK_MESSAGE_DEFAULTS.voicemail;

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
                    description="Suena en el celular o en el panel de las personas que elijas. Estas llamadas se graban."
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
                    Suenan en este orden. Solo reciben llamadas las activas, con celular o usuario del panel.
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
                    <NumberInput
                      label="Timbre por persona"
                      description="Segundos antes de pasar a la siguiente."
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

                  <Divider label="Si nadie atiende o es fuera de horario" labelPosition="left" mt="xs" />
                  <Select
                    aria-label="Si nadie atiende"
                    data={FALLBACK_OPTIONS}
                    allowDeselect={false}
                    value={v.team_fallback}
                    onChange={(f) => {
                      if (f === 'agent' || f === 'voicemail' || f === 'hangup')
                        form.setFieldValue('team_fallback', f);
                    }}
                  />
                  {v.team_fallback === 'agent' ? (
                    <Select
                      label="Agente de respaldo"
                      description="Atiende con su apertura, sabiendo que nadie del equipo contestó."
                      placeholder="Elegí un agente"
                      data={agentOptions}
                      clearable
                      searchable
                      value={v.agent_id || null}
                      onChange={(id) => form.setFieldValue('agent_id', id ?? '')}
                      error={form.errors.agent_id}
                    />
                  ) : (
                    <Textarea
                      label="Mensaje"
                      description="Lo dice antes de cortar o de grabar. Vacío usa el de siempre."
                      placeholder={messageDefault}
                      autosize
                      minRows={2}
                      maxLength={MESSAGE_MAX}
                      {...form.getInputProps('team_fallback_message')}
                    />
                  )}
                </>
              )}
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
