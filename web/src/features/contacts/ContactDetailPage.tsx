import { Anchor, Badge, Button, Card, Group, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { IconArchive, IconArchiveOff, IconArrowLeft, IconPencil } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { ApiError } from '@/api/errors';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState, ErrorAlert, QueryState } from '@/components/QueryState';
import { CHANNEL, CONTACT_RESULT, CONTACT_STATUS, statusLabel } from '@/features/campaigns/labels';
import { formatDate, formatDateTime } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useArchiveContact, useContact, useContactCampaigns } from './api';
import { ContactModal } from './ContactModals';
import { TagBadges } from './TagBadges';
import { CONTACT_SOURCE } from './labels';

function Datum({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm" fw={600} component="div">
        {children}
      </Text>
    </Stack>
  );
}

function CampaignsCard({ id }: { id: string }) {
  const campaigns = useContactCampaigns(id);
  return (
    <Card>
      <Title order={4} mb="md">
        Campañas
      </Title>
      <QueryState query={campaigns}>
        {(rows) =>
          rows.length === 0 ? (
            <EmptyState>Todavía no está en ninguna campaña.</EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={720}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Campaña</Table.Th>
                    <Table.Th>Canal</Table.Th>
                    <Table.Th>Estado</Table.Th>
                    <Table.Th>Resultado</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>Intentos</Table.Th>
                    <Table.Th>Último intento</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((r) => {
                    const st = statusLabel({ status: r.campaign_status, channel: r.channel });
                    const res = r.result ? CONTACT_RESULT[r.result] : null;
                    const cs = CONTACT_STATUS[r.status];
                    const when = r.last_attempt_at ?? r.sent_at;
                    return (
                      <Table.Tr key={r.campaign_id}>
                        <Table.Td>
                          <Anchor component={Link} to={`/campaigns/${r.campaign_id}`} size="sm" fw={600}>
                            {r.campaign_name}
                          </Anchor>
                        </Table.Td>
                        <Table.Td>{CHANNEL[r.channel]}</Table.Td>
                        <Table.Td>
                          <Badge color={st.color}>{st.label}</Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={(res ?? cs)?.color ?? 'gray'}>{(res ?? cs)?.label ?? r.status}</Badge>
                        </Table.Td>
                        <Table.Td className="mono" ta="right">
                          {r.channel === 'voice' ? r.attempts : <Dash />}
                        </Table.Td>
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>
                          {when ? formatDateTime(when) : <Dash />}
                        </Table.Td>
                        <Table.Td>
                          {r.conversation_id && (
                            <Anchor component={Link} to={`/calls/${r.conversation_id}`} size="sm">
                              Ver conversación
                            </Anchor>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
    </Card>
  );
}

/** La ficha de un contacto: sus datos y las campañas en las que estuvo. */
export function ContactDetailPage() {
  const { id = '' } = useParams();
  const query = useContact(id);
  const archive = useArchiveContact();
  const [editing, setEditing] = useState(false);

  const back = (
    <Button
      component={Link}
      to="/contacts"
      variant="subtle"
      size="compact-sm"
      leftSection={<IconArrowLeft size={16} />}
      w="fit-content"
    >
      Contactos
    </Button>
  );

  if (query.isError) {
    const gone = query.error instanceof ApiError && query.error.status === 404;
    return (
      <>
        <PageHeader title="Contacto" above={back} />
        <ErrorAlert error={gone ? new Error('El contacto no existe o no tenés acceso.') : query.error} />
      </>
    );
  }

  return (
    <QueryState query={query}>
      {(c) => {
        const toggle = async () => {
          if (!c.archived_at) {
            const ok = await confirmAction({
              title: `Archivar a ${c.name || c.phone}`,
              message:
                'No se borra: queda en el historial y los reportes. No entra en campañas nuevas, y sus llamadas o mensajes pendientes en campañas en curso se saltean.',
              confirmLabel: 'Archivar',
              danger: true,
            });
            if (!ok) return;
          }
          archive.mutate(
            { id: c.id, archive: !c.archived_at },
            {
              onSuccess: () =>
                notifySuccess(c.archived_at ? 'Contacto activo de nuevo.' : 'Contacto archivado.'),
              onError: (e) => notifyError(e),
            },
          );
        };
        return (
          <Stack gap="md">
            <PageHeader
              above={back}
              docTitle={c.name || c.phone}
              title={
                <Group gap="sm" component="span">
                  {c.name || <span className="mono">{c.phone}</span>}
                  {c.archived_at && <Badge color="gray">Archivado</Badge>}
                </Group>
              }
              description={c.name ? <span className="mono">{c.phone}</span> : undefined}
              actions={
                <>
                  <Button
                    variant="default"
                    leftSection={<IconPencil size={18} />}
                    onClick={() => setEditing(true)}
                  >
                    Editar
                  </Button>
                  <Button
                    variant={c.archived_at ? 'default' : 'subtle'}
                    color={c.archived_at ? undefined : 'red'}
                    leftSection={c.archived_at ? <IconArchiveOff size={18} /> : <IconArchive size={18} />}
                    loading={archive.isPending}
                    onClick={() => void toggle()}
                  >
                    {c.archived_at ? 'Desarchivar' : 'Archivar'}
                  </Button>
                </>
              }
            />
            <Card>
              <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }} spacing="md">
                <Datum label="Email">{c.email ?? <Dash />}</Datum>
                <Datum label="ID externo">
                  {c.external_id ? <span className="mono">{c.external_id}</span> : <Dash />}
                </Datum>
                <Datum label="Origen">{CONTACT_SOURCE[c.source] ?? c.source}</Datum>
                <Datum label="Alta">{formatDate(c.created_at)}</Datum>
                <Datum label="Etiquetas">
                  <TagBadges tags={c.tags} max={8} />
                </Datum>
              </SimpleGrid>
              {Object.keys(c.attributes).length > 0 && (
                <>
                  <Text className="label" mt="lg" mb={6}>
                    Datos
                  </Text>
                  <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }} spacing="md">
                    {Object.entries(c.attributes).map(([k, v]) => (
                      <Datum key={k} label={k}>
                        <span className="mono">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                      </Datum>
                    ))}
                  </SimpleGrid>
                </>
              )}
            </Card>
            <CampaignsCard id={c.id} />
            {editing && <ContactModal contact={c} onClose={() => setEditing(false)} />}
          </Stack>
        );
      }}
    </QueryState>
  );
}
