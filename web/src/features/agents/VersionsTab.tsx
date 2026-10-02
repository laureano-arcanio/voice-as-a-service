import { Badge, Button, Card, Group, Modal, SegmentedControl, Stack, Table, Text } from '@mantine/core';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { AgentDetail } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { JsonEditor } from '@/components/JsonEditor';
import { QueryState } from '@/components/QueryState';
import { diffLines, withContext } from '@/lib/diff';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { agentKeys, fetchAgentVersion, useAgentVersion, useAgentVersions, useSaveDefinition } from './api';
import { toJsonText } from './definition';

/** JSON sin `version` (siempre cambia; no aporta al diff). */
function withoutVersion(d: Record<string, unknown>): string {
  const { version: _version, ...rest } = d;
  return toJsonText(rest);
}

function DiffView({ from, to }: { from: string; to: string }) {
  const lines = withContext(diffLines(from, to));
  if (!lines.some((l) => l && l.op !== 'same')) {
    return (
      <Text size="sm" c="dimmed">
        Sin diferencias.
      </Text>
    );
  }
  return (
    <pre className="code" style={{ maxHeight: 520 }}>
      {lines.map((l, i) =>
        l === null ? (
          <span key={i} className="diff-line diff-gap">
            ⋯
          </span>
        ) : (
          <span
            key={i}
            className={`diff-line${l.op === 'add' ? ' diff-add' : l.op === 'del' ? ' diff-del' : ''}`}
          >
            {l.op === 'add' ? '+ ' : l.op === 'del' ? '- ' : '  '}
            {l.text}
          </span>
        ),
      )}
    </pre>
  );
}

function VersionModal({
  agent,
  version,
  onClose,
}: {
  agent: AgentDetail;
  version: number | null;
  onClose: () => void;
}) {
  const query = useAgentVersion(agent.id, version);
  const [view, setView] = useState<'json' | 'diff'>('json');
  return (
    <Modal opened={version != null} onClose={onClose} title={`Versión ${version ?? ''}`} size="xl">
      <QueryState query={query}>
        {(v) => {
          const text = toJsonText(v.definition ?? {});
          return (
            <Stack gap="sm">
              <SegmentedControl
                value={view}
                onChange={(x) => setView(x as 'json' | 'diff')}
                data={[
                  { value: 'json', label: 'JSON' },
                  { value: 'diff', label: `Cambios hacia la vigente (v${agent.version})` },
                ]}
                disabled={v.version === agent.version}
              />
              {view === 'json' || v.version === agent.version ? (
                <JsonEditor value={text} readOnly height="480px" />
              ) : (
                <DiffView from={withoutVersion(v.definition ?? {})} to={withoutVersion(agent.definition)} />
              )}
            </Stack>
          );
        }}
      </QueryState>
    </Modal>
  );
}

export function VersionsTab({ agent, canEdit }: { agent: AgentDetail; canEdit: boolean }) {
  const versions = useAgentVersions(agent.id);
  const save = useSaveDefinition(agent.id);
  const [viewing, setViewing] = useState<number | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);
  const qc = useQueryClient();

  const restore = async (version: number) => {
    const ok = await confirmAction({
      title: `Restaurar la versión ${version}`,
      message: `Se guarda la definición de la v${version} como versión nueva (v${agent.version + 1}). La historia no se pierde.`,
      confirmLabel: 'Restaurar',
    });
    if (!ok) return;
    setRestoring(version);
    try {
      const v = await qc.fetchQuery({
        queryKey: agentKeys.version(agent.id, version),
        queryFn: () => fetchAgentVersion(agent.id, version),
        staleTime: Infinity,
      });
      const saved = await save.mutateAsync(v.definition ?? {});
      if (saved.version === agent.version) notifySuccess('Esa versión es igual a la vigente.', 'Sin cambios');
      else notifySuccess(`Versión ${saved.version} guardada (restaurada de la v${version}).`);
    } catch (e) {
      notifyError(e, 'No se pudo restaurar');
    } finally {
      setRestoring(null);
    }
  };

  return (
    <Card>
      <QueryState query={versions}>
        {(list) => (
          <Table.ScrollContainer minWidth={520}>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Versión</Table.Th>
                  <Table.Th>Fecha</Table.Th>
                  <Table.Th>Autor</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {list.map((v) => (
                  <Table.Tr key={v.version}>
                    <Table.Td>
                      <Group gap={6}>
                        <Text fw={600} className="mono">
                          v{v.version}
                        </Text>
                        {v.version === agent.version && <Badge color="green">vigente</Badge>}
                      </Group>
                    </Table.Td>
                    <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(v.created_at)}</Table.Td>
                    <Table.Td>{v.created_by_email ?? (v.created_by ? 'Usuario borrado' : '–')}</Table.Td>
                    <Table.Td>
                      <Group gap="xs" justify="flex-end">
                        <Button size="compact-sm" variant="subtle" onClick={() => setViewing(v.version)}>
                          Ver
                        </Button>
                        {canEdit && v.version !== agent.version && (
                          <Button
                            size="compact-sm"
                            variant="subtle"
                            onClick={() => void restore(v.version)}
                            loading={restoring === v.version}
                            disabled={restoring != null && restoring !== v.version}
                          >
                            Restaurar
                          </Button>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </QueryState>
      <VersionModal agent={agent} version={viewing} onClose={() => setViewing(null)} />
    </Card>
  );
}
