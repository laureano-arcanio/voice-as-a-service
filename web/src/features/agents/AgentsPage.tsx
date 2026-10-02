import { Anchor, Badge, Button, Card, Group, Select, Switch, Table, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconPlus } from '@tabler/icons-react';
import { Link, useSearchParams } from 'react-router';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { formatDateTime } from '@/lib/format';
import { ENGINE } from '@/lib/labels';
import { useAgents } from './api';
import { NewAgentModal } from './NewAgentModal';

export function AgentsPage() {
  const isAdmin = useIsAdmin();
  const [params, setParams] = useSearchParams();
  const clientId = params.get('client') ?? undefined;
  const includeArchived = params.get('archived') === '1';
  const agents = useAgents(clientId, includeArchived);
  const clients = useClients(isAdmin);
  const [creating, create] = useDisclosure(false);
  const clientName = new Map((clients.data ?? []).map((c) => [c.id, c.name]));

  const set = (k: string, v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set(k, v);
        else next.delete(k);
        return next;
      },
      { replace: true },
    );

  return (
    <>
      <PageHeader
        title="Agentes"
        description={
          isAdmin
            ? 'Cada agente es un workflow versionado: qué datos pide, cómo habla y cómo cierra.'
            : 'Cada agente define qué datos pide, cómo habla y cómo cierra la conversación.'
        }
        actions={
          isAdmin && (
            <Button leftSection={<IconPlus size={18} />} onClick={create.open}>
              Nuevo agente
            </Button>
          )
        }
      />
      <Card>
        <Group mb="md" gap="md" align="flex-end">
          {isAdmin && (
            <Select
              label="Cliente"
              data={[
                { value: '', label: 'Todos' },
                ...(clients.data ?? []).map((c) => ({ value: c.id, label: c.name })),
              ]}
              value={clientId ?? ''}
              onChange={(v) => set('client', v || null)}
              allowDeselect={false}
              searchable
              w={220}
            />
          )}
          <Switch
            label="Incluir archivados"
            checked={includeArchived}
            onChange={(e) => set('archived', e.currentTarget.checked ? '1' : null)}
            mb={6}
          />
        </Group>
        <QueryState query={agents}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState>
                {isAdmin ? 'No hay agentes. Creá uno desde una plantilla.' : 'No hay agentes.'}
              </EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={isAdmin ? 820 : 560}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Nombre</Table.Th>
                      {isAdmin && <Table.Th>Slug</Table.Th>}
                      {isAdmin && <Table.Th>Cliente</Table.Th>}
                      {isAdmin && <Table.Th>Motor</Table.Th>}
                      <Table.Th>Voz</Table.Th>
                      <Table.Th>Versión</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Actualizado</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((a) => (
                      <Table.Tr key={a.id}>
                        <Table.Td>
                          <Anchor component={Link} to={`/agents/${a.id}`} fw={600} size="sm">
                            {a.name}
                          </Anchor>
                          {a.description && (
                            <Text size="xs" c="dimmed" lineClamp={1}>
                              {a.description}
                            </Text>
                          )}
                        </Table.Td>
                        {isAdmin && <Table.Td className="mono">{a.slug}</Table.Td>}
                        {isAdmin && <Table.Td>{clientName.get(a.client_id) ?? '–'}</Table.Td>}
                        {isAdmin && <Table.Td>{ENGINE[a.engine] ?? a.engine}</Table.Td>}
                        <Table.Td>{a.voice ?? '–'}</Table.Td>
                        <Table.Td className="mono">v{a.version}</Table.Td>
                        <Table.Td>
                          {a.archived ? (
                            <Badge color="gray">Archivado</Badge>
                          ) : (
                            <Badge color="green">Activo</Badge>
                          )}
                        </Table.Td>
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(a.updated_at)}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      {isAdmin && (
        <NewAgentModal key={String(creating)} opened={creating} onClose={create.close} clientId={clientId} />
      )}
    </>
  );
}
