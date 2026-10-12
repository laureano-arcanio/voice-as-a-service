import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Menu,
  Select,
  Stack,
  Table,
  Text,
  Tooltip,
} from '@mantine/core';
import {
  IconChevronDown,
  IconChevronRight,
  IconDots,
  IconLink,
  IconList,
  IconRefresh,
  IconTrash,
  IconUnlink,
  IconUserPlus,
} from '@tabler/icons-react';
import { Fragment, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { App } from '@/api/types';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { formatDateTime } from '@/lib/format';
import { APP_STATUS, TOOL_KIND } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useApps, useDeleteApp, useRefreshApp, useReleaseApp } from './api';
import { AssignAppModal, CreateLinkModal, LinksModal } from './AppModals';

type Dialog = { kind: 'assign' | 'link' | 'links'; app: App } | null;

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

export function AppStatusBadge({ app }: { app: App }) {
  const l = APP_STATUS[app.status] ?? { label: app.status, color: 'gray' };
  const badge = <Badge color={l.color}>{l.label}</Badge>;
  return app.last_error ? (
    <Tooltip label={app.last_error} multiline maw={360} withArrow>
      {badge}
    </Tooltip>
  ) : (
    badge
  );
}

/** Vistas y herramientas de una app, para la fila expandida. */
export function AppDetail({ app }: { app: App }) {
  const views = app.views ?? [];
  const tools = app.tools ?? [];
  return (
    <Stack gap="sm" py="xs">
      <div>
        <Text className="label" mb={4}>
          Vistas
        </Text>
        {views.length ? (
          <Stack gap={4}>
            {views.map((v) => (
              <Text key={v.name} size="sm">
                <Text span fw={600}>
                  {v.title}
                </Text>{' '}
                <Text span className="mono" c="dimmed">
                  {v.name}
                </Text>
                {v.description && ` · ${v.description}`}
              </Text>
            ))}
          </Stack>
        ) : (
          <Dash />
        )}
      </div>
      <div>
        <Text className="label" mb={4}>
          Herramientas
        </Text>
        {tools.length ? (
          <Table withRowBorders={false} verticalSpacing={4}>
            <Table.Tbody>
              {tools.map((t) => {
                const k = TOOL_KIND[t.kind] ?? { label: t.kind, color: 'gray' };
                return (
                  <Table.Tr key={t.name}>
                    <Table.Td className="mono" style={{ whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                      {t.name}
                    </Table.Td>
                    <Table.Td style={{ verticalAlign: 'top' }}>
                      <Badge color={k.color}>{k.label}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="gray.7">
                        {t.description}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        ) : (
          <Dash />
        )}
        {tools.some((t) => t.kind === 'destructive' || t.kind === 'send') && (
          <Text size="xs" c="dimmed" mt={4}>
            Las que borran o envían a terceros el asistente las confirma con la persona antes de usarlas.
          </Text>
        )}
      </div>
    </Stack>
  );
}

export function AppsPage() {
  const isAdmin = useIsAdmin();
  const [params, setParams] = useSearchParams();
  const clientId = (isAdmin && params.get('client')) || undefined;
  const apps = useApps(clientId);
  const clients = useClients(isAdmin);
  const release = useReleaseApp();
  const refresh = useRefreshApp();
  const del = useDeleteApp();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const doRelease = async (a: App) => {
    const ok = await confirmAction({
      title: `Liberar ${a.name}`,
      message: `Vuelve al inventario: sus links dejan de abrir y los agentes de ${a.client_name ?? 'el cliente'} pierden sus herramientas.`,
      confirmLabel: 'Liberar',
      danger: true,
    });
    if (ok)
      release.mutate(a.id, {
        onSuccess: () => notifySuccess(`${a.name} volvió al inventario.`),
        onError: (e) => notifyError(e, 'No se pudo liberar'),
      });
  };

  const doRefresh = (a: App) =>
    refresh.mutate(a.id, {
      onSuccess: (r) =>
        r.status === 'ok'
          ? notifySuccess(`${r.name} responde (versión ${r.version}).`)
          : notifyError(new Error(r.last_error ?? 'No responde'), `${r.name} no responde bien`),
      onError: (e) => notifyError(e, 'No se pudo releer'),
    });

  const doDelete = async (a: App) => {
    const ok = await confirmAction({
      title: `Borrar ${a.name}`,
      message:
        'Se quita del inventario con sus links. El contenedor sigue corriendo: se baja con make down en atentina-apps.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      del.mutate(a.id, {
        onSuccess: () => notifySuccess(`${a.name} borrada.`),
        onError: (e) =>
          notifyError(
            e,
            e instanceof ApiError && e.status === 409 ? 'Está asignada: liberala antes' : undefined,
          ),
      });
  };

  const cols = isAdmin ? 7 : 5;

  return (
    <>
      <PageHeader
        title="Apps"
        description={
          isAdmin
            ? 'Apps de los clientes: se registran desde atentina-apps, se asignan a un cliente y sus herramientas las usa un agente con motor asistente.'
            : 'Las aplicaciones de tu negocio: guardan tus datos, le dan herramientas a tu asistente y tienen vistas que abrís con un link.'
        }
      />
      <Card>
        {isAdmin && (
          <Group mb="md" gap="sm">
            <Select
              placeholder="Todos los clientes"
              data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
              value={clientId ?? null}
              onChange={(v) =>
                setParams(
                  (prev) => {
                    const next = new URLSearchParams(prev);
                    if (v) next.set('client', v);
                    else next.delete('client');
                    return next;
                  },
                  { replace: true },
                )
              }
              clearable
              searchable
              w={240}
              aria-label="Cliente"
            />
          </Group>
        )}
        <QueryState query={apps}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState>
                {isAdmin ? (
                  <>
                    No hay apps registradas. Se registran desde atentina-apps con{' '}
                    <code>make register A=&lt;cliente&gt;/&lt;app&gt;</code> (o <code>make deploy</code>).
                  </>
                ) : (
                  'Todavía no tenés aplicaciones. Escribinos y armamos la de tu negocio.'
                )}
              </EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={isAdmin ? 980 : 640}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>App</Table.Th>
                      {isAdmin && <Table.Th>Versión</Table.Th>}
                      <Table.Th>Estado</Table.Th>
                      {isAdmin && <Table.Th>Cliente</Table.Th>}
                      <Table.Th>Vistas y herramientas</Table.Th>
                      <Table.Th>Último chequeo</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((a) => {
                      const expanded = !!open[a.id];
                      return (
                        <Fragment key={a.id}>
                          <Table.Tr>
                            <Table.Td>
                              <Text size="sm" fw={600} style={{ whiteSpace: 'nowrap' }}>
                                {a.name || a.slug}
                              </Text>
                              {isAdmin && (
                                <Text size="xs" c="dimmed" className="mono">
                                  {a.slug}
                                </Text>
                              )}
                            </Table.Td>
                            {isAdmin && <Table.Td className="mono">{a.version || <Dash />}</Table.Td>}
                            <Table.Td>
                              <AppStatusBadge app={a} />
                            </Table.Td>
                            {isAdmin && (
                              <Table.Td>
                                {a.client_id ? (
                                  <Anchor component={Link} to={`/clients/${a.client_id}`} size="sm">
                                    {a.client_name ?? 'Cliente'}
                                  </Anchor>
                                ) : (
                                  <Badge color="gray">Libre</Badge>
                                )}
                              </Table.Td>
                            )}
                            <Table.Td>
                              <Button
                                size="compact-sm"
                                variant="subtle"
                                color="gray"
                                leftSection={
                                  expanded ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />
                                }
                                onClick={() => setOpen((o) => ({ ...o, [a.id]: !expanded }))}
                                aria-expanded={expanded}
                              >
                                {plural(a.views?.length ?? 0, 'vista', 'vistas')} ·{' '}
                                {plural(a.tools?.length ?? 0, 'herramienta', 'herramientas')}
                              </Button>
                            </Table.Td>
                            <Table.Td style={{ whiteSpace: 'nowrap' }}>
                              {a.last_health_at ? formatDateTime(a.last_health_at) : <Dash />}
                            </Table.Td>
                            <Table.Td>
                              <Group gap={4} justify="flex-end" wrap="nowrap">
                                {a.client_id && (a.views?.length ?? 0) > 0 && (
                                  <Button
                                    size="compact-sm"
                                    variant="subtle"
                                    leftSection={<IconLink size={16} />}
                                    onClick={() => setDialog({ kind: 'link', app: a })}
                                  >
                                    Link a una vista
                                  </Button>
                                )}
                                {isAdmin && !a.client_id && (
                                  <Button
                                    size="compact-sm"
                                    variant="subtle"
                                    leftSection={<IconUserPlus size={16} />}
                                    onClick={() => setDialog({ kind: 'assign', app: a })}
                                  >
                                    Asignar
                                  </Button>
                                )}
                                <Menu position="bottom-end" withinPortal>
                                  <Menu.Target>
                                    <ActionIcon
                                      variant="subtle"
                                      color="gray"
                                      aria-label={`Acciones de ${a.name}`}
                                    >
                                      <IconDots size={16} />
                                    </ActionIcon>
                                  </Menu.Target>
                                  <Menu.Dropdown>
                                    <Menu.Item
                                      leftSection={<IconList size={16} />}
                                      onClick={() => setDialog({ kind: 'links', app: a })}
                                    >
                                      Ver links
                                    </Menu.Item>
                                    {isAdmin && (
                                      <Menu.Item
                                        leftSection={<IconRefresh size={16} />}
                                        onClick={() => doRefresh(a)}
                                      >
                                        Releer manifest
                                      </Menu.Item>
                                    )}
                                    {isAdmin &&
                                      (a.client_id ? (
                                        <Menu.Item
                                          color="red"
                                          leftSection={<IconUnlink size={16} />}
                                          onClick={() => void doRelease(a)}
                                        >
                                          Liberar
                                        </Menu.Item>
                                      ) : (
                                        <Menu.Item
                                          color="red"
                                          leftSection={<IconTrash size={16} />}
                                          onClick={() => void doDelete(a)}
                                        >
                                          Borrar
                                        </Menu.Item>
                                      ))}
                                  </Menu.Dropdown>
                                </Menu>
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                          {expanded && (
                            <Table.Tr>
                              <Table.Td colSpan={cols} bg="var(--app-surface-2)">
                                <AppDetail app={a} />
                              </Table.Td>
                            </Table.Tr>
                          )}
                        </Fragment>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      {dialog?.kind === 'assign' && <AssignAppModal app={dialog.app} onClose={() => setDialog(null)} />}
      {dialog?.kind === 'link' && <CreateLinkModal app={dialog.app} onClose={() => setDialog(null)} />}
      {dialog?.kind === 'links' && <LinksModal app={dialog.app} onClose={() => setDialog(null)} />}
    </>
  );
}
