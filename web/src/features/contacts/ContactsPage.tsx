import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Pagination,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import {
  IconArchive,
  IconArchiveOff,
  IconFileImport,
  IconPencil,
  IconPlus,
  IconSearch,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { Contact } from '@/api/types';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { usePlan } from '@/features/campaigns/api';
import { useClients } from '@/features/clients/api';
import { formatDate, formatNumber } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  type ArchivedFilter,
  CONTACTS_PAGE,
  useArchiveContact,
  useArchiveMany,
  useContacts,
  useTagSuggestions,
  useUnarchiveMany,
} from './api';
import { ContactModal, ImportContactsModal } from './ContactModals';
import { TagBadges } from './TagBadges';
import { attributesText } from './labels';

const ARCHIVED_OPTIONS: { value: ArchivedFilter; label: string }[] = [
  { value: 'false', label: 'Activos' },
  { value: 'true', label: 'Archivados' },
  { value: 'all', label: 'Todos' },
];

export function ContactsPage() {
  const isAdmin = useIsAdmin();
  const [params, setParams] = useSearchParams();
  const clientId = isAdmin ? (params.get('client') ?? undefined) : undefined;
  const clients = useClients(isAdmin);
  const [search, setSearch] = useState('');
  const [q] = useDebouncedValue(search.trim(), 300);
  const [tag, setTag] = useState('');
  const [archived, setArchived] = useState<ArchivedFilter>('false');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dialog, setDialog] = useState<'new' | 'import' | Contact | null>(null);

  const contacts = useContacts({ clientId, q, tag, archived, offset: (page - 1) * CONTACTS_PAGE });
  const tags = useTagSuggestions(clientId);
  const plan = usePlan(clientId, !isAdmin || !!clientId);
  const archiveOne = useArchiveContact();
  const archiveMany = useArchiveMany(clientId);
  const unarchiveMany = useUnarchiveMany();

  // Otra pagina o filtro: la seleccion era de otra lista.
  const restart = (change: () => void) => {
    change();
    setPage(1);
    setSelected(new Set());
  };

  const canWrite = !isAdmin || !!clientId;
  const noAgenda = plan.data?.max_contacts === 0;
  const blocked = !canWrite
    ? 'Elegí un cliente para cargar contactos'
    : noAgenda
      ? 'Tu plan no incluye la agenda de contactos'
      : null;
  const items = contacts.data?.items ?? [];
  const total = contacts.data?.total ?? 0;
  const allChecked = items.length > 0 && items.every((c) => selected.has(c.id));

  const setClient = (v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set('client', v);
        else next.delete('client');
        return next;
      },
      { replace: true },
    );

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const archiveOneContact = async (c: Contact) => {
    const ok = await confirmAction({
      title: `Archivar a ${c.name || c.phone}`,
      message:
        'No se borra: queda en el historial y los reportes. No entra en campañas nuevas, y sus llamadas o mensajes pendientes en campañas en curso se saltean.',
      confirmLabel: 'Archivar',
      danger: true,
    });
    if (ok)
      archiveOne.mutate(
        { id: c.id, archive: true },
        { onSuccess: () => notifySuccess('Contacto archivado.'), onError: (e) => notifyError(e) },
      );
  };

  const unarchiveOneContact = (c: Contact) =>
    archiveOne.mutate(
      { id: c.id, archive: false },
      {
        onSuccess: () => notifySuccess('Contacto activo de nuevo.'),
        onError: (e) => notifyError(e, 'No se pudo desarchivar'),
      },
    );

  const bulkArchive = async (by: { contact_ids?: string[]; tags?: string[] }, what: string) => {
    const ok = await confirmAction({
      title: `Archivar ${what}`,
      message:
        'No se borran: quedan en el historial y los reportes. Sus llamadas o mensajes pendientes en campañas en curso se saltean. Podés desarchivarlos cuando quieras.',
      confirmLabel: 'Archivar',
      danger: true,
    });
    if (ok)
      archiveMany.mutate(by, {
        onSuccess: (r) => {
          notifySuccess(r.archived === 1 ? '1 contacto archivado.' : `${r.archived} contactos archivados.`);
          setSelected(new Set());
        },
        onError: (e) => notifyError(e),
      });
  };

  const bulkUnarchive = () =>
    unarchiveMany.mutate([...selected], {
      onSuccess: (r) => {
        if (r.done)
          notifySuccess(
            r.done === 1 ? '1 contacto activo de nuevo.' : `${r.done} contactos activos de nuevo.`,
          );
        if (r.failed) notifyError(r.firstError, `${r.failed} no se pudieron desarchivar`);
        setSelected(new Set());
      },
    });

  const usage = plan.data;
  const agendaNote =
    usage && usage.max_contacts != null && usage.max_contacts > 0
      ? `${formatNumber(usage.contacts_active, 0)} de ${formatNumber(usage.max_contacts, 0)} contactos activos en tu plan.`
      : null;

  return (
    <Stack gap="md">
      <PageHeader
        title="Contactos"
        description="La agenda del negocio: a quién llaman y le escriben las campañas. Los contactos no se borran, se archivan."
        actions={
          <>
            <Tooltip label={blocked} withArrow disabled={!blocked}>
              <Button
                variant="default"
                leftSection={<IconFileImport size={18} />}
                data-disabled={!!blocked || undefined}
                onClick={(e) => (blocked ? e.preventDefault() : setDialog('import'))}
              >
                Importar CSV
              </Button>
            </Tooltip>
            <Tooltip label={blocked} withArrow disabled={!blocked}>
              <Button
                leftSection={<IconPlus size={18} />}
                data-disabled={!!blocked || undefined}
                onClick={(e) => (blocked ? e.preventDefault() : setDialog('new'))}
              >
                Nuevo contacto
              </Button>
            </Tooltip>
          </>
        }
      />
      <Card>
        <Group mb="md" gap="sm" align="flex-end">
          {isAdmin && (
            <Select
              label="Cliente"
              placeholder="Todos los clientes"
              data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
              value={clientId ?? null}
              onChange={(v) => restart(() => setClient(v))}
              clearable
              searchable
              w={220}
            />
          )}
          <TextInput
            label="Buscar"
            placeholder="Nombre, teléfono, email o ID"
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(e) => restart(() => setSearch(e.currentTarget.value))}
            w={260}
          />
          <Select
            label="Etiqueta"
            placeholder="Todas"
            data={tags.data ?? []}
            value={tag || null}
            onChange={(v) => restart(() => setTag(v ?? ''))}
            clearable
            searchable
            nothingFoundMessage="No hay etiquetas"
            w={180}
          />
          <SegmentedControl
            aria-label="Estado"
            data={ARCHIVED_OPTIONS}
            value={archived}
            onChange={(v) => restart(() => setArchived(v as ArchivedFilter))}
          />
        </Group>
        {agendaNote && (
          <Text size="xs" c="dimmed" mb="sm">
            {agendaNote}
          </Text>
        )}
        {selected.size > 0 && (
          <Group mb="sm" gap="sm">
            <Text size="sm" fw={600}>
              {selected.size} {selected.size === 1 ? 'seleccionado' : 'seleccionados'}
            </Text>
            <Button
              variant="subtle"
              color="red"
              size="compact-sm"
              leftSection={<IconArchive size={16} />}
              loading={archiveMany.isPending}
              onClick={() => void bulkArchive({ contact_ids: [...selected] }, `${selected.size} contactos`)}
            >
              Archivar
            </Button>
            <Button
              variant="subtle"
              size="compact-sm"
              leftSection={<IconArchiveOff size={16} />}
              loading={unarchiveMany.isPending}
              onClick={bulkUnarchive}
            >
              Desarchivar
            </Button>
            <Button variant="subtle" color="gray" size="compact-sm" onClick={() => setSelected(new Set())}>
              Quitar selección
            </Button>
          </Group>
        )}
        {tag && archived === 'false' && total > 0 && selected.size === 0 && (
          <Group mb="sm">
            <Button
              variant="subtle"
              color="red"
              size="compact-sm"
              leftSection={<IconArchive size={16} />}
              loading={archiveMany.isPending}
              onClick={() => void bulkArchive({ tags: [tag] }, `todos los de la etiqueta ${tag}`)}
            >
              Archivar la etiqueta {tag}
            </Button>
          </Group>
        )}
        <QueryState query={contacts}>
          {() =>
            items.length === 0 ? (
              <EmptyState>
                {q || tag || archived !== 'false'
                  ? 'No hay contactos con esos filtros.'
                  : 'Todavía no hay contactos. Importá un CSV o agregá el primero: las campañas toman sus destinatarios de acá.'}
              </EmptyState>
            ) : (
              <>
                <Table.ScrollContainer minWidth={isAdmin && !clientId ? 980 : 860}>
                  <Table>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th w={36}>
                          <Checkbox
                            aria-label="Seleccionar todos"
                            checked={allChecked}
                            indeterminate={!allChecked && items.some((c) => selected.has(c.id))}
                            onChange={() =>
                              setSelected(allChecked ? new Set() : new Set(items.map((c) => c.id)))
                            }
                          />
                        </Table.Th>
                        <Table.Th>Teléfono</Table.Th>
                        <Table.Th>Nombre</Table.Th>
                        {isAdmin && !clientId && <Table.Th>Cliente</Table.Th>}
                        <Table.Th>Etiquetas</Table.Th>
                        <Table.Th>Datos</Table.Th>
                        <Table.Th>Alta</Table.Th>
                        <Table.Th />
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {items.map((c) => (
                        <Table.Tr key={c.id} bg={selected.has(c.id) ? 'var(--app-surface-2)' : undefined}>
                          <Table.Td>
                            <Checkbox
                              aria-label={`Seleccionar ${c.name || c.phone}`}
                              checked={selected.has(c.id)}
                              onChange={() => toggle(c.id)}
                            />
                          </Table.Td>
                          <Table.Td className="mono" style={{ whiteSpace: 'nowrap' }}>
                            <Anchor
                              component={Link}
                              to={`/contacts/${c.id}`}
                              size="sm"
                              fw={600}
                              className="mono"
                            >
                              {c.phone}
                            </Anchor>
                          </Table.Td>
                          <Table.Td>
                            <Group gap={6} wrap="nowrap">
                              {c.name ?? <Dash />}
                              {c.archived_at && <Badge color="gray">Archivado</Badge>}
                            </Group>
                          </Table.Td>
                          {isAdmin && !clientId && (
                            <Table.Td>
                              {(clients.data ?? []).find((x) => x.id === c.client_id)?.name ?? <Dash />}
                            </Table.Td>
                          )}
                          <Table.Td>
                            <TagBadges tags={c.tags} />
                          </Table.Td>
                          <Table.Td>
                            {Object.keys(c.attributes).length ? (
                              <Text
                                size="xs"
                                c="dimmed"
                                lineClamp={1}
                                maw={220}
                                title={attributesText(c.attributes)}
                              >
                                {attributesText(c.attributes)}
                              </Text>
                            ) : (
                              <Dash />
                            )}
                          </Table.Td>
                          <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDate(c.created_at)}</Table.Td>
                          <Table.Td>
                            <Group gap={4} justify="flex-end" wrap="nowrap">
                              <Tooltip label="Editar" withArrow>
                                <ActionIcon
                                  variant="subtle"
                                  color="gray"
                                  aria-label={`Editar ${c.name || c.phone}`}
                                  onClick={() => setDialog(c)}
                                >
                                  <IconPencil size={16} />
                                </ActionIcon>
                              </Tooltip>
                              {c.archived_at ? (
                                <Tooltip label="Desarchivar" withArrow>
                                  <ActionIcon
                                    variant="subtle"
                                    aria-label={`Desarchivar ${c.name || c.phone}`}
                                    onClick={() => unarchiveOneContact(c)}
                                  >
                                    <IconArchiveOff size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              ) : (
                                <Tooltip label="Archivar" withArrow>
                                  <ActionIcon
                                    variant="subtle"
                                    color="red"
                                    aria-label={`Archivar ${c.name || c.phone}`}
                                    onClick={() => void archiveOneContact(c)}
                                  >
                                    <IconArchive size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              )}
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
                <Group justify="space-between" mt="md">
                  <Text size="xs" c="dimmed">
                    {formatNumber(total, 0)} {total === 1 ? 'contacto' : 'contactos'}
                  </Text>
                  {total > CONTACTS_PAGE && (
                    <Pagination
                      total={Math.ceil(total / CONTACTS_PAGE)}
                      value={page}
                      onChange={(p) => {
                        setPage(p);
                        setSelected(new Set());
                      }}
                    />
                  )}
                </Group>
              </>
            )
          }
        </QueryState>
      </Card>
      {dialog === 'new' && (
        <ContactModal contact={null} clientId={clientId} onClose={() => setDialog(null)} />
      )}
      {dialog === 'import' && <ImportContactsModal clientId={clientId} onClose={() => setDialog(null)} />}
      {dialog && typeof dialog === 'object' && (
        <ContactModal key={dialog.id} contact={dialog} onClose={() => setDialog(null)} />
      )}
    </Stack>
  );
}
