import {
  Alert,
  Badge,
  Button,
  Code,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { useState } from 'react';
import type { App, AppLink } from '@/api/types';
import { EmptyState, QueryState } from '@/components/QueryState';
import { CopyIcon } from '@/components/Copy';
import { confirmAction } from '@/components/confirm';
import { useClients } from '@/features/clients/api';
import { formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { parseParams } from './params';
import { useAppLinks, useAssignApp, useCreateAppLink, useRevokeAppLink } from './api';

export function AssignAppModal({ app, onClose }: { app: App; onClose: () => void }) {
  const clients = useClients();
  const assign = useAssignApp();
  const [clientId, setClientId] = useState<string | null>(null);
  const submit = () => {
    if (!clientId) return;
    assign.mutate(
      { id: app.id, clientId },
      {
        onSuccess: (a) => {
          notifySuccess(`${a.name} asignada a ${a.client_name ?? 'el cliente'}.`);
          onClose();
        },
        onError: (e) => notifyError(e, 'No se pudo asignar'),
      },
    );
  };
  return (
    <Modal opened onClose={onClose} title={`Asignar ${app.name}`}>
      <Stack>
        <Text size="sm">
          Sus herramientas quedan disponibles para los agentes con motor asistente de ese cliente.
        </Text>
        <Select
          label="Cliente"
          placeholder="Elegí un cliente"
          data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
          value={clientId}
          onChange={setClientId}
          searchable
          data-autofocus
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={!clientId} loading={assign.isPending}>
            Asignar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/** Link a una vista: la URL se ve una sola vez (el token no se guarda). */
export function CreateLinkModal({ app, onClose }: { app: App; onClose: () => void }) {
  const create = useCreateAppLink();
  const [view, setView] = useState<string | null>(app.views?.[0]?.name ?? null);
  const [paramsText, setParamsText] = useState('');
  const [created, setCreated] = useState<AppLink | null>(null);
  const params = parseParams(paramsText);
  const selected = app.views?.find((v) => v.name === view);

  const submit = () => {
    if (!view || params === null) return;
    create.mutate(
      { id: app.id, body: { view, params } },
      {
        onSuccess: (l) => setCreated(l),
        onError: (e) => notifyError(e, 'No se pudo crear el link'),
      },
    );
  };

  return (
    <Modal opened onClose={onClose} title="Link a una vista" size="lg">
      {created?.url ? (
        <Stack>
          <Alert color="green" title="Link creado">
            Copialo ahora: por seguridad no se vuelve a mostrar. Vence el {formatDateTime(created.expires_at)}
            .
          </Alert>
          <Group gap="xs" wrap="nowrap" align="flex-start">
            <Code block style={{ flex: 1, wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
              {created.url}
            </Code>
            <CopyIcon value={created.url} label="Copiar link" />
          </Group>
          <Group justify="flex-end">
            <Button onClick={onClose}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          <Select
            label="Vista"
            data={(app.views ?? []).map((v) => ({ value: v.name, label: v.title }))}
            value={view}
            onChange={setView}
            allowDeselect={false}
            description={selected?.description || undefined}
          />
          <TextInput
            label="Parámetros"
            description="Opcional. Sin parámetros, la vista usa los suyos por defecto (por ejemplo, hoy)."
            placeholder="fecha=2026-10-12"
            value={paramsText}
            onChange={(e) => setParamsText(e.currentTarget.value)}
            error={params === null ? 'Escribilos como nombre=valor, separados por &.' : undefined}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button onClick={submit} disabled={!view || params === null} loading={create.isPending}>
              Crear link
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}

function linkState(l: AppLink, now = Date.now()) {
  if (l.revoked_at) return <Badge color="gray">Revocado</Badge>;
  if (new Date(l.expires_at).getTime() <= now) return <Badge color="gray">Vencido</Badge>;
  return <Badge color="green">Vigente</Badge>;
}

export function LinksModal({ app, onClose }: { app: App; onClose: () => void }) {
  const links = useAppLinks(app.id);
  const revoke = useRevokeAppLink();
  const doRevoke = async (l: AppLink) => {
    const ok = await confirmAction({
      title: 'Revocar link',
      message: `El link a ${l.view} deja de abrir, también para quien ya lo tiene abierto.`,
      confirmLabel: 'Revocar',
      danger: true,
    });
    if (ok)
      revoke.mutate(
        { id: app.id, linkId: l.id },
        {
          onSuccess: () => {
            notifySuccess('Link revocado.');
            void links.refetch();
          },
          onError: (e) => notifyError(e, 'No se pudo revocar'),
        },
      );
  };
  return (
    <Modal opened onClose={onClose} title={`Links de ${app.name}`} size="xl">
      <QueryState query={links}>
        {(list) =>
          list.length === 0 ? (
            <EmptyState>
              Todavía no hay links. Los crea el asistente o el botón "Link a una vista".
            </EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={720}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Vista</Table.Th>
                    <Table.Th>Creado por</Table.Th>
                    <Table.Th>Creado</Table.Th>
                    <Table.Th>Vence</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>Aperturas</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((l) => (
                    <Table.Tr key={l.id}>
                      <Table.Td className="mono">{l.view}</Table.Td>
                      <Table.Td className="mono">{l.created_by}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(l.created_at)}</Table.Td>
                      <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(l.expires_at)}</Table.Td>
                      <Table.Td className="mono" style={{ textAlign: 'right' }}>
                        {l.opens}
                      </Table.Td>
                      <Table.Td>{linkState(l)}</Table.Td>
                      <Table.Td>
                        {!l.revoked_at && (
                          <Button
                            size="compact-sm"
                            variant="subtle"
                            color="red"
                            onClick={() => void doRevoke(l)}
                          >
                            Revocar
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
    </Modal>
  );
}
