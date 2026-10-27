import { ActionIcon, Badge, Button, Card, Group, Stack, Table, Text, Title, Tooltip } from '@mantine/core';
import { IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import type { TeamMember } from '@/api/types';
import { Dash } from '@/components/Badges';
import { confirmAction } from '@/components/confirm';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { EmptyState, QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { type AreaRow, useAreas, useDeleteArea, useDeleteMember, useTeam } from './api';
import { AreaModal } from './AreaModal';
import { areaStatus } from './labels';
import { MemberModal } from './MemberModal';
import { scheduleLabel } from './schedule';

type Dialog = { kind: 'member'; member: TeamMember | null } | { kind: 'area'; area: AreaRow | null } | null;

/** Equipo del cliente y areas de derivacion: a quien pasa el agente una llamada o un chat. */
export function TeamPage() {
  const team = useTeam();
  const areas = useAreas();
  const deleteMember = useDeleteMember();
  const deleteArea = useDeleteArea();
  const [dialog, setDialog] = useState<Dialog>(null);

  const members = team.data ?? [];

  const removeMember = async (m: TeamMember) => {
    const inAreas = (areas.data ?? []).filter((a) => a.member_ids.includes(m.id)).map((a) => a.name);
    const ok = await confirmAction({
      title: `¿Borrar a ${m.name}?`,
      message: inAreas.length
        ? `Sale ${inAreas.length === 1 ? 'del área' : 'de las áreas'} ${inAreas.join(', ')} y no recibe más derivaciones. El historial se conserva.`
        : 'No recibe más derivaciones. El historial se conserva.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      deleteMember.mutate(m.id, {
        onSuccess: () => notifySuccess(`${m.name} salió del equipo.`),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  const removeArea = async (a: AreaRow) => {
    const ok = await confirmAction({
      title: `¿Borrar el área ${a.name}?`,
      message: 'El agente ya no puede derivar a esta área. Las personas siguen en el equipo.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok)
      deleteArea.mutate(a.id, {
        onSuccess: () => notifySuccess('Área borrada.'),
        onError: (e) => notifyError(e, 'No se pudo borrar'),
      });
  };

  const addButton = (label: string, onClick: () => void, primary = false) => (
    <Button variant={primary ? 'filled' : 'default'} leftSection={<IconPlus size={18} />} onClick={onClick}>
      {label}
    </Button>
  );

  return (
    <Stack gap="md">
      <PageHeader
        title="Equipo"
        description="Las personas a las que el agente les pasa una llamada o un chat, agrupadas en áreas con su horario."
      />

      <PlanGate feature="team" what="el equipo para derivar llamadas y chats">
        <Stack gap="md">
          <Card>
            <Group justify="space-between" mb="sm" gap="sm">
              <Title order={4}>Personas</Title>
              {addButton('Agregar persona', () => setDialog({ kind: 'member', member: null }))}
            </Group>
            <QueryState query={team}>
              {(rows) =>
                rows.length === 0 ? (
                  <EmptyState>
                    Todavía no hay personas en el equipo. Agregá a quienes atienden las derivaciones, con su
                    teléfono para pasarles llamadas o su WhatsApp para pasarles chats.
                  </EmptyState>
                ) : (
                  <Table.ScrollContainer minWidth={580}>
                    <Table>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Nombre</Table.Th>
                          <Table.Th>Teléfono</Table.Th>
                          <Table.Th>WhatsApp</Table.Th>
                          <Table.Th>Estado</Table.Th>
                          <Table.Th />
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {rows.map((m) => (
                          <Table.Tr key={m.id}>
                            <Table.Td fw={600}>{m.name}</Table.Td>
                            <Table.Td className="mono" style={{ whiteSpace: 'nowrap' }}>
                              {m.phone ?? <Dash />}
                            </Table.Td>
                            <Table.Td className="mono" style={{ whiteSpace: 'nowrap' }}>
                              {m.whatsapp ?? <Dash />}
                            </Table.Td>
                            <Table.Td>
                              <Badge color={m.active ? 'green' : 'gray'}>
                                {m.active ? 'Activa' : 'Inactiva'}
                              </Badge>
                            </Table.Td>
                            <Table.Td>
                              <Group gap={4} justify="flex-end" wrap="nowrap">
                                <Tooltip label="Editar" withArrow>
                                  <ActionIcon
                                    variant="subtle"
                                    color="gray"
                                    aria-label={`Editar a ${m.name}`}
                                    onClick={() => setDialog({ kind: 'member', member: m })}
                                  >
                                    <IconPencil size={16} />
                                  </ActionIcon>
                                </Tooltip>
                                <Tooltip label="Borrar" withArrow>
                                  <ActionIcon
                                    variant="subtle"
                                    color="red"
                                    aria-label={`Borrar a ${m.name}`}
                                    onClick={() => void removeMember(m)}
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
          </Card>

          <Card>
            <Group justify="space-between" mb="sm" gap="sm">
              <Title order={4}>Áreas</Title>
              {addButton('Crear área', () => setDialog({ kind: 'area', area: null }), true)}
            </Group>
            <Text size="sm" c="dimmed" mb="sm">
              El agente elige el área por lo que atiende y llama a sus personas en orden, dentro de su
              horario. Si nadie atiende, toma el mensaje.
            </Text>
            <QueryState query={areas}>
              {(rows) =>
                rows.length === 0 ? (
                  <EmptyState>
                    Todavía no hay áreas. Creá una (por ejemplo, Ventas) con las personas que la atienden y su
                    horario.
                  </EmptyState>
                ) : (
                  <Table.ScrollContainer minWidth={720}>
                    <Table>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Área</Table.Th>
                          <Table.Th>Personas</Table.Th>
                          <Table.Th>Horario</Table.Th>
                          <Table.Th>Estado</Table.Th>
                          <Table.Th />
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {rows.map((a) => {
                          const status = areaStatus(a);
                          const names = a.member_ids
                            .map((id) => members.find((m) => m.id === id)?.name)
                            .filter(Boolean);
                          return (
                            <Table.Tr key={a.id}>
                              <Table.Td>
                                <Text size="sm" fw={600}>
                                  {a.name}
                                </Text>
                                {a.description && (
                                  <Text size="xs" c="dimmed" lineClamp={1} maw={280} title={a.description}>
                                    {a.description}
                                  </Text>
                                )}
                              </Table.Td>
                              <Table.Td>
                                {names.length ? <Text size="sm">{names.join(', ')}</Text> : <Dash />}
                              </Table.Td>
                              <Table.Td>
                                <Text size="sm" maw={300}>
                                  {scheduleLabel(a.schedule_text)}
                                </Text>
                              </Table.Td>
                              <Table.Td>
                                <Badge color={status.color}>{status.label}</Badge>
                              </Table.Td>
                              <Table.Td>
                                <Group gap={4} justify="flex-end" wrap="nowrap">
                                  <Tooltip label="Editar" withArrow>
                                    <ActionIcon
                                      variant="subtle"
                                      color="gray"
                                      aria-label={`Editar el área ${a.name}`}
                                      onClick={() => setDialog({ kind: 'area', area: a })}
                                    >
                                      <IconPencil size={16} />
                                    </ActionIcon>
                                  </Tooltip>
                                  <Tooltip label="Borrar" withArrow>
                                    <ActionIcon
                                      variant="subtle"
                                      color="red"
                                      aria-label={`Borrar el área ${a.name}`}
                                      onClick={() => void removeArea(a)}
                                    >
                                      <IconTrash size={16} />
                                    </ActionIcon>
                                  </Tooltip>
                                </Group>
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
        </Stack>
      </PlanGate>

      {dialog?.kind === 'member' && (
        <MemberModal
          key={dialog.member?.id ?? 'new'}
          member={dialog.member}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.kind === 'area' && (
        <AreaModal
          key={dialog.area?.id ?? 'new'}
          area={dialog.area}
          members={members}
          onClose={() => setDialog(null)}
        />
      )}
    </Stack>
  );
}
