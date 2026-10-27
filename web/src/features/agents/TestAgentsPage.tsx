import { Anchor, Card, Group, Radio, Select, SimpleGrid, Stack, Text, TextInput } from '@mantine/core';
import { IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { AgentTestPanel } from './AgentTestPanel';
import { useAgents } from './api';

// Con más agentes que estos, aparece el buscador.
const SEARCH_FROM = 6;

/** Playground (`/probar`): se elige el agente en una tarjeta y abajo se prueba. */
export function TestAgentsPage() {
  const isAdmin = useIsAdmin();
  const [params, setParams] = useSearchParams();
  const clientId = params.get('client') ?? undefined;
  const agents = useAgents(clientId);
  const clients = useClients(isAdmin);
  const clientName = new Map((clients.data ?? []).map((c) => [c.id, c.name]));
  const [search, setSearch] = useState('');
  const many = (agents.data?.length ?? 0) > SEARCH_FROM;

  const set = (k: string, v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set(k, v);
        else next.delete(k);
        if (k === 'client') next.delete('agent');
        return next;
      },
      { replace: true },
    );

  return (
    <>
      <PageHeader
        title="Playground"
        description="Elegí un agente y probalo por texto, con una llamada o con su link para llamar."
      />
      {(isAdmin || many) && (
        <Group mb="md" align="flex-end">
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
          {many && (
            <TextInput
              label="Buscar"
              placeholder="Nombre u objetivo"
              leftSection={<IconSearch size={16} />}
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              w={260}
            />
          )}
        </Group>
      )}
      <QueryState query={agents}>
        {(list) => {
          if (list.length === 0)
            return (
              <Card>
                <EmptyState>
                  No hay agentes activos para probar.{' '}
                  <Anchor component={Link} to="/agents">
                    Creá uno en Agentes
                  </Anchor>
                  .
                </EmptyState>
              </Card>
            );
          const selected = list.find((a) => a.id === params.get('agent')) ?? list[0];
          const q = search.trim().toLowerCase();
          // El elegido queda visible aunque no coincida con la búsqueda.
          const shown = q
            ? list.filter(
                (a) =>
                  a.id === selected.id ||
                  `${a.name} ${a.objective} ${a.description}`.toLowerCase().includes(q),
              )
            : list;
          return (
            <Stack gap="md">
              <Radio.Group value={selected.id} onChange={(v) => set('agent', v)} aria-label="Agente">
                <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="xs">
                  {shown.map((a) => (
                    <Radio.Card key={a.id} value={a.id} p="sm">
                      <Group wrap="nowrap" align="flex-start" gap="sm">
                        <Radio.Indicator />
                        <Stack gap={2} style={{ minWidth: 0 }}>
                          <Text size="sm" fw={600} truncate>
                            {a.name}
                          </Text>
                          <Text size="xs" c="dimmed" lineClamp={2}>
                            {a.objective || a.description || 'Sin objetivo en la definición.'}
                          </Text>
                          {isAdmin && !clientId && (
                            <Text size="xs" c="dimmed">
                              {clientName.get(a.client_id) ?? ''}
                            </Text>
                          )}
                        </Stack>
                      </Group>
                    </Radio.Card>
                  ))}
                </SimpleGrid>
              </Radio.Group>
              <AgentTestPanel key={selected.id} agent={selected} />
            </Stack>
          );
        }}
      </QueryState>
    </>
  );
}
