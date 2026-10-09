import { Anchor, Badge, Button, Card, Table, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconPlus } from '@tabler/icons-react';
import { Link } from 'react-router';
import { ActiveBadge } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDate } from '@/lib/format';
import { useClients } from './api';
import { NewClientModal } from './NewClientModal';

export function ClientsPage() {
  const clients = useClients();
  const [creating, create] = useDisclosure(false);
  return (
    <>
      <PageHeader
        title="Clientes"
        description="Cada cliente tiene sus números, agentes, usuarios y API keys, con los límites de su tier."
        actions={
          <Button leftSection={<IconPlus size={18} />} onClick={create.open}>
            Nuevo cliente
          </Button>
        }
      />
      <Card>
        <QueryState query={clients}>
          {(list) =>
            list.length === 0 ? (
              <EmptyState>No hay clientes.</EmptyState>
            ) : (
              <Table.ScrollContainer minWidth={720}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>Slug</Table.Th>
                      <Table.Th>Tier</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th ta="right">Agentes</Table.Th>
                      <Table.Th ta="right">Números</Table.Th>
                      <Table.Th>Alta</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td>
                          <Anchor component={Link} to={`/clients/${c.id}`} fw={600} size="sm">
                            {c.name}
                          </Anchor>
                        </Table.Td>
                        <Table.Td className="mono">{c.slug}</Table.Td>
                        <Table.Td>
                          {c.tier.name}
                          {!!c.adjustments_count && (
                            <Badge color="blue" ml={6}>
                              Ajustado
                            </Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <ActiveBadge active={c.active} />
                        </Table.Td>
                        <Table.Td ta="right">{c.agents_count ?? 0}</Table.Td>
                        <Table.Td ta="right">{c.numbers_count ?? 0}</Table.Td>
                        <Table.Td>
                          <Text size="sm">{formatDate(c.created_at)}</Text>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )
          }
        </QueryState>
      </Card>
      <NewClientModal key={String(creating)} opened={creating} onClose={create.close} />
    </>
  );
}
