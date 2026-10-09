import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconSend } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { errorMessage } from '@/api/errors';
import type { AgentDetail, ChatMessage, ConversationState } from '@/api/types';
import { useReadOnly } from '@/features/auth/readOnly';
import { useSendTurn, useStartConversation } from '@/features/calls/api';
import { Dash } from '@/components/Badges';
import { ChatView } from '@/features/calls/ChatView';
import { formatValue } from '@/lib/format';
import { WORKFLOW_STATUS } from '@/lib/labels';

interface Session {
  id: string;
  state: ConversationState;
  nextObjective: string | null;
}

/** Conversacion por texto con el agente (sin llamada): POST /conversations y /turns. */
export function TextChat({ agent }: { agent: AgentDetail }) {
  const start = useStartConversation();
  const turn = useSendTurn();
  // Solo lectura: cada turno consume el LLM.
  const readOnly = useReadOnly();
  const [session, setSession] = useState<Session | null>(null);
  const [text, setText] = useState('');
  const [pending, setPending] = useState<string | null>(null);

  const begin = () =>
    start.mutate(agent.id, {
      onSuccess: (r) => {
        turn.reset();
        setSession({ id: r.conversation_id, state: r.state, nextObjective: null });
      },
    });

  const send = () => {
    const msg = text.trim();
    if (!session || !msg) return;
    setPending(msg);
    setText('');
    turn.mutate(
      { conversationId: session.id, message: msg },
      {
        onSuccess: (r) => setSession({ id: session.id, state: r.state, nextObjective: r.next_objective }),
        onError: () => setText(msg),
        onSettled: () => setPending(null),
      },
    );
  };

  const messages: ChatMessage[] = session ? [...session.state.messages] : [];
  if (pending) messages.push({ role: 'user', text: pending });
  const completed = session?.state.status === 'completed';

  return (
    <Card>
      <Group justify="space-between" mb="sm" wrap="wrap">
        <Stack gap={0}>
          <Title order={4}>Conversación por texto</Title>
          <Text size="xs" c="dimmed">
            Probá el agente escribiendo, sin llamada ni voz. Queda registrada como conversación de origen API.
          </Text>
        </Stack>
        <Button
          variant="default"
          onClick={begin}
          loading={start.isPending}
          disabled={agent.archived || readOnly}
        >
          {session ? 'Empezar de nuevo' : 'Empezar conversación'}
        </Button>
      </Group>
      {agent.archived && (
        <Alert color="yellow" mb="sm">
          El agente está archivado: desarchivalo para probarlo.
        </Alert>
      )}
      {start.isError && (
        <Alert color="red" mb="sm">
          {errorMessage(start.error)}
        </Alert>
      )}
      {session && (
        <Grid gutter="md">
          <Grid.Col span={{ base: 12, md: 7 }}>
            <Stack gap="sm">
              <ChatView
                messages={messages}
                agentLabel={agent.name}
                userLabel="Vos"
                maxHeight={420}
                showLlm={false}
              />
              {turn.isError && (
                <Alert color="red" title="El agente no respondió">
                  {errorMessage(turn.error)}
                </Alert>
              )}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  send();
                }}
              >
                <Group gap="xs" wrap="nowrap">
                  <TextInput
                    style={{ flex: 1 }}
                    placeholder={
                      completed ? 'La conversación terminó' : 'Escribí como si fueras el interesado…'
                    }
                    value={text}
                    onChange={(e) => setText(e.currentTarget.value)}
                    disabled={turn.isPending || completed || readOnly}
                    maxLength={4000}
                    aria-label="Mensaje"
                  />
                  <Button
                    type="submit"
                    loading={turn.isPending}
                    disabled={!text.trim() || completed || readOnly}
                    leftSection={<IconSend size={16} />}
                  >
                    Enviar
                  </Button>
                </Group>
              </form>
              <Anchor component={Link} to={`/calls/${session.id}`} size="xs">
                Ver el detalle de esta conversación (con la salida del LLM)
              </Anchor>
            </Stack>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Stack gap="xs">
              <Group gap="xs">
                <Text size="sm" fw={600}>
                  Estado
                </Text>
                <Badge color={WORKFLOW_STATUS[session.state.status]?.color ?? 'gray'}>
                  {WORKFLOW_STATUS[session.state.status]?.label ?? session.state.status}
                </Badge>
              </Group>
              <Text size="sm">
                <Text span c="dimmed">
                  Próximo objetivo:{' '}
                </Text>
                <b className="mono">{session.nextObjective ?? '–'}</b>
              </Text>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Dato</Table.Th>
                    <Table.Th>Valor extraído</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {Object.entries(session.state.fields).map(([name, value]) => (
                    <Table.Tr key={name}>
                      <Table.Td className="mono">{name}</Table.Td>
                      <Table.Td>{value != null ? formatValue(value) : <Dash />}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Stack>
          </Grid.Col>
        </Grid>
      )}
    </Card>
  );
}
