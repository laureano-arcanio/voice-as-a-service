import { Anchor, Badge, Button, Card, Code, Group, Modal, Stack, Table, Text, Title } from '@mantine/core';
import { useState } from 'react';
import type { LegalDocument, LegalVersion } from '@/api/types';
import { CopyIcon } from '@/components/Copy';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useLegalVersion, useLegalVersions } from './api';

/** 2026-10-01 → 1/10/2026, sin pasar por Date (la medianoche UTC cae el día anterior en Argentina). */
function versionDate(version: string): string {
  const [y, m, d] = version.split('-');
  return `${Number(d)}/${Number(m)}/${y}`;
}

// Las condiciones y la política de privacidad con versión (docs/features/LEGAL.md). La landing solo muestra la
// vigente; las anteriores se abren por el link de los mails de aceptación o desde acá.
export function LegalPage() {
  const versions = useLegalVersions();
  const [open, setOpen] = useState<{ document: LegalDocument; version: string } | null>(null);
  return (
    <>
      <PageHeader
        title="Legales"
        description="Cada versión publicada de las condiciones y de la política de privacidad, con su texto exacto, su huella y cuántas aceptaciones tiene."
      />
      <QueryState query={versions}>
        {(list) =>
          list.length === 0 ? (
            <Card>
              <EmptyState>No hay versiones publicadas.</EmptyState>
            </Card>
          ) : (
            <Stack>
              {(['terms', 'privacy'] as const).map((doc) => {
                const rows = list.filter((v) => v.document === doc);
                return rows.length === 0 ? null : (
                  <Card key={doc}>
                    <Title order={4} mb="sm">
                      {rows[0].title}
                    </Title>
                    <VersionsTable rows={rows} onOpen={(v) => setOpen(v)} />
                  </Card>
                );
              })}
            </Stack>
          )
        }
      </QueryState>
      <VersionModal
        document={open?.document ?? 'terms'}
        version={open?.version ?? null}
        onClose={() => setOpen(null)}
      />
    </>
  );
}

function VersionsTable({
  rows,
  onOpen,
}: {
  rows: LegalVersion[];
  onOpen: (v: { document: LegalDocument; version: string }) => void;
}) {
  return (
    <Table.ScrollContainer minWidth={720}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Versión</Table.Th>
            <Table.Th>Publicada</Table.Th>
            <Table.Th ta="right">Aceptaciones</Table.Th>
            <Table.Th>Huella SHA-256</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((v) => (
            <Table.Tr key={v.version}>
              <Table.Td>
                <Group gap={6} wrap="nowrap">
                  <Text size="sm" className="mono">
                    {v.version}
                  </Text>
                  {v.current && <Badge color="green">Vigente</Badge>}
                </Group>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{versionDate(v.version)}</Text>
              </Table.Td>
              <Table.Td ta="right">{v.acceptances}</Table.Td>
              <Table.Td>
                <Group gap={4} wrap="nowrap">
                  <Text size="xs" className="mono" c="dimmed">
                    {v.sha256.slice(0, 16)}…
                  </Text>
                  <CopyIcon value={v.sha256} label="Copiar huella" />
                </Group>
              </Table.Td>
              <Table.Td ta="right">
                <Button
                  size="xs"
                  variant="light"
                  onClick={() => onOpen({ document: v.document, version: v.version })}
                >
                  Ver texto
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function VersionModal({
  document,
  version,
  onClose,
}: {
  document: LegalDocument;
  version: string | null;
  onClose: () => void;
}) {
  const detail = useLegalVersion(document, version);
  return (
    <Modal opened={version != null} onClose={onClose} title={`Versión ${version ?? ''}`} size="xl">
      <QueryState query={detail}>
        {(v) => (
          <Stack gap="sm">
            <Group justify="space-between" gap="xs">
              <Text fw={600}>{v.title}</Text>
              <Group gap={6}>
                {v.current && <Badge color="green">Vigente</Badge>}
                <Badge variant="light">{v.acceptances} aceptaciones</Badge>
              </Group>
            </Group>
            <Group gap={4} wrap="nowrap">
              <Anchor href={v.url} target="_blank" rel="noreferrer" size="sm">
                {v.url}
              </Anchor>
              <CopyIcon value={v.url} label="Copiar link" />
            </Group>
            <Text size="xs" c="dimmed" className="mono" style={{ wordBreak: 'break-all' }}>
              SHA-256 {v.sha256}
            </Text>
            <Code block style={{ whiteSpace: 'pre-wrap', maxHeight: '60vh', overflow: 'auto' }}>
              {v.text}
            </Code>
          </Stack>
        )}
      </QueryState>
    </Modal>
  );
}
