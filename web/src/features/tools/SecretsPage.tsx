import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Select,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconKey, IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { ClientSecret, Credential } from '@/api/types';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useIsAdmin } from '@/features/auth/api';
import { useClients } from '@/features/clients/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import {
  toolsHref,
  useClientSecrets,
  useCredentials,
  useDeleteClientSecret,
  useDeleteCredential,
  useToolsClient,
} from './api';
import { CredentialModal } from './CredentialModal';
import { CREDENTIAL_TYPE_LABEL } from './credentials';
import { type SecretDialog, SecretModal } from './SecretModal';

/** Links a las herramientas, separados por coma. */
function ToolLinks({ slugs, href }: { slugs: string[]; href: (p: string) => string }) {
  if (!slugs.length) return <Dash />;
  return (
    <Text size="sm">
      {slugs.map((t, i) => (
        <span key={t}>
          {i > 0 && ', '}
          <Anchor component={Link} to={href(`/tools/${t}`)} className="mono" inherit>
            {t}
          </Anchor>
        </span>
      ))}
    </Text>
  );
}

function CredentialsCard({ clientId, href }: { clientId: string; href: (p: string) => string }) {
  const credentials = useCredentials(clientId);
  const remove = useDeleteCredential(clientId);
  const [modal, setModal] = useState<{ edit?: Credential } | null>(null);

  const del = async (c: Credential) => {
    const ok = await confirmAction({
      title: `¿Borrar la credencial ${c.name}?`,
      message: c.used_by.length
        ? `La usan ${c.used_by.join(', ')}: cambiá su autenticación antes.`
        : `El secreto ${c.secret} con el valor queda en la lista de abajo.`,
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      remove.mutate(c.slug, {
        onSuccess: () => notifySuccess('Credencial borrada.'),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  return (
    <Card>
      <Group justify="space-between" gap="sm" mb="sm">
        <div>
          <Title order={4}>Credenciales</Title>
          <Text size="xs" c="dimmed">
            Cómo se identifica Atentina ante cada API tuya: token, API key, usuario y clave u OAuth2. Se elige
            en la pestaña Autenticación de cada herramienta.
          </Text>
        </div>
        <Button variant="default" leftSection={<IconPlus size={16} />} onClick={() => setModal({})}>
          Nueva credencial
        </Button>
      </Group>
      <QueryState query={credentials}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>
              Todavía no hay credenciales. Creá una por cada API a la que llaman tus herramientas.
            </EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={680}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Credencial</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Valor en el secreto</Table.Th>
                    <Table.Th>Herramientas</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td>
                        <Text size="sm" fw={600}>
                          {c.name}
                        </Text>
                        <Text size="xs" c="dimmed" className="mono">
                          {c.slug}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge color="gray">{CREDENTIAL_TYPE_LABEL[c.type] ?? c.type}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={6} wrap="nowrap">
                          <Text span size="sm" className="mono">
                            {c.secret}
                          </Text>
                          {!c.secret_set && <Badge color="yellow">Falta</Badge>}
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <ToolLinks slugs={c.used_by} href={href} />
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4} justify="flex-end" wrap="nowrap">
                          <Tooltip label="Editar" withArrow>
                            <ActionIcon
                              variant="subtle"
                              color="gray"
                              aria-label={`Editar ${c.name}`}
                              onClick={() => setModal({ edit: c })}
                            >
                              <IconPencil size={16} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Borrar" withArrow>
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              aria-label={`Borrar ${c.name}`}
                              onClick={() => void del(c)}
                            >
                              <IconTrash size={16} />
                            </ActionIcon>
                          </Tooltip>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      {modal && (
        <CredentialModal clientId={clientId} credential={modal.edit} onClose={() => setModal(null)} />
      )}
    </Card>
  );
}

function ClientSecretsCard({ clientId, href }: { clientId: string; href: (p: string) => string }) {
  const secrets = useClientSecrets(clientId);
  const remove = useDeleteClientSecret(clientId);
  const [dialog, setDialog] = useState<SecretDialog | null>(null);

  const del = async (s: ClientSecret) => {
    const ok = await confirmAction({
      title: `¿Borrar el secreto ${s.name}?`,
      message: 'Se borra el valor. Los agentes que no tienen uno propio dejan de poder usarlo.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      remove.mutate(s.name, {
        onSuccess: () => notifySuccess('Secreto borrado.'),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  return (
    <Card>
      <Group justify="space-between" gap="sm" mb="sm">
        <div>
          <Title order={4}>Secretos</Title>
          <Text size="xs" c="dimmed">
            Tokens y claves que usan las herramientas, para todos los agentes. Se guardan cifrados, no se
            vuelven a mostrar y el agente nunca los ve. Si un agente necesita otro valor, se lo cargás en el
            agente.
          </Text>
        </div>
        <Button
          variant="default"
          leftSection={<IconPlus size={16} />}
          onClick={() => setDialog({ scope: 'client' })}
        >
          Nuevo secreto
        </Button>
      </Group>
      <QueryState query={secrets}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>
              Todavía no hay secretos. Se crean solos al crear una credencial, o cargá uno para usarlo como{' '}
              {'{{secrets.NOMBRE}}'} en una herramienta.
            </EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={760}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Nombre</Table.Th>
                    <Table.Th>Valor</Table.Th>
                    <Table.Th>Descripción</Table.Th>
                    <Table.Th>Lo usan</Table.Th>
                    <Table.Th>Agentes con otro valor</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((s) => (
                    <Table.Tr key={s.name}>
                      <Table.Td className="mono">{s.name}</Table.Td>
                      <Table.Td>
                        {s.missing ? (
                          <Badge color="yellow">Falta</Badge>
                        ) : s.last4 ? (
                          <Text span className="mono" size="sm">
                            ••••{s.last4}
                          </Text>
                        ) : (
                          <Badge color="green">Cargado</Badge>
                        )}
                      </Table.Td>
                      <Table.Td>{s.description ? <Text size="sm">{s.description}</Text> : <Dash />}</Table.Td>
                      <Table.Td>
                        {s.used_by.length || s.credentials.length ? (
                          <Stack gap={0}>
                            {s.used_by.length > 0 && <ToolLinks slugs={s.used_by} href={href} />}
                            {s.credentials.length > 0 && (
                              <Text size="xs" c="dimmed">
                                Credencial {s.credentials.join(', ')}
                              </Text>
                            )}
                          </Stack>
                        ) : (
                          <Dash />
                        )}
                      </Table.Td>
                      <Table.Td>
                        {s.agents.length ? (
                          <Text size="sm">
                            {s.agents.map((a, i) => (
                              <span key={a.id}>
                                {i > 0 && ', '}
                                <Anchor component={Link} to={`/agents/${a.id}`} inherit>
                                  {a.name}
                                </Anchor>
                              </span>
                            ))}
                          </Text>
                        ) : (
                          <Dash />
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4} justify="flex-end" wrap="nowrap">
                          {s.missing ? (
                            <Button
                              size="compact-sm"
                              variant="subtle"
                              leftSection={<IconKey size={16} />}
                              onClick={() => setDialog({ name: s.name, scope: 'client' })}
                            >
                              Cargar valor
                            </Button>
                          ) : (
                            <>
                              <Button
                                size="compact-sm"
                                variant="subtle"
                                onClick={() =>
                                  setDialog({
                                    name: s.name,
                                    scope: 'client',
                                    replace: { description: s.description },
                                  })
                                }
                              >
                                Reemplazar valor
                              </Button>
                              <Tooltip label="Borrar" withArrow>
                                <ActionIcon
                                  variant="subtle"
                                  color="red"
                                  aria-label={`Borrar ${s.name}`}
                                  onClick={() => void del(s)}
                                >
                                  <IconTrash size={16} />
                                </ActionIcon>
                              </Tooltip>
                            </>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      {dialog && <SecretModal clientId={clientId} dialog={dialog} onClose={() => setDialog(null)} />}
    </Card>
  );
}

/** Credenciales y secretos del cliente: lo que usan las herramientas para entrar a sus APIs. */
export function SecretsPage() {
  const isAdmin = useIsAdmin();
  const clientId = useToolsClient();
  const [, setParams] = useSearchParams();
  const clients = useClients(isAdmin);
  const href = (path: string) => toolsHref(path, clientId, isAdmin);

  const setClient = (v: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (v) next.set('client', v);
        else next.delete('client');
        return next;
      },
      { replace: true },
    );

  return (
    <Stack gap="md">
      <PageHeader
        title="Secretos"
        description="Las credenciales y los tokens con los que tus herramientas entran a tus sistemas. Se cargan una vez y los usan todos los agentes."
      />
      {isAdmin && (
        <Group>
          <Select
            label="Cliente"
            placeholder="Elegí un cliente"
            data={(clients.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            value={clientId ?? null}
            onChange={setClient}
            clearable
            searchable
            w={260}
          />
        </Group>
      )}
      <PlanGate feature="custom_tools" what="herramientas para tus agentes">
        {!clientId ? (
          <Card>
            <EmptyState>Elegí un cliente para ver sus secretos.</EmptyState>
          </Card>
        ) : (
          <Stack gap="md">
            <CredentialsCard clientId={clientId} href={href} />
            <ClientSecretsCard clientId={clientId} href={href} />
          </Stack>
        )}
      </PlanGate>
    </Stack>
  );
}
