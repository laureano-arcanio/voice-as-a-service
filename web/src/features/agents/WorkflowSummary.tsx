import { Card, List, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import type { Definition } from '@/api/types';
import { Dash, OutcomeBadge } from '@/components/Badges';
import { useLlmConnections } from '@/features/llm/api';
import { LOCAL_LABEL } from '@/features/llm/labels';
import { conditionLabel, firstLines, readWorkflow } from './definition';

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600} component="div">
        {children || '–'}
      </Text>
    </Stack>
  );
}

/** Vista legible de la definicion (como el viejo templates/workflow.html). */
export function WorkflowSummary({ definition, clientId }: { definition: Definition; clientId?: string }) {
  const connections = useLlmConnections(clientId).data ?? [];
  const w = readWorkflow(definition);
  // "atentina-conversational-v1" o "atentina-conversational-v1, desde el turno 4 Claude (claude-haiku-5-5)".
  const model = w.llm.length
    ? w.llm
        .map((st, i) => {
          const name = st.connection
            ? `${connections.find((c) => c.id === st.connection)?.name ?? 'Conexión dada de baja'} (${st.model})`
            : LOCAL_LABEL;
          return i === 0 ? name : `desde el turno ${st.fromTurn} ${name}`;
        })
        .join(', ')
    : LOCAL_LABEL;
  return (
    <Stack gap="md">
      <Card>
        <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} spacing="md">
          <Item label="Agente">{w.agent.name}</Item>
          <Item label="Idioma">{w.agent.language}</Item>
          <Item label="Versión">{w.version != null ? `v${w.version}` : '–'}</Item>
          <Item label="Voz">{w.agent.voice ?? 'La predeterminada'}</Item>
          <Item label="Modelo">{w.external ? 'Tu propio agente' : model}</Item>
          <Item label="Grabación">{w.recordAudio ? 'Sí, por turno' : 'No'}</Item>
          <Item label="Resumen por email">{w.callSummaryEmail ? 'Sí, al cliente' : 'No'}</Item>
          <Item label="Ventana de WhatsApp">
            {w.waSessionMinutes != null ? `${w.waSessionMinutes} min` : '1440 min (default)'}
          </Item>
        </SimpleGrid>
        <Title order={5} mt="lg" mb={4}>
          Prompt
        </Title>
        <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
          {firstLines(w.prompt) || '–'}
        </Text>
        <Title order={5} mt="md" mb={4}>
          Primer mensaje
        </Title>
        <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
          {w.firstMessage || '–'}
        </Text>
        <Text size="xs" c="dimmed" mt={4}>
          {w.firstMessageAudio ? 'Audio pregenerado' : 'Sintetizado en vivo'}, tras {w.firstMessageDelayMs} ms
        </Text>
      </Card>

      {w.variables.length > 0 && (
        <Card>
          <Title order={4} mb="sm">
            Variables
          </Title>
          <Table.ScrollContainer minWidth={640}>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Variable</Table.Th>
                  <Table.Th>Valor por defecto</Table.Th>
                  <Table.Th>Descripción</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {w.variables.map((v) => (
                  <Table.Tr key={v.name}>
                    <Table.Td>
                      <Text size="sm" className="mono">
                        {`{{${v.name}}}`}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" className="mono">
                        {v.default || <Dash />}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{v.description || <Dash />}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Card>
      )}

      {w.clientTools.length > 0 && (
        <Card>
          <Title order={4} mb={4}>
            Herramientas de la cuenta
          </Title>
          <Text size="xs" c="dimmed" mb="sm">
            APIs y funciones que el agente puede usar en la conversación.
          </Text>
          <List size="sm" spacing={4}>
            {w.clientTools.map((g) => (
              <List.Item key={g.tool}>
                <Text span className="mono">
                  {g.tool}
                </Text>
              </List.Item>
            ))}
          </List>
        </Card>
      )}

      <Card>
        <Title order={4} mb="sm">
          Análisis al terminar
        </Title>
        {!w.external && (
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md" mb={w.analysisInstructions ? 'md' : 0}>
            <Item label="Resumen">{w.summary ? 'Sí, un párrafo' : 'No'}</Item>
            <Item label="Datos">{w.fields.length ? `${w.fields.length}` : 'Ninguno'}</Item>
          </SimpleGrid>
        )}
        {w.external && (
          <Text size="xs" c="dimmed" mb="sm">
            Con tu propio agente el análisis lo hace tu agente: acá solo se eligen los resultados que puede
            devolver al llamar a end_call.
          </Text>
        )}
        {w.analysisInstructions && (
          <>
            <Title order={5} mt="md" mb={4}>
              Instrucciones
            </Title>
            <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
              {w.analysisInstructions}
            </Text>
          </>
        )}
        {!w.external && (
          <Table.ScrollContainer minWidth={760}>
            <Table mt="md">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Dato</Table.Th>
                  <Table.Th>Tipo</Table.Th>
                  <Table.Th>Descripción</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {w.fields.map((f) => (
                  <Table.Tr key={f.name}>
                    <Table.Td>
                      <Text size="sm" fw={600}>
                        {f.label || f.name}
                      </Text>
                      <Text size="xs" c="dimmed" className="mono">
                        {f.name}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{f.type}</Text>
                      {f.options && (
                        <Text size="xs" c="dimmed">
                          {f.options.join(' / ')}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{f.description}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
        <Title order={5} mt="md" mb={4}>
          Resultados
        </Title>
        <Text size="xs" c="dimmed" mb="sm">
          Clasifican la conversación al terminar (el primero cuyas condiciones se cumplen); el último es el de
          por defecto.
        </Text>
        <Table.ScrollContainer minWidth={640}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Resultado</Table.Th>
                <Table.Th>Cuándo</Table.Th>
                <Table.Th>No volver a llamar</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {w.outcomes.map((o) => (
                <Table.Tr key={o.id}>
                  <Table.Td>
                    <OutcomeBadge label={o.label} goal={o.goal} />
                    {o.goal && (
                      <Text size="xs" c="dimmed" mt={2}>
                        Cumple el objetivo
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{conditionLabel(o.when)}</Text>
                  </Table.Td>
                  <Table.Td>{o.noContact ? 'Sí' : <Dash />}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>
    </Stack>
  );
}
