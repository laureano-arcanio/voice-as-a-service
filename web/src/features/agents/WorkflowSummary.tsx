import { Badge, Card, List, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import type { Definition } from '@/api/types';
import { OutcomeBadge } from '@/components/Badges';
import { ENGINE } from '@/lib/labels';
import { conditionLabel, readWorkflow, requiredLabel } from './definition';

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
export function WorkflowSummary({ definition }: { definition: Definition }) {
  const w = readWorkflow(definition);
  return (
    <Stack gap="md">
      <Card>
        <Text size="xs" c="dimmed" mb="sm">
          Las preguntas son sugeridas: el agente las reformula y completa los datos en el orden que surjan.
        </Text>
        <SimpleGrid cols={{ base: 2, sm: 5 }} spacing="md">
          <Item label="Agente">
            {w.agent.name}
            {w.agent.role && ` (${w.agent.role})`}
          </Item>
          <Item label="Idioma">{w.agent.language}</Item>
          <Item label="Versión">{w.version != null ? `v${w.version}` : '–'}</Item>
          <Item label="Motor">{ENGINE[w.engine] ?? w.engine}</Item>
          <Item label="Voz">{w.agent.voice ?? 'La predeterminada'}</Item>
        </SimpleGrid>
        <Title order={5} mt="lg" mb={4}>
          Objetivo
        </Title>
        <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
          {w.objective || '–'}
        </Text>
        <Title order={5} mt="md" mb={4}>
          Apertura
        </Title>
        <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
          {w.opening || '–'}
        </Text>
        <Title order={5} mt="md" mb={4}>
          Reglas
        </Title>
        {w.rules.length ? (
          <List size="sm" spacing={4}>
            {w.rules.map((r, i) => (
              <List.Item key={i}>{r}</List.Item>
            ))}
          </List>
        ) : (
          <Text size="sm" c="dimmed">
            Sin reglas.
          </Text>
        )}
        {w.knowledge && (
          <>
            <Title order={5} mt="md" mb={4}>
              Conocimiento
            </Title>
            <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
              {w.knowledge}
            </Text>
          </>
        )}
      </Card>

      <Card>
        <Title order={4} mb="sm">
          Datos a obtener
        </Title>
        <Table.ScrollContainer minWidth={760}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={60}>Orden</Table.Th>
                <Table.Th>Dato</Table.Th>
                <Table.Th>Tipo</Table.Th>
                <Table.Th>Obligatorio</Table.Th>
                <Table.Th>Pregunta sugerida</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {w.fields.map(([name, f]) => (
                <Table.Tr key={name}>
                  <Table.Td ta="center">{f.priority}</Table.Td>
                  <Table.Td>
                    <Text size="sm" fw={600}>
                      {name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {f.description}
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
                  <Table.Td>{requiredLabel(f)}</Table.Td>
                  <Table.Td>
                    <Text size="sm">{f.question}</Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      <Card>
        <Title order={4} mb={4}>
          Resultados
        </Title>
        <Text size="xs" c="dimmed" mb="sm">
          Clasifican la llamada al terminar (el primero cuyas condiciones se cumplen). El mensaje es una guía
          para el LLM.
        </Text>
        <Table.ScrollContainer minWidth={640}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Resultado</Table.Th>
                <Table.Th>Cuándo</Table.Th>
                <Table.Th>Mensaje de cierre</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {w.outcomes.map((o) => (
                <Table.Tr key={o.id}>
                  <Table.Td>
                    <OutcomeBadge label={o.label} goal={o.goal} />
                    {o.goal && (
                      <Badge variant="outline" color="green" size="xs" ml={6}>
                        objetivo
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{conditionLabel(o.when)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{o.message}</Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>
    </Stack>
  );
}
