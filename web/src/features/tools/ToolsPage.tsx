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
import { IconApi, IconChevronDown, IconCode, IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import type { ClientTool } from '@/api/types';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useFeatureLock } from '@/features/billing/features';
import { useClients } from '@/features/clients/api';
import { formatDateTime } from '@/lib/format';
import { CLIENT_TOOL_TYPE } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { toolsHref, useDeleteTool, useTools, useToolsClient } from './api';

function LastTest({ tool }: { tool: ClientTool }) {
  if (!tool.last_test_at) return <Dash />;
  return (
    <Group gap={6} wrap="nowrap">
      <Badge color={tool.last_test_ok ? 'green' : 'red'}>{tool.last_test_ok ? 'Funcionó' : 'Falló'}</Badge>
      <Text span size="xs" c="dimmed" title={tool.last_test_detail || undefined}>
        {formatDateTime(tool.last_test_at)}
      </Text>
    </Group>
  );
}

/** Herramientas del cliente: APIs y funciones que llaman sus agentes en una conversacion. */
export function ToolsPage() {
  const isAdmin = useIsAdmin();
  const clientId = useToolsClient();
  const [, setParams] = useSearchParams();
  const navigate = useNavigate();
  const clients = useClients(isAdmin);
  const tools = useTools(clientId);
  const remove = useDeleteTool(clientId ?? '');
  const codeLock = useFeatureLock('code_tools');
  const href = (path: string) => toolsHref(path, clientId, isAdmin);

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

  const del = async (t: ClientTool) => {
    const ok = await confirmAction({
      title: `¿Borrar la herramienta ${t.slug}?`,
      message: t.used_by.length
        ? `La usan ${t.used_by.map((a) => a.name).join(', ')}: sacala de cada agente antes.`
        : 'Los agentes ya no la pueden usar. Las conversaciones pasadas se conservan.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      remove.mutate(t.slug, {
        onSuccess: () => notifySuccess('Herramienta borrada.'),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  const newMenu = (
    <Menu position="bottom-end">
      <Menu.Target>
        <Button
          leftSection={<IconPlus size={18} />}
          rightSection={<IconChevronDown size={16} />}
          disabled={!clientId}
        >
          Nueva herramienta
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item
          leftSection={<IconApi size={18} />}
          onClick={() => void navigate(href('/tools/new?type=http'))}
        >
          <Text size="sm" fw={600}>
            Llamar a una API
          </Text>
          <Text size="xs" c="dimmed">
            Un pedido HTTP a tu sistema: método, URL y parámetros.
          </Text>
        </Menu.Item>
        <Menu.Item
          leftSection={<IconCode size={18} />}
          disabled={codeLock.locked}
          onClick={() => void navigate(href('/tools/new?type=code'))}
        >
          <Text size="sm" fw={600}>
            Escribir código
          </Text>
          <Text size="xs" c="dimmed">
            {codeLock.locked
              ? `Tu plan no lo incluye. ${codeLock.reason ?? ''}`
              : 'Una función en JavaScript, para lo que no entra en un solo pedido.'}
          </Text>
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );

  return (
    <Stack gap="md">
      <PageHeader
        title="Herramientas"
        description="Lo que tus agentes pueden hacer durante una conversación: consultar o registrar datos en tu sistema."
        actions={newMenu}
      />
      {isAdmin && (
        <Group>
          <Select
            label="Cliente"
            placeholder="Elegí un cliente"
            data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            value={clientId ?? null}
            onChange={setClient}
            clearable
            searchable
            w={260}
          />
        </Group>
      )}
      <PlanGate feature="custom_tools" what="herramientas para tus agentes">
        <Card>
          {!clientId ? (
            <EmptyState>Elegí un cliente para ver sus herramientas.</EmptyState>
          ) : (
            <QueryState query={tools}>
              {(rows) =>
                rows.length === 0 ? (
                  <EmptyState>
                    Todavía no hay herramientas. Creá una para que tus agentes consulten turnos, deudas o
                    pedidos en tu sistema, y después elegila en cada agente.
                  </EmptyState>
                ) : (
                  <Table.ScrollContainer minWidth={720}>
                    <Table>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Herramienta</Table.Th>
                          <Table.Th>Tipo</Table.Th>
                          <Table.Th>Agentes que la usan</Table.Th>
                          <Table.Th>Última prueba</Table.Th>
                          <Table.Th />
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {rows.map((t) => (
                          <Table.Tr key={t.id}>
                            <Table.Td>
                              <Anchor
                                component={Link}
                                to={href(`/tools/${t.slug}`)}
                                className="mono"
                                fw={600}
                              >
                                {t.slug}
                              </Anchor>
                              <Text
                                size="xs"
                                c="dimmed"
                                lineClamp={1}
                                maw={360}
                                title={String(t.definition.description ?? '')}
                              >
                                {String(t.definition.description ?? '')}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Badge color="gray">{CLIENT_TOOL_TYPE[t.type] ?? t.type}</Badge>
                            </Table.Td>
                            <Table.Td>
                              {t.used_by.length ? (
                                <Text size="sm">
                                  {t.used_by.map((a, i) => (
                                    <span key={a.id}>
                                      {i > 0 && ', '}
                                      <Anchor component={Link} to={`/agents/${a.id}`} inherit>
                                        {a.name}
                                      </Anchor>
                                    </span>
                                  ))}
                                </Text>
                              ) : (
                                <Dash />
                              )}
                            </Table.Td>
                            <Table.Td>
                              <LastTest tool={t} />
                            </Table.Td>
                            <Table.Td>
                              <Group gap={4} justify="flex-end" wrap="nowrap">
                                <Tooltip label="Editar" withArrow>
                                  <ActionIcon
                                    variant="subtle"
                                    color="gray"
                                    component={Link}
                                    to={href(`/tools/${t.slug}`)}
                                    aria-label={`Editar ${t.slug}`}
                                  >
                                    <IconPencil size={16} />
                                  </ActionIcon>
                                </Tooltip>
                                <Tooltip label="Borrar" withArrow>
                                  <ActionIcon
                                    variant="subtle"
                                    color="red"
                                    aria-label={`Borrar ${t.slug}`}
                                    onClick={() => void del(t)}
                                  >
                                    <IconTrash size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </Table.ScrollContainer>
                )
              }
            </QueryState>
          )}
        </Card>
      </PlanGate>
    </Stack>
  );
}
