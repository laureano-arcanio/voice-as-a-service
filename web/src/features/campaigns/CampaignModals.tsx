import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  Stack,
  Tabs,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import type { Campaign, ContactRejected, WaAccount, WaCampaignCreated } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { CsvFileInput, RejectedTable } from '@/features/contacts/ContactModals';
import { useWaTemplates } from '@/features/whatsapp/api';
import { TEMPLATE_CATEGORY } from '@/features/whatsapp/labels';
import { placeholderNumbers, templateBody } from '@/features/whatsapp/templates';
import { notifyError } from '@/lib/notify';
import { useAddContacts, useAddRecipients, useCreateWhatsAppCampaign } from './api';
import { csvHelp } from './labels';
import { RecipientsPicker } from './RecipientsPicker';
import { EMPTY_RECIPIENTS, type Recipients, recipientsEmpty } from './recipients';

/** Resultado de una carga: cuantos entraron y los salteados con el motivo. */
export function LoadResult({ result }: { result: { added: number; skipped: ContactRejected[] } }) {
  return (
    <Stack gap="xs">
      <Text size="sm">
        Se cargaron <b>{result.added}</b> contactos.
        {result.skipped.length > 0 && ` ${result.skipped.length} quedaron afuera:`}
      </Text>
      {result.skipped.length > 0 && <RejectedTable rows={result.skipped} />}
    </Stack>
  );
}

export function NewCampaignModal({ accounts, onClose }: { accounts: WaAccount[]; onClose: () => void }) {
  const create = useCreateWhatsAppCampaign();
  const navigate = useNavigate();
  const [created, setCreated] = useState<WaCampaignCreated | null>(null);
  const form = useForm({
    initialValues: {
      name: '',
      account_id: accounts.length === 1 ? accounts[0].id : '',
      template: '',
      agent_id: '',
      window_start: 9,
      window_end: 20,
      rate_per_minute: 20,
      csv: '',
    },
    validate: {
      name: (v) => (v.trim() ? null : 'Requerido'),
      account_id: (v) => (v ? null : 'Elegí un número'),
      template: (v) => (v ? null : 'Elegí una plantilla aprobada'),
      window_end: (v, values) => (v > values.window_start ? null : 'Tiene que ser después del inicio'),
    },
  });
  const account = accounts.find((a) => a.id === form.values.account_id);
  const templates = useWaTemplates(account?.id);
  const agents = useAgents(account?.client_id, false, !!account);
  const approved = (templates.data ?? []).filter((t) => t.status === 'APPROVED');
  const template = approved.find((t) => `${t.name}|${t.language}` === form.values.template);
  const body = template ? templateBody(template.components ?? []) : '';
  const vars = placeholderNumbers(body).length;

  if (created) {
    return (
      <Modal opened onClose={onClose} title="Campaña creada">
        <Stack>
          <LoadResult result={created} />
          <Text size="sm" c="dimmed">
            Queda en borrador: revisala y usá "Iniciar envío".
          </Text>
          <Group justify="flex-end">
            <Button onClick={() => navigate(`/campaigns/${created.campaign.id}`)}>Ver campaña</Button>
          </Group>
        </Stack>
      </Modal>
    );
  }

  return (
    <Modal opened onClose={onClose} title="Nueva campaña de WhatsApp" size="lg">
      <form
        onSubmit={form.onSubmit((v) => {
          const [name, language] = v.template.split('|');
          create.mutate(
            {
              account_id: v.account_id,
              name: v.name.trim(),
              template_name: name,
              template_language: language,
              agent_id: v.agent_id || null,
              window_start: v.window_start,
              window_end: v.window_end,
              rate_per_minute: v.rate_per_minute,
              csv: v.csv.trim() || null,
              recipients: [],
            },
            { onSuccess: setCreated, onError: (e) => notifyError(e, 'No se pudo crear la campaña') },
          );
        })}
      >
        <Stack>
          <TextInput
            label="Nombre"
            placeholder="Prospectos octubre"
            data-autofocus
            {...form.getInputProps('name')}
          />
          <Select
            label="Número que envía"
            data={accounts.map((a) => ({
              value: a.id,
              label: a.name ? `${a.display_phone_number} · ${a.name}` : a.display_phone_number,
            }))}
            allowDeselect={false}
            {...form.getInputProps('account_id')}
            onChange={(v) => {
              form.setFieldValue('account_id', v ?? '');
              form.setFieldValue('template', '');
              form.setFieldValue('agent_id', '');
            }}
          />
          <Select
            label="Plantilla"
            description="Solo las aprobadas por Meta. Se crean en WhatsApp → Plantillas."
            placeholder={templates.isFetching ? 'Leyendo de Meta…' : 'Elegí una plantilla'}
            disabled={!account}
            data={approved.map((t) => ({
              value: `${t.name}|${t.language}`,
              label: `${t.name} · ${t.language} · ${TEMPLATE_CATEGORY[t.category] ?? t.category}`,
            }))}
            nothingFoundMessage="No hay plantillas aprobadas"
            searchable
            {...form.getInputProps('template')}
          />
          {templates.isError && (
            <Alert color="red" icon={<IconInfoCircle size={18} />}>
              No se pudieron leer las plantillas de Meta.
            </Alert>
          )}
          {body && (
            <Paper p="sm" bg="var(--app-surface-2)">
              <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
                {body}
              </Text>
            </Paper>
          )}
          <Select
            label="Agente que responde"
            description="Atiende a los contactos que contestan, con el mensaje de la plantilla como inicio de la charla."
            placeholder={account ? `El del número (${account.agent_name ?? 'agente'})` : 'El del número'}
            disabled={!account}
            data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
            clearable
            searchable
            {...form.getInputProps('agent_id')}
            onChange={(v) => form.setFieldValue('agent_id', v ?? '')}
          />
          <Group grow align="flex-start">
            <NumberInput label="Desde (hora)" min={0} max={23} {...form.getInputProps('window_start')} />
            <NumberInput label="Hasta (hora)" min={1} max={24} {...form.getInputProps('window_end')} />
            <NumberInput
              label="Mensajes por minuto"
              min={1}
              max={600}
              {...form.getInputProps('rate_per_minute')}
            />
          </Group>
          <Textarea
            label="Contactos (CSV)"
            description={csvHelp(vars)}
            placeholder={'telefono,nombre\n351 555-1234,Ana'}
            autosize
            minRows={4}
            maxRows={10}
            classNames={{ input: 'mono' }}
            {...form.getInputProps('csv')}
          />
          <CsvFileInput onText={(t) => form.setFieldValue('csv', t)} />
          <Text size="xs" c="dimmed">
            Meta cobra cada plantilla entregada a la cuenta de WhatsApp Business del número (la de Marketing
            es la más cara). Conviene escribirles solo a quienes aceptaron recibir mensajes: si muchos
            bloquean o denuncian, Meta baja la calidad del número y su límite de envío. Quien responda "No me
            interesa" o "Baja" no recibe más campañas.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending}>
              Crear campaña
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

/** Suma contactos a una campaña en borrador o pausada. En WhatsApp el CSV sigue siendo posicional
 * ({{1}}, {{2}}...); las campañas de voz (y las de WhatsApp con las variables por nombre) toman los
 * contactos de la agenda. */
export function AddContactsModal({ campaign, onClose }: { campaign: Campaign; onClose: () => void }) {
  const whatsapp = campaign.channel === 'whatsapp';
  const byAgenda = !whatsapp || !campaign.template_params || !!campaign.param_names?.length;
  const addRecipients = useAddRecipients(campaign.id);
  const addContacts = useAddContacts(campaign.id);
  const [csv, setCsv] = useState('');
  const [picked, setPicked] = useState<Recipients>(EMPTY_RECIPIENTS);
  const [result, setResult] = useState<{ added: number; skipped: ContactRejected[] } | null>(null);
  const pending = addRecipients.isPending || addContacts.isPending;
  const fail = (e: unknown) => notifyError(e, 'No se pudieron cargar');

  const sendCsv = () =>
    whatsapp
      ? addRecipients.mutate({ csv, recipients: [] }, { onSuccess: setResult, onError: fail })
      : addContacts.mutate({ csv }, { onSuccess: setResult, onError: fail });
  const sendAgenda = () =>
    addContacts.mutate(
      {
        tags: picked.tags,
        contact_ids: picked.contactIds,
        csv: picked.csv.trim() || null,
      },
      { onSuccess: setResult, onError: fail },
    );

  const csvForm = (
    <Stack>
      <Textarea
        label="Contactos (CSV)"
        description={
          whatsapp
            ? csvHelp(campaign.template_params ?? 0)
            : 'Con encabezado: telefono (obligatorio), nombre, email y las demás columnas como datos del contacto. Quienes no estén en la agenda se agregan.'
        }
        placeholder={'telefono,nombre\n351 555-1234,Ana'}
        autosize
        minRows={6}
        maxRows={14}
        classNames={{ input: 'mono' }}
        value={csv}
        onChange={(e) => setCsv(e.currentTarget.value)}
        data-autofocus
      />
      <CsvFileInput onText={setCsv} />
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>
          Cancelar
        </Button>
        <Button disabled={!csv.trim()} loading={pending} onClick={sendCsv}>
          Agregar
        </Button>
      </Group>
    </Stack>
  );

  return (
    <Modal opened onClose={onClose} title="Agregar contactos" size="lg">
      {result ? (
        <Stack>
          <LoadResult result={result} />
          <Group justify="flex-end">
            <Button onClick={onClose}>Listo</Button>
          </Group>
        </Stack>
      ) : byAgenda ? (
        <Tabs defaultValue="agenda">
          <Tabs.List mb="md">
            <Tabs.Tab value="agenda">De la agenda</Tabs.Tab>
            <Tabs.Tab value="csv">Cargar un CSV</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="agenda">
            <Stack>
              <RecipientsPicker clientId={campaign.client_id} value={picked} onChange={setPicked} />
              <Group justify="flex-end">
                <Button variant="default" onClick={onClose}>
                  Cancelar
                </Button>
                <Button disabled={recipientsEmpty(picked)} loading={pending} onClick={sendAgenda}>
                  Agregar
                </Button>
              </Group>
            </Stack>
          </Tabs.Panel>
          <Tabs.Panel value="csv">{csvForm}</Tabs.Panel>
        </Tabs>
      ) : (
        csvForm
      )}
    </Modal>
  );
}
