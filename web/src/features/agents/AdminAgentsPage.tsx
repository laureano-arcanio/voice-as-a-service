import { Badge, Button, Card, Group, Select, Switch, Table, Text, TextInput } from '@mantine/core';
import { IconExternalLink, IconSearch } from '@tabler/icons-react';
import { useSearchParams } from 'react-router';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useClients } from '@/features/clients/api';
import { useSupportSwitch } from '@/features/support/api';
import { formatDateTime } from '@/lib/format';
import { useAgents } from './api';

/** Agentes de todos los clientes (`/admin/agents`), solo lectura: para editar uno se entra como su cliente. */
export function AdminAgentsPage() {
  const [params, setParams] = useSearchParams();
  const clientId = params.get('client') ?? undefined;
  const includeArchived = params.get('archived') === '1';
  const search = params.get('q') ?? '';
  const agents = useAgents(clientId, includeArchived);
  const clients = useClients();
  const support = useSupportSwitch();
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

  const q = search.trim().toLowerCase();

  return (
    <>
      <PageHeader
        title="Agentes"
        description="Los agentes de todos los clientes. Para editar uno o probarlo, abrilo como su cliente."
      />
      <Card>
        <Group mb="md" gap="md" align="flex-end">
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
          <TextInput
            label="Buscar"
            placeholder="Nombre o slug"
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(e) => set('q', e.currentTarget.value || null)}
            w={240}
          />
          <Switch
            label="Incluir archivados"
            checked={includeArchived}
            onChange={(e) => set('archived', e.currentTarget.checked ? '1' : null)}
            mb={6}
          />
        </Group>
        <QueryState query={agents}>
          {(all) => {
            const list = q ? all.filter((a) => `${a.name} ${a.slug}`.toLowerCase().includes(q)) : all;
            return list.length === 0 ? (
              <EmptyState>
                {all.length === 0 ? 'No hay agentes.' : 'Ningún agente coincide con la búsqueda.'}
              </EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={900}>
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Cliente</Table.Th>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>Slug</Table.Th>
                      <Table.Th>Versión</Table.Th>
                      <Table.Th>Voz</Table.Th>
                      <Table.Th>Actualizado</Table.Th>
                      <Table.Th />
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((a) => (
                      <Table.Tr
                        key={a.id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => void support.enter(a.client_id, `/agents/${a.id}`)}
                      >
                        <Table.Td>{clientName.get(a.client_id) ?? '–'}</Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <Text size="sm" fw={600}>
                              {a.name}
                            </Text>
                            {a.archived && <Badge color="gray">Archivado</Badge>}
                          </Group>
                        </Table.Td>
                        <Table.Td className="mono">{a.slug}</Table.Td>
                        <Table.Td className="mono">v{a.version}</Table.Td>
                        <Table.Td>{a.voice ?? '–'}</Table.Td>
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(a.updated_at)}</Table.Td>
                        <Table.Td>
                          <Button
                            variant="subtle"
                            size="compact-sm"
                            leftSection={<IconExternalLink size={14} />}
                            loading={support.pending}
                            onClick={(e) => {
                              e.stopPropagation();
                              void support.enter(a.client_id, `/agents/${a.id}`);
                            }}
                          >
                            Abrir como el cliente
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            );
          }}
        </QueryState>
      </Card>
    </>
  );
}
