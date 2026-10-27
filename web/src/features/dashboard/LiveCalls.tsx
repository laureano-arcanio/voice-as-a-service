import { Button, Card, Group, Table, Text, Title } from '@mantine/core';
import { Link } from 'react-router';
import type { CallSummary } from '@/api/types';
import { CallStatusBadge, LiveBadge, OriginBadge } from '@/components/Badges';
import { useAreaPath } from '@/features/support/paths';
import { formatDateTime, formatValue } from '@/lib/format';
import { callPerson } from '@/lib/labels';

/** Sin agente: quién habló ("Llamó: Ana"). */
function personText(c: CallSummary): string {
  const who = callPerson(c);
  return who ? `${who.verb}: ${who.name}` : '–';
}

export function LiveCalls({ calls, showClient }: { calls: CallSummary[]; showClient: boolean }) {
  const areaPath = useAreaPath();
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
                <Table.Td>{c.agent_name ?? personText(c)}</Table.Td>
                <Table.Td>
                  <OriginBadge mode={c.mode} phone={c.phone} answeredBy={c.answered_by} />
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
                  {c.agent_id || c.required ? `${c.captured}/${c.required} datos` : '–'}
                </Table.Td>
                <Table.Td ta="right">
                  <Button component={Link} to={areaPath(`/calls/${c.id}`)} variant="subtle" size="compact-sm">
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
