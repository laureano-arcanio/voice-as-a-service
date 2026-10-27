import { Accordion, Badge, Drawer, Group, Text } from '@mantine/core';
import { QueryState } from '@/components/QueryState';
import { CLIENT_TOOL_TYPE } from '@/lib/labels';
import { formatDateTime } from '@/lib/format';
import { useToolVersions } from './api';

/** Historial de una herramienta (solo lectura): cada revision con su fecha y su definicion. La traza de una
 * llamada dice con que revision corrio. */
export function ToolHistory({
  clientId,
  slug,
  current,
  opened,
  onClose,
}: {
  clientId: string;
  slug: string;
  /** Revision vigente, para marcarla. */
  current: number;
  opened: boolean;
  onClose: () => void;
}) {
  const versions = useToolVersions(clientId, slug, opened);
  return (
    <Drawer opened={opened} onClose={onClose} position="right" size="lg" title={`Historial de ${slug}`}>
      <Text size="xs" c="dimmed" mb="sm">
        Cada vez que se guarda un cambio queda una revisión nueva. La traza de cada llamada dice con cuál
        corrió.
      </Text>
      <QueryState query={versions}>
        {(list) =>
          list.length === 0 ? (
            <Text size="sm" c="dimmed">
              Todavía no hay revisiones guardadas.
            </Text>
          ) : (
            <Accordion variant="separated" defaultValue={String(list[0]?.revision ?? '')}>
              {list.map((v) => (
                <Accordion.Item key={v.revision} value={String(v.revision)}>
                  <Accordion.Control>
                    <Group gap="xs" wrap="wrap">
                      <Text span fw={600} className="mono">
                        rev. {v.revision}
                      </Text>
                      <Text span size="sm" c="dimmed">
                        {formatDateTime(v.created_at)}
                      </Text>
                      <Badge color="gray">{CLIENT_TOOL_TYPE[v.type] ?? v.type}</Badge>
                      {v.revision === current && <Badge color="green">Vigente</Badge>}
                    </Group>
                  </Accordion.Control>
                  <Accordion.Panel>
                    <pre className="code" style={{ margin: 0, maxHeight: 420, overflow: 'auto' }}>
                      {JSON.stringify(v.definition, null, 2)}
                    </pre>
                  </Accordion.Panel>
                </Accordion.Item>
              ))}
            </Accordion>
          )
        }
      </QueryState>
    </Drawer>
  );
}
