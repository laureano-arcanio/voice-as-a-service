import { Badge, Button, Card, Code, Group, Stack, Table, Text, Title } from '@mantine/core';
import { IconPlugConnected } from '@tabler/icons-react';
import { confirmAction } from '@/components/confirm';
import { CopyIcon } from '@/components/Copy';
import { EmptyState, QueryState } from '@/components/QueryState';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import type { OAuthGrant } from '@/api/types';
import { useMcpUsage, useOAuthGrants, useRevokeGrant } from './api';

function Row({ label, value }: { label: string; value: string }) {
  return (
    <Group gap="xs" wrap="nowrap" align="flex-start">
      <Text size="sm" w={110} fw={600} style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Code style={{ wordBreak: 'break-all' }}>{value}</Code>
      <CopyIcon value={value} label={`Copiar ${label.toLowerCase()}`} />
    </Group>
  );
}

/** Cuántas veces usaron los agentes cada herramienta en los últimos 30 días. */
function McpUsage({ clientId }: { clientId: string }) {
  const usage = useMcpUsage(clientId);
  return (
    <QueryState query={usage}>
      {(u) =>
        u.tools.length === 0 ? (
          <EmptyState>Todavía ningún agente usó el MCP en los últimos {u.days} días.</EmptyState>
        ) : (
          <>
            <Text size="sm" c="dimmed" mb="xs">
              {u.calls} usos en los últimos {u.days} días{u.errors ? `, ${u.errors} con error` : ''}.
            </Text>
            <Table.ScrollContainer minWidth={480}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Herramienta</Table.Th>
                    <Table.Th ta="right">Usos</Table.Th>
                    <Table.Th ta="right">Con error</Table.Th>
                    <Table.Th ta="right">Tiempo medio</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {u.tools.map((t) => (
                    <Table.Tr key={t.tool}>
                      <Table.Td className="mono">{t.tool}</Table.Td>
                      <Table.Td ta="right">{t.calls}</Table.Td>
                      <Table.Td ta="right">{t.errors}</Table.Td>
                      <Table.Td ta="right">{t.avg_ms} ms</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </>
        )
      }
    </QueryState>
  );
}

/** Cómo conectar un agente de IA (Claude, ChatGPT, Cursor) por MCP, los que ya están conectados y su uso. */
export function McpAccess({ clientId }: { clientId: string }) {
  // El servidor MCP en este host (app.atentina.com.ar/mcp o mcp.atentina.com.ar/mcp).
  const url = `${location.origin}/mcp`;
  const grants = useOAuthGrants(clientId);
  const revoke = useRevokeGrant(clientId);

  const doRevoke = async (g: OAuthGrant) => {
    if (
      await confirmAction({
        title: 'Desconectar agente',
        message: `${g.app_name} deja de tener acceso a la cuenta. Para volver a usarlo, hay que conectarlo de nuevo.`,
        confirmLabel: 'Desconectar',
        danger: true,
      })
    ) {
      revoke.mutate(g.id, {
        onSuccess: () => notifySuccess('Agente desconectado.'),
        onError: (e) => notifyError(e),
      });
    }
  };

  return (
    <Card>
      <Group gap="xs" mb={4}>
        <IconPlugConnected size={20} />
        <Title order={4}>Agentes de IA (MCP)</Title>
      </Group>
      <Text size="sm" c="dimmed" mb="sm">
        Conectá Claude, ChatGPT, Cursor u otro agente compatible con MCP para que maneje tu cuenta: armar y probar
        agentes, revisar llamadas, cargar contactos y campañas. Agregá esta URL como conector e iniciá sesión con
        tu usuario.
      </Text>
      <Stack gap="xs" mb="md">
        <Row label="URL" value={url} />
        <Row label="Claude Code" value={`claude mcp add --transport http atentina ${url}`} />
      </Stack>
      <Text size="xs" c="dimmed" mb="md">
        También anda con una API key con el alcance &quot;Agentes de IA (MCP)&quot; (o &quot;solo lectura&quot;) en{' '}
        <Code>Authorization: Bearer &lt;key&gt;</Code>, para agentes que no inician sesión.
      </Text>
      <Title order={5} mb="xs">
        Agentes conectados
      </Title>
      <QueryState query={grants}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>Ningún agente conectado. Aparecen acá cuando alguien autoriza uno con su usuario.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={620}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>App</Table.Th>
                    <Table.Th>Lo conectó</Table.Th>
                    <Table.Th>Conectado</Table.Th>
                    <Table.Th>Último uso</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((g) => (
                    <Table.Tr key={g.id}>
                      <Table.Td>
                        <Group gap={6} wrap="nowrap">
                          {g.app_name}
                          {!g.verified && <Badge color="gray">sin verificar</Badge>}
                        </Group>
                      </Table.Td>
                      <Table.Td>{g.user_email}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(g.created_at)}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>
                        {g.last_used_at ? formatDateTime(g.last_used_at) : 'Nunca'}
                      </Table.Td>
                      <Table.Td ta="right">
                        <Button size="compact-sm" variant="subtle" color="red" onClick={() => void doRevoke(g)}>
                          Desconectar
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
      <Title order={5} mt="lg" mb="xs">
        Uso por herramienta
      </Title>
      <McpUsage clientId={clientId} />
    </Card>
  );
}
