import {
  Alert,
  Button,
  Checkbox,
  Divider,
  Group,
  Modal,
  MultiSelect,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import type { CampaignCreated, CampaignIn } from '@/api/types';
import { CopyIcon } from '@/components/Copy';
import { useAgents } from '@/features/agents/api';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { RejectedTable } from '@/features/contacts/ContactModals';
import { usePhoneNumbers } from '@/features/numbers/api';
import { useVoices } from '@/features/voices/api';
import { useWaAccounts, useWaTemplates } from '@/features/whatsapp/api';
import { placeholderNumbers, templateBody } from '@/features/whatsapp/templates';
import { notifyError } from '@/lib/notify';
import { useCreateCampaign, usePlan } from './api';
import { fieldApi, scheduleBody, scheduleDefaults, scheduleErrors, voiceRunDefaults } from './campaignForm';
import { ScheduleFields, VoiceRunFields, WebhookFields } from './CampaignFields';
import { CONTACT_RESULT, PURPOSE } from './labels';
import { RecipientsPicker } from './RecipientsPicker';
import { EMPTY_RECIPIENTS, type Recipients, recipientsCount, recipientsEmpty } from './recipients';
import { DEFAULT_TZ } from './schedule';

const FOLLOWUP_AFTER = ['no_answer', 'busy', 'voicemail', 'failed'] as const;

/** Datos que el aviso muestra una sola vez, y lo que no entro. */
function Created({ result, onClose }: { result: CampaignCreated; onClose: () => void }) {
  const navigate = useNavigate();
  const c = result.campaign;
  return (
    <Stack>
      <Text size="sm">
        Se cargaron <b>{result.added}</b> contactos.
        {result.skipped.length > 0 && ` ${result.skipped.length} quedaron afuera:`}
      </Text>
      {result.skipped.length > 0 && <RejectedTable rows={result.skipped} />}
      {c.callback_secret && (
        <Alert color="yellow" icon={<IconInfoCircle size={18} />} title="Secreto del webhook">
          <Group gap="xs" wrap="nowrap">
            <Text className="mono" size="sm" style={{ wordBreak: 'break-all' }}>
              {c.callback_secret}
            </Text>
            <CopyIcon value={c.callback_secret} label="Copiar el secreto" />
          </Group>
          <Text size="xs" mt={4}>
            Guardalo ahora: no se vuelve a mostrar. Con él se firman los avisos (X-Atentina-Signature).
          </Text>
        </Alert>
      )}
      <Text size="sm" c="dimmed">
        {c.status === 'draft'
          ? 'Queda en borrador: revisala y usá "Iniciar campaña".'
          : c.status === 'scheduled'
            ? 'Quedó programada: arranca sola a la hora indicada.'
            : 'Ya está en curso.'}
      </Text>
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>
          Cerrar
        </Button>
        <Button
          onClick={() => {
            onClose();
            navigate(`/campaigns/${c.id}`);
          }}
        >
          Ver campaña
        </Button>
      </Group>
    </Stack>
  );
}

export function VoiceCampaignModal({
  clientId: initialClient,
  onClose,
}: {
  clientId?: string;
  onClose: () => void;
}) {
  const isAdmin = useIsAdmin();
  const create = useCreateCampaign();
  const clients = useClients(isAdmin);
  const [created, setCreated] = useState<CampaignCreated | null>(null);
  const [recipients, setPickedRecipients] = useState<Recipients>(EMPTY_RECIPIENTS);
  const [noRecipients, setNoRecipients] = useState(false);
  const setRecipients = (r: Recipients) => {
    setPickedRecipients(r);
    setNoRecipients(false);
  };
  const form = useForm({
    initialValues: {
      client_id: initialClient ?? '',
      name: '',
      agent_id: '',
      from_number_id: '',
      voice: '',
      purpose: '',
      registry_checked: false,
      ...scheduleDefaults(),
      ...voiceRunDefaults(),
      followup: false,
      f_account: '',
      f_template: '',
      f_after: ['no_answer', 'busy', 'voicemail'] as string[],
      f_params: [] as string[],
      f_agent: '',
      callback_url: '',
      callback_secret: '',
    },
    validate: (values) => ({
      ...(isAdmin && !values.client_id ? { client_id: 'Elegí un cliente' } : {}),
      ...(values.name.trim() ? {} : { name: 'Requerido' }),
      ...(values.agent_id ? {} : { agent_id: 'Elegí el agente que llama' }),
      ...(!values.callback_url.trim() || /^https:\/\//i.test(values.callback_url.trim())
        ? {}
        : { callback_url: 'Tiene que empezar con https://' }),
      ...scheduleErrors(values),
    }),
  });
  const api = fieldApi(form);
  const v = form.values;
  const client = isAdmin ? v.client_id || undefined : undefined;
  const ready = !isAdmin || !!v.client_id;

  const plan = usePlan(client, ready);
  const agents = useAgents(client, false, ready);
  const numbers = usePhoneNumbers({ clientId: client }, ready);
  const voices = useVoices();
  const accounts = useWaAccounts(client);
  const connected = (accounts.data ?? []).filter((a) => a.active && a.status === 'connected');
  const account = connected.find((a) => a.id === v.f_account);
  const templates = useWaTemplates(account?.id);
  const approved = (templates.data ?? []).filter((t) => t.status === 'APPROVED');
  const template = approved.find((t) => `${t.name}|${t.language}` === v.f_template);
  const placeholders = template ? placeholderNumbers(templateBody(template.components ?? [])) : [];

  const p = plan.data;
  const hasVoice = !p || p.channels.includes('voice');
  const cap = p?.max_campaign_concurrency ?? null;
  const monthFull =
    !!p && p.max_campaigns_per_month != null && p.campaigns_started >= p.max_campaigns_per_month;
  const csvRows = recipientsCount(recipients).rows;
  const overContacts =
    !!p &&
    p.max_campaign_contacts != null &&
    csvRows + recipients.contactIds.length > p.max_campaign_contacts;
  const followupBlocked = !!p && !p.followup;
  const comercial = v.purpose === 'comercial';
  const startBlock = !hasVoice
    ? 'Tu plan no incluye campañas por llamadas'
    : monthFull
      ? `Tu plan permite ${p?.max_campaigns_per_month} campañas por mes y ya iniciaste ${p?.campaigns_started}`
      : comercial && !v.registry_checked
        ? 'Confirmá que filtraste la lista contra el Registro No Llame'
        : null;

  const submit = (start: boolean) =>
    form.onSubmit((values) => {
      if (recipientsEmpty(recipients)) {
        setNoRecipients(true);
        return;
      }
      if (values.followup && (!values.f_account || !values.f_template || values.f_after.length === 0)) {
        if (!values.f_account) form.setFieldError('f_account', 'Elegí un número');
        else if (!values.f_template) form.setFieldError('f_template', 'Elegí una plantilla');
        else form.setFieldError('f_after', 'Elegí al menos un resultado');
        return;
      }
      const [templateName, templateLanguage] = values.f_template.split('|');
      create.mutate(
        {
          channel: 'voice',
          client_id: isAdmin ? values.client_id : null,
          name: values.name.trim(),
          agent_id: values.agent_id,
          from_number_id: values.from_number_id || null,
          voice: values.voice || null,
          purpose: (values.purpose || null) as CampaignIn['purpose'],
          no_call_registry_checked: values.registry_checked,
          ...scheduleBody(values, DEFAULT_TZ),
          concurrency: values.mode === 'parallel' ? values.concurrency : 1,
          max_attempts: values.max_attempts,
          retry_minutes: values.retry_minutes,
          retry_on: values.retry_on as ('no_answer' | 'busy' | 'voicemail' | 'failed')[],
          followup: values.followup
            ? {
                after: values.f_after as ('no_answer' | 'busy' | 'voicemail' | 'failed')[],
                account_id: values.f_account,
                template_name: templateName,
                template_language: templateLanguage,
                params: placeholders.map((_, i) => values.f_params[i]?.trim() ?? ''),
                agent_id: values.f_agent || null,
              }
            : null,
          callback_url: values.callback_url.trim() || null,
          callback_secret: values.callback_secret.trim() || null,
          tags: recipients.tags,
          contact_ids: recipients.contactIds,
          csv: recipients.csv.trim() || null,
          start,
        },
        { onSuccess: setCreated, onError: (e) => notifyError(e, 'No se pudo crear la campaña') },
      );
    });

  if (created)
    return (
      <Modal opened onClose={onClose} title="Campaña creada">
        <Created result={created} onClose={onClose} />
      </Modal>
    );

  const starting = v.starts_at ? 'Crear y programar' : 'Crear e iniciar';
  const disabled = !ready || !hasVoice;

  return (
    <Modal opened onClose={onClose} title="Nueva campaña de llamadas" size="xl">
      <form onSubmit={submit(false)}>
        <Stack>
          {!hasVoice && (
            <Alert color="yellow" icon={<IconInfoCircle size={18} />}>
              Tu plan ({p?.tier_name}) no incluye campañas por llamadas. Podés ver las opciones en la pantalla
              Plan.
            </Alert>
          )}
          {isAdmin && (
            <Select
              label="Cliente"
              placeholder="Elegí un cliente"
              data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
              searchable
              {...form.getInputProps('client_id')}
              onChange={(val) => {
                form.setFieldValue('client_id', val ?? '');
                for (const k of ['agent_id', 'from_number_id', 'f_account', 'f_template', 'f_agent'] as const)
                  form.setFieldValue(k, '');
                setRecipients(EMPTY_RECIPIENTS);
              }}
            />
          )}
          <TextInput
            label="Nombre"
            placeholder="Cobranza octubre"
            disabled={disabled}
            data-autofocus
            {...form.getInputProps('name')}
          />
          <Group grow align="flex-start">
            <Select
              label="Agente que llama"
              placeholder="Elegí un agente"
              disabled={disabled}
              data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
              searchable
              nothingFoundMessage="No hay agentes"
              {...form.getInputProps('agent_id')}
            />
            <Select
              label="Número de origen"
              description="El que ve quien recibe la llamada."
              placeholder="El predeterminado"
              disabled={disabled}
              data={(numbers.data ?? [])
                .filter((n) => !isAdmin || n.client_id === client)
                .map((n) => ({ value: n.id, label: n.label ? `${n.e164} · ${n.label}` : n.e164 }))}
              clearable
              {...form.getInputProps('from_number_id')}
              onChange={(val) => form.setFieldValue('from_number_id', val ?? '')}
            />
            <Select
              label="Voz"
              placeholder="La del agente"
              disabled={disabled}
              data={(voices.data ?? []).map((x) => ({ value: x.nombre, label: x.nombre }))}
              clearable
              searchable
              {...form.getInputProps('voice')}
              onChange={(val) => form.setFieldValue('voice', val ?? '')}
            />
          </Group>
          <Select
            label="Finalidad"
            description="Para qué se llama. Las comerciales piden confirmar el Registro No Llame antes de iniciar."
            placeholder="Sin definir"
            disabled={disabled}
            data={Object.entries(PURPOSE).map(([value, label]) => ({ value, label }))}
            clearable
            {...form.getInputProps('purpose')}
            onChange={(val) => form.setFieldValue('purpose', val ?? '')}
          />
          {comercial && (
            <Checkbox
              label="Confirmo que filtré la lista contra el Registro No Llame"
              description="Las llamadas de publicidad a inscriptos están prohibidas (Ley 26.951). La responsabilidad de la lista es del cliente."
              {...form.getInputProps('registry_checked', { type: 'checkbox' })}
            />
          )}

          <Divider label="Destinatarios" labelPosition="left" mt="xs" />
          {ready ? (
            <RecipientsPicker clientId={client} value={recipients} onChange={setRecipients} />
          ) : (
            <Text size="sm" c="dimmed">
              Elegí un cliente para ver sus contactos.
            </Text>
          )}
          {noRecipients && (
            <Text size="sm" c="red">
              Elegí a quién llamar: etiquetas, contactos o un CSV.
            </Text>
          )}
          {overContacts && (
            <Alert color="yellow" icon={<IconInfoCircle size={18} />}>
              Tu plan permite {p?.max_campaign_contacts} contactos por campaña: lo que sobre queda afuera o no
              se podrá iniciar.
            </Alert>
          )}

          <Divider label="Horario" labelPosition="left" mt="xs" />
          <ScheduleFields api={api} rateLabel="Llamadas por minuto" rateHelp="Cuántas arranca como máximo." />

          <Divider label="Llamadas" labelPosition="left" mt="xs" />
          <VoiceRunFields
            api={api}
            values={v}
            maxConcurrency={cap}
            onMode={(mode) => {
              form.setFieldValue('mode', mode);
              form.setFieldValue('concurrency', mode === 'parallel' ? Math.min(2, cap ?? 2) : 1);
            }}
          />

          <Divider label="Seguimiento por WhatsApp" labelPosition="left" mt="xs" />
          <Tooltip
            label="Tu plan no incluye el seguimiento por WhatsApp"
            withArrow
            disabled={!followupBlocked}
          >
            <Switch
              label="Escribirle por WhatsApp a quien no atendió"
              description="Después del último intento, con una plantilla aprobada por Meta."
              disabled={disabled || followupBlocked}
              {...form.getInputProps('followup', { type: 'checkbox' })}
            />
          </Tooltip>
          {v.followup && (
            <Stack gap="sm">
              <Group grow align="flex-start">
                <Select
                  label="Número de WhatsApp"
                  placeholder={connected.length ? 'Elegí un número' : 'No hay números conectados'}
                  data={connected.map((a) => ({ value: a.id, label: a.display_phone_number }))}
                  {...form.getInputProps('f_account')}
                  onChange={(val) => {
                    form.setFieldValue('f_account', val ?? '');
                    form.setFieldValue('f_template', '');
                  }}
                />
                <Select
                  label="Plantilla"
                  placeholder={templates.isFetching ? 'Leyendo de Meta…' : 'Elegí una plantilla'}
                  disabled={!account}
                  data={approved.map((t) => ({
                    value: `${t.name}|${t.language}`,
                    label: `${t.name} · ${t.language}`,
                  }))}
                  nothingFoundMessage="No hay plantillas aprobadas"
                  searchable
                  {...form.getInputProps('f_template')}
                />
              </Group>
              {template && (
                <Text size="sm" c="dimmed" style={{ whiteSpace: 'pre-line' }}>
                  {templateBody(template.components ?? [])}
                </Text>
              )}
              {placeholders.map((n, i) => (
                <TextInput
                  key={n}
                  label={`Dato para {{${n}}}`}
                  description="El nombre del dato del contacto que completa la variable."
                  placeholder={i === 0 ? 'nombre' : 'deuda'}
                  value={v.f_params[i] ?? ''}
                  onChange={(e) => {
                    const next = [...v.f_params];
                    next[i] = e.currentTarget.value;
                    form.setFieldValue('f_params', next);
                  }}
                />
              ))}
              <MultiSelect
                label="Se manda si el resultado fue"
                data={FOLLOWUP_AFTER.map((r) => ({ value: r, label: CONTACT_RESULT[r].label }))}
                {...form.getInputProps('f_after')}
              />
              <Select
                label="Agente que responde"
                description="Atiende a quien conteste el WhatsApp."
                placeholder="El de la campaña"
                data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
                clearable
                searchable
                {...form.getInputProps('f_agent')}
                onChange={(val) => form.setFieldValue('f_agent', val ?? '')}
              />
            </Stack>
          )}

          <Divider label="Webhook" labelPosition="left" mt="xs" />
          <WebhookFields api={api} />

          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" variant="default" loading={create.isPending} disabled={disabled}>
              Guardar borrador
            </Button>
            <Tooltip label={startBlock} withArrow multiline w={280} disabled={!startBlock}>
              <Button
                loading={create.isPending}
                disabled={disabled}
                data-disabled={!!startBlock || undefined}
                onClick={(e) => {
                  e.preventDefault();
                  if (startBlock) return;
                  void submit(true)();
                }}
              >
                {starting}
              </Button>
            </Tooltip>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
