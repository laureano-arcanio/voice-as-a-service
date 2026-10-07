import {
  Alert,
  Button,
  FileInput,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconFileUpload, IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import type { WaAccount, WaCampaignCreated, WaRecipientsAdded } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { useWaTemplates } from '@/features/whatsapp/api';
import { TEMPLATE_CATEGORY } from '@/features/whatsapp/labels';
import { placeholderNumbers, templateBody } from '@/features/whatsapp/templates';
import { notifyError } from '@/lib/notify';
import { useAddRecipients, useCreateCampaign } from './api';
import { csvHelp } from './labels';

const MAX_CSV_BYTES = 900_000;

/** Lee un archivo .csv en el textarea (hasta ~900 KB). */
function CsvFileInput({ onText }: { onText: (text: string) => void }) {
  return (
    <FileInput
      label="O subí un archivo"
      placeholder="contactos.csv"
      accept=".csv,text/csv,text/plain"
      leftSection={<IconFileUpload size={16} />}
      clearable
      onChange={(file) => {
        if (!file) return;
        if (file.size > MAX_CSV_BYTES) {
          notifyError(new Error('El archivo pasa de 900 KB: dividilo en partes.'));
          return;
        }
        void file.text().then(onText);
      }}
    />
  );
}

/** Resultado de una carga: cuantos entraron y los salteados con el motivo. */
export function LoadResult({ result }: { result: WaRecipientsAdded }) {
  return (
    <Stack gap="xs">
      <Text size="sm">
        Se cargaron <b>{result.added}</b> contactos.
        {result.skipped.length > 0 && ` ${result.skipped.length} quedaron afuera:`}
      </Text>
      {result.skipped.length > 0 && (
        <Table.ScrollContainer minWidth={420} mah={260}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fila</Table.Th>
                <Table.Th>Teléfono</Table.Th>
                <Table.Th>Motivo</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {result.skipped.map((s, i) => (
                <Table.Tr key={i}>
                  <Table.Td className="mono">{s.line ?? '–'}</Table.Td>
                  <Table.Td className="mono">{s.phone || '–'}</Table.Td>
                  <Table.Td>{s.reason}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}

export function NewCampaignModal({ accounts, onClose }: { accounts: WaAccount[]; onClose: () => void }) {
  const create = useCreateCampaign();
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

/** Suma contactos a una campaña en borrador o pausada. */
export function AddRecipientsModal({
  campaignId,
  vars,
  onClose,
}: {
  campaignId: string;
  vars: number;
  onClose: () => void;
}) {
  const add = useAddRecipients(campaignId);
  const [csv, setCsv] = useState('');
  const [result, setResult] = useState<WaRecipientsAdded | null>(null);
  return (
    <Modal opened onClose={onClose} title="Agregar contactos" size="lg">
      {result ? (
        <Stack>
          <LoadResult result={result} />
          <Group justify="flex-end">
            <Button onClick={onClose}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          <Textarea
            label="Contactos (CSV)"
            description={csvHelp(vars)}
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
            <Button
              disabled={!csv.trim()}
              loading={add.isPending}
              onClick={() =>
                add.mutate(
                  { csv, recipients: [] },
                  { onSuccess: setResult, onError: (e) => notifyError(e, 'No se pudieron cargar') },
                )
              }
            >
              Agregar
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
