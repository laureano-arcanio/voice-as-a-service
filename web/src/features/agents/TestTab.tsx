import { Anchor, Card, Group, Stack, Title } from '@mantine/core';
import { IconHistory } from '@tabler/icons-react';
import { Link } from 'react-router';
import type { AgentDetail } from '@/api/types';
import { NewCallForm } from '@/features/calls/NewCallForm';
import { TextChat } from './TextChat';

export function TestTab({ agent }: { agent: AgentDetail }) {
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
          Llamada con este agente
        </Title>
        <NewCallForm fixedAgent={agent} />
      </Card>
    </Stack>
  );
}
