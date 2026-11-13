import { Alert, Anchor, Box, Button, Card, Group, Stack, Text, TextInput, Title } from '@mantine/core';
import { IconHistory, IconMicrophone } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import type { AgentDetail } from '@/api/types';
import { TestVariables } from './TestVariables';
import { useTestVariables } from './testVariables';
import { TextChat } from './TextChat';
import { VoiceCallModal } from './VoiceCallModal';

/** Tiene pre-call o post-call: las pruebas los ejecutan de verdad (docs/features/HERRAMIENTAS.md). */
function hasAutomaticTools(agent: AgentDetail): boolean {
  const w = agent.definition?.workflows as { pre_call?: unknown; post_call?: unknown } | undefined;
  return !!(w?.pre_call || w?.post_call);
}

/**
 * Probar un agente (pestaña Probar): hablarle desde el navegador o escribirle, con un número de quien llama
 * simulado y los valores de sus variables. Las pruebas corren el pre-call y el post-call del agente.
 */
export function AgentTestPanel({ agent }: { agent: AgentDetail }) {
  const [phone, setPhone] = useState('');
  // El número y las variables quedan fijos mientras dura la llamada.
  const [talking, setTalking] = useState<{
    phone?: string;
    variables: Record<string, string>;
  } | null>(null);
  const callerPhone = phone.trim() || undefined;
  const test = useTestVariables(agent.id, agent.definition);

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
      {hasAutomaticTools(agent) && (
        <Alert color="yellow" title="Las pruebas ejecutan las herramientas automáticas">
          Las pruebas desde acá ejecutan las herramientas automáticas del agente, antes y después de la
          conversación, como en una llamada real: si registran algo o cobran, lo hacen de verdad. Por texto,
          la de después corre al terminar la conversación o a los 10 minutos sin mensajes.
        </Alert>
      )}
      <Card>
        <Group justify="space-between" align="flex-end" wrap="wrap">
          <Stack gap={0} style={{ flex: 1, minWidth: 260 }}>
            <Title order={4} mb="xs">
              Probar el agente
            </Title>
            <TextInput
              label="Número de quien llama (simulado)"
              description="Llega a las herramientas como {{call.phone}}. No se llama a ese número."
              placeholder="+5491155551234"
              value={phone}
              onChange={(e) => setPhone(e.currentTarget.value)}
              maxLength={32}
              inputMode="tel"
            />
          </Stack>
          <Button
            leftSection={<IconMicrophone size={16} />}
            onClick={() => setTalking({ phone: callerPhone, variables: test.variables })}
            disabled={agent.archived}
          >
            Hablar
          </Button>
        </Group>
        {agent.archived && (
          <Text size="xs" c="dimmed" mt="xs">
            El agente está archivado: desarchivalo para probarlo.
          </Text>
        )}
        <Box mt="md">
          <TestVariables
            rows={test.rows}
            onChange={test.setRows}
            fixedNames={test.names.map((n) => n.name)}
          />
        </Box>
      </Card>
      {talking && (
        <VoiceCallModal
          agent={agent}
          opened
          onClose={() => setTalking(null)}
          callerPhone={talking.phone}
          variables={talking.variables}
          workflows
        />
      )}
      <TextChat agent={agent} callerPhone={callerPhone} variables={test.variables} />
    </Stack>
  );
}
