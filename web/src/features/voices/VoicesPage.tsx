import { Badge, Button, Card, Grid, Group, Stack, Table, Text, Title } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatNumber } from '@/lib/format';
import { EMPTY_VOICE_FILTERS, useVoices, type VoiceFilters } from './api';
import { VOICE_METRICS_HINT, VoiceFiltersBar } from './VoiceFiltersBar';
import { VoicePreview } from './VoicePreview';

export function VoicesPage() {
  const [filters, setFilters] = useState<VoiceFilters>(EMPTY_VOICE_FILTERS);
  const [debounced] = useDebouncedValue(filters, 300);
  const voices = useVoices(debounced);
  const [selected, setSelected] = useState<string | null>(null);
  const current = selected ?? voices.data?.[0]?.nombre ?? null;

  return (
    <>
      <PageHeader title="Voces" description="Catálogo de voces del TTS. Elegí una y probala con tu texto." />
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card>
            <Stack gap="sm">
              <VoiceFiltersBar value={filters} onChange={setFilters} />
              <Text size="xs" c="dimmed">
                {VOICE_METRICS_HINT}
              </Text>
              <QueryState query={voices}>
                {(list) =>
                  list.length === 0 ? (
                    <EmptyState>Ninguna voz con esos filtros.</EmptyState>
                  ) : (
                    <Table.ScrollContainer minWidth={420}>
                      <Table>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>Voz</Table.Th>
                            <Table.Th>Género</Table.Th>
                            <Table.Th ta="right">WER</Table.Th>
                            <Table.Th ta="right">car/s</Table.Th>
                            <Table.Th />
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {list.map((v) => (
                            <Table.Tr
                              key={v.nombre}
                              bg={v.nombre === current ? 'var(--mantine-color-blue-light)' : undefined}
                              style={{ cursor: 'pointer' }}
                              onClick={() => setSelected(v.nombre)}
                            >
                              <Table.Td fw={600}>{v.nombre}</Table.Td>
                              <Table.Td>
                                <Badge color="gray">{v.genero}</Badge>
                              </Table.Td>
                              <Table.Td ta="right" className="mono">
                                {formatNumber(v.wer)}%
                              </Table.Td>
                              <Table.Td ta="right" className="mono">
                                {formatNumber(v.car_s)}
                              </Table.Td>
                              <Table.Td ta="right">
                                <Button
                                  size="compact-sm"
                                  variant={v.nombre === current ? 'light' : 'subtle'}
                                  onClick={() => setSelected(v.nombre)}
                                >
                                  {v.nombre === current ? 'Elegida' : 'Elegir'}
                                </Button>
                              </Table.Td>
                            </Table.Tr>
                          ))}
                        </Table.Tbody>
                      </Table>
                    </Table.ScrollContainer>
                  )
                }
              </QueryState>
            </Stack>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card pos="sticky" top={76}>
            <Stack gap="sm">
              <Group justify="space-between">
                <Title order={4}>Probar</Title>
                {current && <Badge color="blue">{current}</Badge>}
              </Group>
              <VoicePreview voice={current} />
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </>
  );
}
