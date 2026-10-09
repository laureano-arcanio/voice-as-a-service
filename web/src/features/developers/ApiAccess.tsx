import { Card, Code, Group, Stack, Table, Tabs, Text, Title } from '@mantine/core';
import { CopyIcon } from '@/components/Copy';
import { ApiKeysSection } from '@/features/clients/ApiKeysSection';
import { InferenceUsageCard } from './InferenceUsageCard';
import { ENDPOINTS, EXAMPLE_LABELS, inferenceBaseUrl, inferenceExample, type ExampleKind } from './examples';

const KINDS: ExampleKind[] = ['llm', 'stt', 'tts', 'python'];

function CodeBlock({ code }: { code: string }) {
  return (
    <Group gap="xs" wrap="nowrap" align="flex-start">
      <Code block style={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
        {code}
      </Code>
      <CopyIcon value={code} label="Copiar ejemplo" />
    </Group>
  );
}

function ConnectionCard() {
  const base = inferenceBaseUrl(location.origin);
  return (
    <Card>
      <Title order={4} mb={4}>
        Conexión
      </Title>
      <Text size="sm" c="dimmed" mb="sm">
        LLM, transcripción y síntesis de voz propios, con una API key. Es compatible con el SDK de OpenAI:
        apuntalo a esta URL.
      </Text>
      <Stack gap="xs" mb="md">
        <Group gap="xs" wrap="nowrap">
          <Text size="sm" w={110} fw={600}>
            URL base
          </Text>
          <Code style={{ wordBreak: 'break-all' }}>{base}</Code>
          <CopyIcon value={base} label="Copiar URL" />
        </Group>
        <Group gap="xs" wrap="nowrap">
          <Text size="sm" w={110} fw={600}>
            Autenticación
          </Text>
          <Code>Authorization: Bearer &lt;tu API key&gt;</Code>
        </Group>
      </Stack>
      <Table.ScrollContainer minWidth={560}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Endpoint</Table.Th>
              <Table.Th>Alcance de la key</Table.Th>
              <Table.Th>Qué hace</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {ENDPOINTS.map((e) => (
              <Table.Tr key={e.path}>
                <Table.Td className="mono" style={{ whiteSpace: 'nowrap' }}>
                  {e.method} {e.path}
                </Table.Td>
                <Table.Td>{e.scope === 'cualquiera' ? 'cualquiera de inferencia' : e.scope}</Table.Td>
                <Table.Td>{e.description}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      <Text size="xs" c="dimmed" mt="sm">
        Los límites del plan (tokens, minutos y pedidos por minuto) cuentan solo el uso por API; al agotarlos,
        la API responde 429 con el motivo en <Code>code</Code>.
      </Text>
    </Card>
  );
}

function ExamplesCard() {
  return (
    <Card>
      <Title order={4} mb="sm">
        Ejemplos
      </Title>
      <Tabs defaultValue="llm" keepMounted={false}>
        <Tabs.List mb="sm">
          {KINDS.map((k) => (
            <Tabs.Tab key={k} value={k}>
              {EXAMPLE_LABELS[k]}
            </Tabs.Tab>
          ))}
        </Tabs.List>
        {KINDS.map((k) => (
          <Tabs.Panel key={k} value={k}>
            <CodeBlock code={inferenceExample(k, location.origin)} />
          </Tabs.Panel>
        ))}
      </Tabs>
    </Card>
  );
}

/** API de inferencia de un cliente: conexion y ejemplos, consumo contra el plan y API keys con su alcance. */
export function ApiAccess({ clientId }: { clientId: string }) {
  return (
    <Stack gap="md">
      <InferenceUsageCard clientId={clientId} />
      <ApiKeysSection clientId={clientId} />
      <ConnectionCard />
      <ExamplesCard />
    </Stack>
  );
}
