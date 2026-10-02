import { Badge, Group, Radio, SimpleGrid, Stack, Text } from '@mantine/core';
import { ENGINE } from '@/lib/labels';
import { ENGINE_HELP } from './draft';

/** Rotulo del motor: solo lo ve un admin, en pantallas que comparte con el cliente. */
export function EngineLabel() {
  return (
    <Group gap="xs" component="span" display="inline-flex">
      Motor
      <Badge color="gray" size="sm">
        interno
      </Badge>
    </Group>
  );
}

/** Opciones de motor como tarjetas; van dentro de un Radio.Group. */
export function EngineCards() {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs" mt="xs">
      {(['classic', 'structured'] as const).map((e) => (
        <Radio.Card key={e} value={e} p="sm">
          <Group wrap="nowrap" align="flex-start" gap="sm">
            <Radio.Indicator />
            <Stack gap={2} style={{ minWidth: 0 }}>
              <Text size="sm" fw={600}>
                {ENGINE[e] ?? e}
              </Text>
              <Text size="xs" c="dimmed">
                {ENGINE_HELP[e]}
              </Text>
            </Stack>
          </Group>
        </Radio.Card>
      ))}
    </SimpleGrid>
  );
}
