import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconPlus, IconRefresh } from '@tabler/icons-react';
import type { WaAccount, WaTemplateIn } from '@/api/types';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useReadOnly } from '@/features/auth/readOnly';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCreateWaTemplate, useWaTemplates } from './api';
import { TEMPLATE_CATEGORY, TEMPLATE_STATUS } from './labels';
import {
  placeholderError,
  placeholderNumbers,
  TEMPLATE_NAME,
  normalizeTemplateName,
  templateBody,
} from './templates';
import { useState } from 'react';

// Respuesta rapida que da la baja de las campañas (app/whatsapp/campaigns.py, OPTOUT_TEXTS).
const OPTOUT_BUTTON = 'No me interesa';

const LANGUAGES = [
  { value: 'es_AR', label: 'Español (Argentina)' },
  { value: 'es', label: 'Español' },
  { value: 'es_MX', label: 'Español (México)' },
  { value: 'es_ES', label: 'Español (España)' },
  { value: 'en_US', label: 'Inglés (EE.UU.)' },
  { value: 'pt_BR', label: 'Portugués (Brasil)' },
];

// Autenticacion queda afuera: Meta le fija el texto (codigo + boton), no es un cuerpo libre.
const CATEGORIES = [
  { value: 'UTILITY', label: 'Utilidad: recordatorios, confirmaciones, avisos de cuenta' },
  { value: 'MARKETING', label: 'Marketing: promociones (la más cara)' },
];

function NewTemplateModal({ account, onClose }: { account: WaAccount; onClose: () => void }) {
  const create = useCreateWaTemplate();
  const form = useForm({
    initialValues: {
      name: '',
      language: 'es_AR',
      category: 'UTILITY',
      header_text: '',
      body: '',
      footer_text: '',
      examples: [] as string[],
      url_text: '',
      url: '',
      optout_button: false,
    },
    validate: {
      name: (v) => (TEMPLATE_NAME.test(v) ? null : 'Minúsculas, números y _'),
      body: (v) =>
        !v.trim() ? 'Requerido' : v.length > 1024 ? 'Hasta 1024 caracteres' : placeholderError(v),
      header_text: (v) => (v.includes('{{') ? 'El encabezado no admite variables' : null),
      footer_text: (v) => (v.includes('{{') ? 'El pie no admite variables' : null),
      url: (v, values) =>
        values.url_text.trim() && !/^https:\/\/\S+$/.test(v.trim()) ? 'Una dirección https://' : null,
      url_text: (v, values) => (values.url.trim() && !v.trim() ? 'El texto del botón' : null),
      examples: (v, values) =>
        v.slice(0, placeholderNumbers(values.body).length).some((e) => !e.trim())
          ? 'Hace falta un ejemplo para cada variable'
          : null,
    },
  });
  const vars = placeholderNumbers(form.values.body);

  return (
    <Modal opened onClose={onClose} title={`Nueva plantilla para ${account.display_phone_number}`} size="lg">
      <form
        onSubmit={form.onSubmit((v) => {
          const body: WaTemplateIn = {
            name: v.name,
            language: v.language,
            category: v.category as WaTemplateIn['category'],
            body: v.body,
            examples: vars.map((_, i) => (v.examples[i] ?? '').trim()),
            header_text: v.header_text.trim() || null,
            footer_text: v.footer_text.trim() || null,
            buttons: [
              ...(v.url_text.trim()
                ? [{ type: 'URL' as const, text: v.url_text.trim(), url: v.url.trim() }]
                : []),
              ...(v.optout_button ? [{ type: 'QUICK_REPLY' as const, text: OPTOUT_BUTTON }] : []),
            ],
          };
          create.mutate(
            { accountId: account.id, body },
            {
              onSuccess: (t) => {
                notifySuccess(`Plantilla ${v.name} enviada a Meta (${t.status ?? 'PENDING'}).`);
                onClose();
              },
              onError: (e) => notifyError(e, 'Meta no aceptó la plantilla'),
            },
          );
        })}
      >
        <Stack>
          <Group grow align="flex-start">
            <TextInput
              label="Nombre"
              description="Minúsculas, números y _ (ej. recordatorio_turno)."
              classNames={{ input: 'mono' }}
              data-autofocus
              {...form.getInputProps('name')}
              onChange={(e) => form.setFieldValue('name', normalizeTemplateName(e.currentTarget.value))}
            />
            <Select label="Idioma" data={LANGUAGES} searchable {...form.getInputProps('language')} />
          </Group>
          <Select
            label="Categoría"
            data={CATEGORIES}
            allowDeselect={false}
            {...form.getInputProps('category')}
          />
          <TextInput label="Encabezado (opcional)" maxLength={60} {...form.getInputProps('header_text')} />
          <Textarea
            label="Cuerpo"
            description="Variables {{1}}, {{2}}... en orden. Ej.: Hola {{1}}, te recordamos tu turno del {{2}}."
            autosize
            minRows={3}
            maxLength={1024}
            {...form.getInputProps('body')}
          />
          {vars.map((n, i) => (
            <TextInput
              key={n}
              label={`Ejemplo de {{${n}}}`}
              description={i === 0 ? 'Meta los usa para revisar la plantilla.' : undefined}
              maxLength={200}
              value={form.values.examples[i] ?? ''}
              onChange={(e) => {
                const next = [...form.values.examples];
                next[i] = e.currentTarget.value;
                form.setFieldValue('examples', next);
              }}
              error={i === 0 ? form.errors.examples : undefined}
            />
          ))}
          <TextInput label="Pie (opcional)" maxLength={60} {...form.getInputProps('footer_text')} />
          <Group grow align="flex-start">
            <TextInput
              label="Botón con enlace (opcional)"
              placeholder="Probar la demo"
              maxLength={25}
              {...form.getInputProps('url_text')}
            />
            <TextInput
              label="Dirección"
              placeholder="https://atentina.com.ar"
              {...form.getInputProps('url')}
            />
          </Group>
          <Checkbox
            label={`Botón "${OPTOUT_BUTTON}"`}
            description="Quien lo toca no recibe más campañas de este cliente. Recomendado en Marketing."
            {...form.getInputProps('optout_button', { type: 'checkbox' })}
          />
          <Text size="xs" c="dimmed">
            Meta revisa cada plantilla: queda "En revisión" y pasa a Aprobada o Rechazada (con el motivo).
            Hasta 100 altas por hora por cuenta.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending}>
              Crear
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

/** Plantillas de la WABA de una cuenta, en vivo desde Meta, con su estado de aprobacion. */
export function TemplatesCard({
  accounts,
  accountId,
  onSelect,
}: {
  accounts: WaAccount[];
  accountId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const account = accounts.find((a) => a.id === accountId);
  const templates = useWaTemplates(account && account.status !== 'disconnected' ? account.id : undefined);
  const [creating, setCreating] = useState(false);
  const readOnly = useReadOnly();

  return (
    <Card id="wa-templates" mt="md">
      <Group justify="space-between" mb="md" gap="sm">
        <Title order={4}>Plantillas</Title>
        <Group gap="xs">
          <Select
            placeholder="Elegí un número"
            data={accounts.map((a) => ({
              value: a.id,
              label: a.name ? `${a.display_phone_number} · ${a.name}` : a.display_phone_number,
            }))}
            value={accountId}
            onChange={onSelect}
            w={280}
            aria-label="Número de las plantillas"
          />
          <Tooltip label="Releer de Meta" withArrow>
            <ActionIcon
              variant="default"
              size="lg"
              aria-label="Releer plantillas"
              disabled={!account || account.status === 'disconnected'}
              loading={templates.isFetching}
              onClick={() => void templates.refetch()}
            >
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
          <Button
            variant="default"
            leftSection={<IconPlus size={16} />}
            disabled={!account || account.status === 'disconnected' || readOnly}
            onClick={() => setCreating(true)}
          >
            Nueva plantilla
          </Button>
        </Group>
      </Group>
      <Text size="sm" c="dimmed" mb="sm">
        Los mensajes que inicia el negocio (fuera de las 24 h desde el último mensaje del contacto) solo salen
        con una plantilla aprobada por Meta. Se comparten entre los números de la misma cuenta de WhatsApp
        Business.
      </Text>
      {!account ? (
        <EmptyState>Elegí un número para ver sus plantillas.</EmptyState>
      ) : account.status === 'disconnected' ? (
        <EmptyState>El número está desconectado: volvé a conectarlo para ver sus plantillas.</EmptyState>
      ) : (
        <QueryState query={templates}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState>Esta cuenta no tiene plantillas.</EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={760}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>Idioma</Table.Th>
                      <Table.Th>Categoría</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Cuerpo</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((t) => {
                      const st = TEMPLATE_STATUS[t.status] ?? { label: t.status || '–', color: 'gray' };
                      return (
                        <Table.Tr key={t.id}>
                          <Table.Td>
                            <Text size="sm" className="mono">
                              {t.name}
                            </Text>
                          </Table.Td>
                          <Table.Td>{t.language}</Table.Td>
                          <Table.Td>{TEMPLATE_CATEGORY[t.category] ?? t.category}</Table.Td>
                          <Table.Td>
                            <Badge color={st.color}>{st.label}</Badge>
                            {t.rejected_reason && (
                              <Text size="xs" c="red" mt={2}>
                                {t.rejected_reason}
                              </Text>
                            )}
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" lineClamp={2} maw={360}>
                              {templateBody(t.components ?? [])}
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      )}
      {creating && account && <NewTemplateModal account={account} onClose={() => setCreating(false)} />}
    </Card>
  );
}
