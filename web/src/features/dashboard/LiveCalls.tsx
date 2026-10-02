import { Button, Card, Group, Table, Text, Title } from '@mantine/core';
import { Link } from 'react-router';
import type { CallSummary } from '@/api/types';
import { CallStatusBadge, LiveBadge, OriginBadge } from '@/components/Badges';
import { formatDateTime, formatValue } from '@/lib/format';

export function LiveCalls({ calls, showClient }: { calls: CallSummary[]; showClient: boolean }) {
  if (!calls.length) return null;
  return (
    <Card>
      <Group gap="xs" mb="sm">
        <Title order={4}>En vivo</Title>
        <LiveBadge>{calls.length}</LiveBadge>
      </Group>
      <Table.ScrollContainer minWidth={700}>
        <Table>
          <Table.Tbody>
            {calls.map((c) => (
              <Table.Tr key={c.id}>
                <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(c.created_at)}</Table.Td>
                {showClient && <Table.Td>{c.client_name}</Table.Td>}
                <Table.Td>{c.agent_name}</Table.Td>
                <Table.Td>
                  <OriginBadge mode={c.mode} phone={c.phone} />
                </Table.Td>
                <Table.Td>
                  <CallStatusBadge status={c.status} />
                </Table.Td>
                <Table.Td>
                  {formatValue(c.contact_name) || '–'}
                  {formatValue(c.company) && (
                    <Text span c="dimmed" size="sm">
                      {' '}
                      · {formatValue(c.company)}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td className="mono">
                  {c.captured}/{c.required} datos
                </Table.Td>
                <Table.Td ta="right">
                  <Button component={Link} to={`/calls/${c.id}`} variant="subtle" size="compact-sm">
                    Ver en vivo
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Card>
  );
}
