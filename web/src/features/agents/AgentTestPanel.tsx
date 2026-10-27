import { Anchor, Card, Group, Stack, Title } from '@mantine/core';
import { IconHistory } from '@tabler/icons-react';
import { Link } from 'react-router';
import type { Agent } from '@/api/types';
import { TestCallButton } from '@/features/calls/TestCallButton';
import { CallLinkCard } from './CallLinkTab';
import { TextChat } from './TextChat';

/**
 * Probar un agente: por texto, con una llamada y con su link para llamar. Lo usan la
 * pestaña Probar del agente y la pantalla Playground (`/probar`).
 */
export function AgentTestPanel({ agent }: { agent: Agent }) {
  return (
    <Stack gap="md">
      <Group justify="flex-end">
        <Anchor component={Link} to={`/calls?agent=${agent.id}`} size="sm">
          <Group gap={4} component="span">
            <IconHistory size={14} />
            Ver conversaciones de este agente (incluidas las pruebas)
          </Group>
        </Anchor>
      </Group>
      <TextChat agent={agent} />
      <Card>
        <Title order={4} mb="sm">
          Probar por voz
        </Title>
        <TestCallButton agent={agent} />
      </Card>
      <CallLinkCard agent={agent} />
    </Stack>
  );
}
