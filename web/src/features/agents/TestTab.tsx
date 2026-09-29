import { Card, Stack, Title } from '@mantine/core';
import type { AgentDetail } from '@/api/types';
import { NewCallForm } from '@/features/calls/NewCallForm';
import { TextChat } from './TextChat';

export function TestTab({ agent }: { agent: AgentDetail }) {
  return (
    <Stack gap="md">
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
