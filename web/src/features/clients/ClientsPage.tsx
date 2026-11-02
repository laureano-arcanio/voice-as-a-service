import { Anchor, Badge, Button, Card, Group, Select, Table, Text, UnstyledButton } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconChevronDown, IconChevronUp, IconPlus } from '@tabler/icons-react';
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { ActiveBadge } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDate } from '@/lib/format';
import { useClients } from './api';
import {
  DEFAULT_SORT,
  FILTER_ALL,
  filterClients,
  filterOptions,
  nextSort,
  sortClients,
  type Sort,
  type SortKey,
} from './clientsTable';
import { NewClientModal } from './NewClientModal';

function SortableTh({
  column,
  sort,
  onSort,
  right,
  children,
}: {
  column: SortKey;
  sort: Sort;
  onSort: (key: SortKey) => void;
  right?: boolean;
  children: ReactNode;
}) {
  const active = sort.key === column;
  const Icon = sort.desc ? IconChevronDown : IconChevronUp;
  return (
    <Table.Th
      ta={right ? 'right' : undefined}
      aria-sort={active ? (sort.desc ? 'descending' : 'ascending') : 'none'}
    >
      <UnstyledButton onClick={() => onSort(column)} fz="inherit" fw="inherit" c="inherit">
        <Group gap={4} wrap="nowrap" justify={right ? 'flex-end' : undefined}>
          {children}
          {active && <Icon size={14} aria-hidden />}
        </Group>
      </UnstyledButton>
    </Table.Th>
  );
}

export function ClientsPage() {
  const clients = useClients();
  const [creating, create] = useDisclosure(false);
  const [filter, setFilter] = useState(FILTER_ALL);
  const [sort, setSort] = useState<Sort>(DEFAULT_SORT);
  const onSort = (key: SortKey) => setSort((s) => nextSort(s, key));
  const th = { sort, onSort };
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
          {(list) => {
            if (list.length === 0) return <EmptyState>No hay clientes.</EmptyState>;
            const rows = sortClients(filterClients(list, filter), sort);
            return (
              <>
                <Select
                  label="Plan"
                  data={filterOptions(list)}
                  value={filter}
                  onChange={(v) => setFilter(v ?? FILTER_ALL)}
                  allowDeselect={false}
                  maw={260}
                  mb="md"
                />
                {rows.length === 0 ? (
                  <EmptyState>Ningún cliente con ese filtro.</EmptyState>
                ) : (
                  <Table.ScrollContainer minWidth={720}>
                    <Table>
                      <Table.Thead>
                        <Table.Tr>
                          <SortableTh column="name" {...th}>
                            Nombre
                          </SortableTh>
                          <SortableTh column="slug" {...th}>
                            Slug
                          </SortableTh>
                          <SortableTh column="tier" {...th}>
                            Tier
                          </SortableTh>
                          <SortableTh column="active" {...th}>
                            Estado
                          </SortableTh>
                          <SortableTh column="agents" right {...th}>
                            Agentes
                          </SortableTh>
                          <SortableTh column="numbers" right {...th}>
                            Números
                          </SortableTh>
                          <SortableTh column="created_at" {...th}>
                            Alta
                          </SortableTh>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {rows.map((c) => (
                          <Table.Tr key={c.id}>
                            <Table.Td>
                              <Anchor component={Link} to={`/admin/clients/${c.id}`} fw={600} size="sm">
                                {c.name}
                              </Anchor>
                            </Table.Td>
                            <Table.Td className="mono">{c.slug}</Table.Td>
                            <Table.Td>
                              {c.tier.name}
                              {c.paying && (
                                <Badge color="green" ml={6}>
                                  Pago
                                </Badge>
                              )}
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
                )}
              </>
            );
          }}
        </QueryState>
      </Card>
      <NewClientModal key={String(creating)} opened={creating} onClose={create.close} />
    </>
  );
}
