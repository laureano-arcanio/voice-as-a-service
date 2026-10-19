import { Button, Divider, Group, Modal, Select, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import type { Campaign, CampaignPatch } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { usePhoneNumbers } from '@/features/numbers/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useUpdateCampaign, usePlan } from './api';
import { fieldApi, scheduleBody, scheduleErrors, scheduleFromCampaign } from './campaignForm';
import { ScheduleFields, VoiceRunFields, WebhookFields } from './CampaignFields';
import { PURPOSE } from './labels';

/** Edicion de una campaña en borrador o pausada: nombre, agente, horario y, en voz, el modo,
 * los reintentos, el numero de origen y la finalidad. */
export function EditCampaignModal({ campaign: c, onClose }: { campaign: Campaign; onClose: () => void }) {
  const voice = c.channel === 'voice';
  const update = useUpdateCampaign(c.id);
  const agents = useAgents(c.client_id, false);
  const numbers = usePhoneNumbers({ clientId: c.client_id }, voice);
  const plan = usePlan(c.client_id, voice);
  const cap = plan.data?.max_campaign_concurrency ?? null;
  const form = useForm({
    initialValues: {
      name: c.name,
      agent_id: c.agent_id ?? '',
      from_number_id: c.from_number_id ?? '',
      purpose: c.purpose ?? '',
      ...scheduleFromCampaign(c),
      mode: ((c.concurrency ?? 1) > 1 ? 'parallel' : 'sequential') as 'sequential' | 'parallel',
      concurrency: c.concurrency ?? 1,
      max_attempts: c.max_attempts ?? 3,
      retry_minutes: c.retry_minutes ?? 60,
      retry_on: (c.retry_on ?? []) as string[],
      callback_url: c.callback_url ?? '',
      callback_secret: '',
    },
    validate: (values) => ({
      ...(values.name.trim() ? {} : { name: 'Requerido' }),
      ...(voice && !values.agent_id ? { agent_id: 'Elegí el agente que llama' } : {}),
      ...(!values.callback_url.trim() || /^https:\/\//i.test(values.callback_url.trim())
        ? {}
        : { callback_url: 'Tiene que empezar con https://' }),
      ...scheduleErrors(values),
    }),
  });
  const api = fieldApi(form);

  return (
    <Modal opened onClose={onClose} title="Editar campaña" size="lg">
      <form
        onSubmit={form.onSubmit((v) => {
          const body: CampaignPatch = {
            name: v.name.trim(),
            agent_id: v.agent_id || null,
            ...scheduleBody(v, c.timezone),
          };
          if (voice) {
            body.concurrency = v.mode === 'parallel' ? v.concurrency : 1;
            body.max_attempts = v.max_attempts;
            body.retry_minutes = v.retry_minutes;
            body.retry_on = v.retry_on as ('no_answer' | 'busy' | 'voicemail' | 'failed')[];
            body.from_number_id = v.from_number_id || null;
          }
          if ((v.purpose || null) !== (c.purpose ?? null))
            body.purpose = (v.purpose || null) as CampaignPatch['purpose'];
          if ((v.callback_url.trim() || null) !== (c.callback_url ?? null))
            body.callback_url = v.callback_url.trim() || null;
          if (v.callback_secret.trim()) body.callback_secret = v.callback_secret.trim();
          update.mutate(body, {
            onSuccess: () => {
              notifySuccess('Campaña guardada.');
              onClose();
            },
            onError: (e) => notifyError(e, 'No se pudo guardar'),
          });
        })}
      >
        <Stack>
          <TextInput label="Nombre" {...form.getInputProps('name')} />
          <Select
            label={voice ? 'Agente que llama' : 'Agente que responde'}
            placeholder="El del número"
            data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
            clearable={!voice}
            searchable
            {...form.getInputProps('agent_id')}
            onChange={(val) => form.setFieldValue('agent_id', val ?? '')}
          />
          {voice && (
            <Select
              label="Número de origen"
              placeholder="El predeterminado"
              data={(numbers.data ?? [])
                .filter((n) => n.client_id === c.client_id)
                .map((n) => ({ value: n.id, label: n.label ? `${n.e164} · ${n.label}` : n.e164 }))}
              clearable
              {...form.getInputProps('from_number_id')}
              onChange={(val) => form.setFieldValue('from_number_id', val ?? '')}
            />
          )}
          <Select
            label="Finalidad"
            description={
              c.status === 'running' || c.status === 'scheduled'
                ? 'Para cambiarla, pausá la campaña.'
                : 'Cambiarla pide confirmar de nuevo el Registro No Llame al iniciar una comercial.'
            }
            placeholder="Sin definir"
            disabled={c.status === 'running' || c.status === 'scheduled'}
            data={Object.entries(PURPOSE).map(([value, label]) => ({ value, label }))}
            clearable
            {...form.getInputProps('purpose')}
            onChange={(val) => form.setFieldValue('purpose', val ?? '')}
          />
          <Divider label="Horario" labelPosition="left" mt="xs" />
          <ScheduleFields api={api} rateLabel={voice ? 'Llamadas por minuto' : 'Mensajes por minuto'} />
          {voice && (
            <>
              <Divider label="Llamadas" labelPosition="left" mt="xs" />
              <VoiceRunFields
                api={api}
                values={form.values}
                maxConcurrency={cap}
                onMode={(mode) => {
                  form.setFieldValue('mode', mode);
                  form.setFieldValue(
                    'concurrency',
                    mode === 'parallel' ? Math.min(Math.max(form.values.concurrency, 2), cap ?? 99) : 1,
                  );
                }}
              />
            </>
          )}
          <Divider label="Webhook" labelPosition="left" mt="xs" />
          <WebhookFields api={api} hasSecret={!!c.callback_url} />
          <Text size="xs" c="dimmed">
            El seguimiento por WhatsApp y los destinatarios se definen al crear la campaña; para sumar
            contactos usá "Agregar contactos".
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={update.isPending}>
              Guardar cambios
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
