import { Anchor, Badge, Button, Card, Group, Stack, Switch, Table, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconPlayerPlay, IconPlus } from '@tabler/icons-react';
import { Link, useSearchParams } from 'react-router';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime } from '@/lib/format';
import { useAgents } from './api';
import { CallLinkCell } from './CallLinkCell';
import { NewAgentModal } from './NewAgentModal';

export function AgentsPage() {
  const [params, setParams] = useSearchParams();
  const includeArchived = params.get('archived') === '1';
  const agents = useAgents(undefined, includeArchived);
  // ?nuevo=1 (desde Inicio): abre el alta.
  const [creating, create] = useDisclosure(params.get('nuevo') === '1');

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
        description="Cada agente define qué datos pide, cómo habla y cómo cierra la conversación."
        actions={
          <Button leftSection={<IconPlus size={18} />} onClick={create.open}>
            Nuevo agente
          </Button>
        }
      />
      <Card>
        <Group mb="md" gap="md" align="flex-end">
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
              <Stack align="center" gap={0} pb="lg">
                <EmptyState>
                  {includeArchived ? 'Todavía no tenés agentes.' : 'No tenés agentes activos.'} Creá uno y
                  después elegí qué número atiende.
                </EmptyState>
                <Button variant="light" leftSection={<IconPlus size={18} />} onClick={create.open}>
                  Crear agente
                </Button>
              </Stack>
            ) : (
              <Table.ScrollContainer minWidth={900}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>Voz</Table.Th>
                      <Table.Th>Versión</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Actualizado</Table.Th>
                      <Table.Th>Probar</Table.Th>
                      <Table.Th>Link para llamar</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {list.map((a) => (
                      <Table.Tr key={a.id}>
                        <Table.Td>
                          <Anchor component={Link} to={`/agents/${a.id}`} fw={600} size="sm">
                            {a.name}
                          </Anchor>
                          {/* El slug (interno) va debajo del nombre: deja lugar al link para llamar. */}
                          <Text size="xs" c="dimmed" className="mono">
                            {a.slug}
                          </Text>
                          {a.own_agent && (
                            <Badge color="gray" mt={2}>
                              Tu propio agente
                            </Badge>
                          )}
                          {a.description && (
                            <Text size="xs" c="dimmed" lineClamp={1}>
                              {a.description}
                            </Text>
                          )}
                        </Table.Td>
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
                        <Table.Td>
                          <Button
                            component={Link}
                            to={`/probar?agent=${a.id}`}
                            variant="subtle"
                            size="compact-sm"
                            leftSection={<IconPlayerPlay size={14} />}
                            disabled={a.archived}
                          >
                            Probar
                          </Button>
                        </Table.Td>
                        <Table.Td>
                          <CallLinkCell agent={a} />
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
      <NewAgentModal key={String(creating)} opened={creating} onClose={create.close} />
    </>
  );
}
