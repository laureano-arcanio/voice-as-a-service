import { Anchor, Button, Card, SegmentedControl, Group, Stack, Table, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { Link } from 'react-router';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatArs, formatDateTime } from '@/lib/format';
import { PAYMENT_METHOD, TAX_CONDITION } from '@/lib/labels';
import { notifyError } from '@/lib/notify';
import { useMarkInvoiced, usePayments, useSubscriptions } from './api';
import { formatDay } from './format';
import { SubscriptionBadge } from './parts';

function SubscriptionsCard() {
  const subs = useSubscriptions();
  return (
    <Card>
      <Title order={4} mb="sm">
        Planes pagos
      </Title>
      <QueryState query={subs}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>No hay planes pagos ni pedidos.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={820}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Cliente</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Tier</Table.Th>
                    <Table.Th>Medio</Table.Th>
                    <Table.Th>Pago hasta</Table.Th>
                    <Table.Th>Gracia hasta</Table.Th>
                    <Table.Th ta="right">Próximo cobro</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((s) => (
                    <Table.Tr key={s.id}>
                      <Table.Td>
                        <Anchor component={Link} to={`/clients/${s.client_id}`} size="sm" fw={600}>
                          {s.client_name}
                        </Anchor>
                      </Table.Td>
                      <Table.Td>
                        <SubscriptionBadge sub={s} />
                      </Table.Td>
                      <Table.Td>
                        {s.tier.name}
                        {s.pending_tier && s.status !== 'pending' && (
                          <Text size="xs" c="dimmed">
                            pidió {s.pending_tier.name}
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>{PAYMENT_METHOD[s.method] ?? s.method}</Table.Td>
                      <Table.Td>{formatDay(s.current_period_end)}</Table.Td>
                      <Table.Td>{formatDay(s.grace_until)}</Table.Td>
                      <Table.Td ta="right" className="mono">
                        {formatArs(s.amount_due)}
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
  );
}

function PaymentsCard() {
  const [filter, setFilter] = useState<'pending' | 'all'>('pending');
  const payments = usePayments(filter === 'pending' ? false : null);
  const mark = useMarkInvoiced();
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Pagos</Title>
        <SegmentedControl
          size="xs"
          value={filter}
          onChange={(v) => setFilter(v as 'pending' | 'all')}
          data={[
            { value: 'pending', label: 'Sin facturar' },
            { value: 'all', label: 'Todos' },
          ]}
        />
      </Group>
      <QueryState query={payments}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>{filter === 'pending' ? 'No hay pagos sin facturar.' : 'No hay pagos.'}</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={1000}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Cliente</Table.Th>
                    <Table.Th>Factura a</Table.Th>
                    <Table.Th>Tier</Table.Th>
                    <Table.Th>Medio</Table.Th>
                    <Table.Th ta="right">Monto</Table.Th>
                    <Table.Th>Nota</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((p) => (
                    <Table.Tr key={p.id}>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDay(p.paid_on)}</Table.Td>
                      <Table.Td>
                        <Anchor component={Link} to={`/clients/${p.client_id}`} size="sm">
                          {p.client_name}
                        </Anchor>
                      </Table.Td>
                      <Table.Td>
                        {p.legal_name ? (
                          <Stack gap={0}>
                            <Text size="sm">{p.legal_name}</Text>
                            <Text size="xs" c="dimmed">
                              <span className="mono">{p.tax_id}</span> ·{' '}
                              {TAX_CONDITION[p.tax_condition ?? ''] ?? ''}
                            </Text>
                          </Stack>
                        ) : (
                          <Text size="sm" c="yellow">
                            Sin datos
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>{p.tier_name ?? '–'}</Table.Td>
                      <Table.Td>{PAYMENT_METHOD[p.method] ?? p.method}</Table.Td>
                      <Table.Td ta="right" className="mono">
                        {formatArs(p.amount_ars)}
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed" lineClamp={2}>
                          {p.note || '–'}
                          {p.recorded_by_email ? ` · ${p.recorded_by_email}` : ''}
                        </Text>
                      </Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>
                        {p.invoiced_at ? (
                          <Group gap={4} wrap="nowrap" justify="flex-end">
                            <Text size="xs" c="dimmed">
                              Facturado {formatDateTime(p.invoiced_at)}
                            </Text>
                            <Button
                              variant="subtle"
                              size="compact-sm"
                              color="gray"
                              onClick={() =>
                                mark.mutate({ id: p.id, invoiced: false }, { onError: (e) => notifyError(e) })
                              }
                            >
                              Deshacer
                            </Button>
                          </Group>
                        ) : (
                          <Button
                            variant="subtle"
                            size="compact-sm"
                            onClick={() =>
                              mark.mutate({ id: p.id, invoiced: true }, { onError: (e) => notifyError(e) })
                            }
                          >
                            Marcar facturado
                          </Button>
                        )}
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
  );
}

/** Cobros (admin): planes pagos y pedidos abiertos, y pagos para facturar. */
export function BillingPage() {
  return (
    <>
      <PageHeader
        title="Cobros"
        description="Pedidos de plan, vencimientos y pagos para facturar. Los pagos por transferencia se registran desde la ficha del cliente."
      />
      <Stack gap="md">
        <SubscriptionsCard />
        <PaymentsCard />
      </Stack>
    </>
  );
}
