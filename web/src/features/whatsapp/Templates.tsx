import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  List,
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
import { IconEdit, IconPlus, IconRefresh, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { WaAccount, WaTemplate, WaTemplateButton, WaTemplateEdit, WaTemplateIn } from '@/api/types';
import { EmptyState, QueryState } from '@/components/QueryState';
import { ModalSelect } from '@/components/ModalDropdown';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  TemplateInUseError,
  useCreateWaTemplate,
  useDeleteWaTemplate,
  useEditWaTemplate,
  useWaTemplates,
  type WaTemplateUsage,
} from './api';
import { TEMPLATE_CATEGORY, TEMPLATE_STATUS } from './labels';
import {
  placeholderError,
  placeholderNumbers,
  TEMPLATE_NAME,
  normalizeTemplateName,
  templateBody,
} from './templates';

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

// Meta solo deja editar aprobadas, rechazadas o pausadas (docs/features/WHATSAPP.md).
const EDITABLE_STATUSES = new Set(['APPROVED', 'REJECTED', 'PAUSED']);

/** Valores del formulario: crea una plantilla de texto o edita una existente. */
interface TemplateForm {
  name: string;
  language: string;
  category: string;
  header_text: string;
  body: string;
  footer_text: string;
  examples: string[];
  url_text: string;
  url: string;
  quick_text: string;
  optout_button: boolean;
}

const EMPTY_FORM: TemplateForm = {
  name: '',
  language: 'es_AR',
  category: 'UTILITY',
  header_text: '',
  body: '',
  footer_text: '',
  examples: [],
  url_text: '',
  url: '',
  quick_text: '',
  optout_button: false,
};

/** Plantilla de Meta a valores del formulario, o null si esta pantalla no sabe cargarla
 * (HEADER de media, botones que el formulario no tiene, Autenticación). Editar reemplaza
 * TODOS los componentes: lo que no se muestra se perdería. */
function templateToForm(t: WaTemplate): TemplateForm | null {
  if (t.category !== 'UTILITY' && t.category !== 'MARKETING') return null;
  const form: TemplateForm = { ...EMPTY_FORM, name: t.name, language: t.language, category: t.category };
  const freeReplies: string[] = [];
  let urls = 0;
  for (const c of t.components ?? []) {
    const type = String(c.type ?? '').toUpperCase();
    if (type === 'HEADER') {
      // Solo texto: imagen, video o documento no los carga el formulario.
      if (String(c.format ?? 'TEXT').toUpperCase() !== 'TEXT' || typeof c.text !== 'string' || c.example)
        return null;
      form.header_text = c.text;
    } else if (type === 'BODY') {
      if (typeof c.text !== 'string') return null;
      form.body = c.text;
      const rows = (c.example as { body_text?: unknown } | undefined)?.body_text;
      if (Array.isArray(rows) && Array.isArray(rows[0]))
        form.examples = (rows[0] as unknown[]).map((x) => (typeof x === 'string' ? x : ''));
    } else if (type === 'FOOTER') {
      if (typeof c.text !== 'string') return null;
      form.footer_text = c.text;
    } else if (type === 'BUTTONS') {
      if (!Array.isArray(c.buttons)) return null;
      for (const b of c.buttons) {
        if (!b || typeof b !== 'object' || typeof b.text !== 'string') return null;
        if (b.type === 'URL') {
          if (typeof b.url !== 'string' || ++urls > 1) return null;
          form.url_text = b.text;
          form.url = b.url;
        } else if (b.type === 'QUICK_REPLY') {
          if (b.text === OPTOUT_BUTTON) form.optout_button = true;
          else freeReplies.push(b.text);
        } else return null; // teléfono, copiar código, carrusel...
      }
    } else return null;
  }
  if (freeReplies.length > 1) return null;
  form.quick_text = freeReplies[0] ?? '';
  return form;
}

/** Por qué esta pantalla no puede editar la plantilla, o null si puede. */
function editBlocked(t: WaTemplate): string | null {
  if (!EDITABLE_STATUSES.has(t.status)) return 'Meta solo deja editar aprobadas, rechazadas o pausadas';
  if (t.category !== 'UTILITY' && t.category !== 'MARKETING') return 'Autenticación tiene el texto fijo de Meta';
  return templateToForm(t) ? null : 'Tiene componentes que esta pantalla no edita (imagen, video, carrusel u otros botones)';
}

/** Por qué no se puede borrar, o null si se puede. */
function deleteBlocked(t: WaTemplate): string | null {
  if (t.status === 'DISABLED') return 'Meta no borra una plantilla deshabilitada';
  if (t.status === 'PENDING_DELETION') return 'Ya está marcada para borrado: Meta la reintenta hasta 30 días';
  return null;
}

/** Botones del formulario a los de la API (crear y editar arman igual). */
function formButtons(v: TemplateForm): WaTemplateButton[] {
  return [
    ...(v.url_text.trim() ? [{ type: 'URL' as const, text: v.url_text.trim(), url: v.url.trim() }] : []),
    ...(v.quick_text.trim() ? [{ type: 'QUICK_REPLY' as const, text: v.quick_text.trim() }] : []),
    // Si el rótulo libre ya es el de la baja, no se repite.
    ...(v.optout_button && v.quick_text.trim() !== OPTOUT_BUTTON
      ? [{ type: 'QUICK_REPLY' as const, text: OPTOUT_BUTTON }]
      : []),
  ];
}

function TemplateModal({
  account,
  template,
  onClose,
}: {
  account: WaAccount;
  /** Sin template: alta. Con template: edición en el lugar de Meta. */
  template?: WaTemplate;
  onClose: () => void;
}) {
  const create = useCreateWaTemplate();
  const edit = useEditWaTemplate();
  const initial = template === undefined ? EMPTY_FORM : (templateToForm(template) ?? EMPTY_FORM);
  const form = useForm({
    initialValues: initial,
    validate: {
      name: (v) => (TEMPLATE_NAME.test(v) ? null : 'Minúsculas, números y _'),
      body: (v) =>
        !v.trim() ? 'Requerido' : v.length > 1024 ? 'Hasta 1024 caracteres' : placeholderError(v),
      header_text: (v) => (v.includes('{{') ? 'El encabezado no admite variables' : null),
      footer_text: (v) => (v.includes('{{') ? 'El pie no admite variables' : null),
      url: (v, values) =>
        values.url_text.trim() && !/^https:\/\/\S+$/.test(v.trim()) ? 'Una dirección https://' : null,
      url_text: (v, values) => (values.url.trim() && !v.trim() ? 'El texto del botón' : null),
      quick_text: (v) => (v.includes('{{') ? 'El botón no admite variables' : null),
      examples: (v, values) =>
        v.slice(0, placeholderNumbers(values.body).length).some((e) => !e.trim())
          ? 'Hace falta un ejemplo para cada variable'
          : null,
    },
  });
  const vars = placeholderNumbers(form.values.body);
  // Inmutables al editar: el nombre, el idioma y (en una aprobada) la categoría.
  const categoryLocked = template?.status === 'APPROVED';
  const varsChanged = template !== undefined && vars.length !== placeholderNumbers(initial.body).length;
  const metaRules =
    template === undefined
      ? 'Meta revisa cada plantilla: queda "En revisión" y pasa a Aprobada o Rechazada (con el motivo).'
      : template.status === 'APPROVED'
        ? 'Meta vuelve a revisar el cambio: si lo rechaza, la plantilla queda Rechazada y la versión anterior no vuelve. Las aprobadas se editan 1 vez cada 24 h (10 cada 30 días).'
        : template.status === 'REJECTED'
          ? 'Meta vuelve a revisar el cambio: si lo rechaza, la plantilla queda Rechazada y la versión anterior no vuelve. Las rechazadas se editan sin tope.'
          : 'Meta vuelve a revisar el cambio: si lo rechaza, la plantilla queda Rechazada y la versión anterior no vuelve.';

  return (
    <Modal
      opened
      onClose={onClose}
      title={template === undefined ? `Nueva plantilla para ${account.display_phone_number}` : `Editar ${template.name}`}
      size="lg"
    >
      <form
        onSubmit={form.onSubmit((v) => {
          if (template === undefined) {
            const body: WaTemplateIn = {
              name: v.name,
              language: v.language,
              category: v.category as WaTemplateIn['category'],
              body: v.body,
              examples: vars.map((_, i) => (v.examples[i] ?? '').trim()),
              header_text: v.header_text.trim() || null,
              footer_text: v.footer_text.trim() || null,
              buttons: formButtons(v),
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
          } else {
            const body: WaTemplateEdit = {
              // Aprobada: Meta rechaza el cambio de categoría, no se manda.
              category: categoryLocked ? null : (v.category as WaTemplateEdit['category']),
              body: v.body,
              examples: vars.map((_, i) => (v.examples[i] ?? '').trim()),
              header_text: v.header_text.trim() || null,
              footer_text: v.footer_text.trim() || null,
              buttons: formButtons(v),
            };
            edit.mutate(
              { accountId: account.id, templateId: template.id, body },
              {
                onSuccess: () => {
                  notifySuccess(`Plantilla ${v.name} editada: Meta la vuelve a revisar.`);
                  onClose();
                },
                onError: (e) => notifyError(e, 'Meta no aceptó la edición'),
              },
            );
          }
        })}
      >
        <Stack>
          <Group grow align="flex-start">
            <TextInput
              label="Nombre"
              description={template === undefined ? 'Minúsculas, números y _ (ej. recordatorio_turno).' : 'Meta no permite cambiarlo.'}
              inputWrapperOrder={['label', 'input', 'description', 'error']}
              classNames={{ input: 'mono' }}
              data-autofocus={template === undefined || undefined}
              disabled={template !== undefined}
              {...form.getInputProps('name')}
              onChange={
                template === undefined
                  ? (e) => form.setFieldValue('name', normalizeTemplateName(e.currentTarget.value))
                  : undefined
              }
            />
            <ModalSelect
              label="Idioma"
              data={LANGUAGES}
              searchable
              disabled={template !== undefined}
              {...form.getInputProps('language')}
            />
          </Group>
          <ModalSelect
            label="Categoría"
            data={CATEGORIES}
            allowDeselect={false}
            disabled={categoryLocked}
            description={categoryLocked ? 'Meta no permite cambiar la categoría de una plantilla aprobada.' : undefined}
            {...form.getInputProps('category')}
          />
          <TextInput label="Encabezado (opcional)" maxLength={60} {...form.getInputProps('header_text')} />
          <Textarea
            label="Cuerpo"
            description="Variables {{1}}, {{2}}... en orden. Ej.: Hola {{1}}, te recordamos tu turno del {{2}}."
            autosize
            minRows={3}
            maxLength={1024}
            data-autofocus={template !== undefined || undefined}
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
          <TextInput
            label="Botón de respuesta rápida (opcional)"
            description="Quien lo toca envía ese texto como respuesta. Sirve, por ejemplo, para que una persona del equipo acepte un pedido con «Aceptar»."
            placeholder="Aceptar"
            maxLength={25}
            {...form.getInputProps('quick_text')}
          />
          <Checkbox
            label={`Botón "${OPTOUT_BUTTON}"`}
            description="Quien lo toca no recibe más campañas de este cliente. Recomendado en Marketing."
            {...form.getInputProps('optout_button', { type: 'checkbox' })}
          />
          {template?.status === 'REJECTED' && template.rejected_reason && (
            <Text size="xs" c="red">
              Motivo del rechazo: {template.rejected_reason}
            </Text>
          )}
          {varsChanged && (
            <Text size="xs" c="orange">
              Cambiás la cantidad de variables: si una campaña o un área usa esta plantilla, sus parámetros van por
              posición y los que falten quedan como texto literal en el mensaje.
            </Text>
          )}
          <Text size="xs" c="dimmed">{metaRules} Hasta 100 operaciones con plantillas por hora.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={create.isPending || edit.isPending}>
              {template === undefined ? 'Crear' : 'Guardar'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function DeleteTemplateModal({
  account,
  template,
  onClose,
}: {
  account: WaAccount;
  template: WaTemplate;
  onClose: () => void;
}) {
  const del = useDeleteWaTemplate();
  // Usos del 409 template_in_use: mientras es null, la confirmación normal.
  const [usages, setUsages] = useState<WaTemplateUsage[] | null>(null);
  const [conflict, setConflict] = useState('');

  const remove = (force: boolean) =>
    del.mutate(
      { accountId: account.id, templateId: template.id, force },
      {
        onSuccess: () => {
          notifySuccess(`Plantilla ${template.name} borrada de Meta.`);
          onClose();
        },
        onError: (e) => {
          if (e instanceof TemplateInUseError) {
            setUsages(e.usages);
            setConflict(e.message);
          } else {
            notifyError(e, 'No se pudo borrar la plantilla');
          }
        },
      },
    );

  return (
    <Modal opened onClose={onClose} title={`Borrar ${template.name}`} size="md">
      <Stack>
        {usages === null ? (
          <>
            <Text size="sm">
              Se borra de Meta la plantilla <b>{template.name}</b> ({template.language}) del número{' '}
              {account.display_phone_number}. No se puede deshacer.
            </Text>
            {template.status === 'APPROVED' && (
              <Text size="sm" c="orange">
                Al borrar una plantilla aprobada, crear otra con el nombre <b>{template.name}</b> queda bloqueado
                durante 30 días.
              </Text>
            )}
            <Group justify="flex-end">
              <Button variant="default" onClick={onClose}>
                Cancelar
              </Button>
              <Button color="red" loading={del.isPending} onClick={() => remove(false)}>
                Borrar
              </Button>
            </Group>
          </>
        ) : (
          <>
            <Text size="sm">No se puede borrar porque la usan:</Text>
            <List size="sm" withPadding>
              {usages.map((u) => (
                <List.Item key={`${u.kind}:${u.id}`}>
                  {u.kind === 'campaign' ? 'la campaña' : 'el área'} <b>{u.name}</b>
                </List.Item>
              ))}
            </List>
            {usages.length === 0 && <Text size="sm">{conflict}</Text>}
            <Text size="sm" c="orange">
              Si la borrás igual, los envíos de esas campañas y áreas fallan en el momento: los mensajes salen por
              nombre en cada envío.
            </Text>
            <Group justify="flex-end">
              <Button variant="default" onClick={onClose}>
                Cancelar
              </Button>
              <Button color="red" loading={del.isPending} onClick={() => remove(true)}>
                Borrar igual
              </Button>
            </Group>
          </>
        )}
      </Stack>
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
  const [dialog, setDialog] = useState<
    { kind: 'create' } | { kind: 'edit'; template: WaTemplate } | { kind: 'delete'; template: WaTemplate } | null
  >(null);
  const close = () => setDialog(null);

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
            disabled={!account || account.status === 'disconnected'}
            onClick={() => setDialog({ kind: 'create' })}
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
                      <Table.Th>Acciones</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((t) => {
                      const st = TEMPLATE_STATUS[t.status] ?? { label: t.status || '–', color: 'gray' };
                      const whyEdit = editBlocked(t);
                      const whyDelete = deleteBlocked(t);
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
                          <Table.Td>
                            {/* El span: un botón deshabilitado no dispara eventos y el Tooltip
                                (el motivo) tiene que verse igual. */}
                            <Group gap="xs" wrap="nowrap">
                              <Tooltip label={whyEdit ?? 'Editar'} withArrow>
                                <span>
                                  <ActionIcon
                                    variant="default"
                                    size="lg"
                                    aria-label={`Editar ${t.name}`}
                                    disabled={!!whyEdit}
                                    onClick={() => setDialog({ kind: 'edit', template: t })}
                                  >
                                    <IconEdit size={16} />
                                  </ActionIcon>
                                </span>
                              </Tooltip>
                              <Tooltip label={whyDelete ?? 'Borrar'} withArrow>
                                <span>
                                  <ActionIcon
                                    variant="default"
                                    size="lg"
                                    aria-label={`Borrar ${t.name}`}
                                    disabled={!!whyDelete}
                                    onClick={() => setDialog({ kind: 'delete', template: t })}
                                  >
                                    <IconTrash size={16} />
                                  </ActionIcon>
                                </span>
                              </Tooltip>
                            </Group>
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
      {dialog?.kind === 'create' && account && <TemplateModal account={account} onClose={close} />}
      {dialog?.kind === 'edit' && account && (
        <TemplateModal account={account} template={dialog.template} onClose={close} />
      )}
      {dialog?.kind === 'delete' && account && (
        <DeleteTemplateModal account={account} template={dialog.template} onClose={close} />
      )}
    </Card>
  );
}
