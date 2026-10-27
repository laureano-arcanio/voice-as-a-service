import { ActionIcon, Badge, Group, Select, Stack, Text, Tooltip } from '@mantine/core';
import { IconArrowDown, IconArrowUp, IconPlus, IconX } from '@tabler/icons-react';
import type { ReactNode } from 'react';
import type { TeamMember } from '@/api/types';

/**
 * Personas del equipo en orden (areas de derivacion y numeros que atiende el equipo): subir, bajar, quitar y
 * agregar. `detail` pone lo propio de cada uso (el telefono, que le falta) al lado del nombre.
 */
export function MemberPicker({
  members,
  value,
  onChange,
  addLabel,
  removeLabel,
  detail,
}: {
  /** Las personas del equipo del cliente. */
  members: TeamMember[];
  /** Los ids elegidos, en orden. */
  value: string[];
  onChange: (ids: string[]) => void;
  /** Etiqueta accesible del selector que agrega ("Agregar persona al área"). */
  addLabel: string;
  /** Tooltip de quitar ("Quitar del área"). */
  removeLabel: string;
  detail: (member: TeamMember | undefined) => ReactNode;
}) {
  const byId = new Map(members.map((m) => [m.id, m]));
  const available = members.filter((m) => !value.includes(m.id));
  const move = (i: number, d: -1 | 1) => {
    const ids = [...value];
    [ids[i], ids[i + d]] = [ids[i + d], ids[i]];
    onChange(ids);
  };
  return (
    <>
      {value.length > 0 && (
        <Stack gap={6}>
          {value.map((id, i) => {
            const m = byId.get(id);
            const name = m?.name ?? 'Persona borrada';
            return (
              <Group key={id} className="def-item" justify="space-between" wrap="nowrap" gap="xs">
                <Group gap="xs" wrap="wrap" style={{ minWidth: 0 }}>
                  <Text className="mono" c="dimmed" w={18} ta="right">
                    {i + 1}
                  </Text>
                  <Text size="sm" fw={600} truncate>
                    {name}
                  </Text>
                  {detail(m)}
                  {m && !m.active && <Badge color="gray">Inactiva</Badge>}
                </Group>
                <Group gap={4} wrap="nowrap">
                  <Tooltip label="Subir" withArrow>
                    <ActionIcon
                      variant="default"
                      aria-label={`Subir a ${name}`}
                      disabled={i === 0}
                      onClick={() => move(i, -1)}
                    >
                      <IconArrowUp size={16} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Bajar" withArrow>
                    <ActionIcon
                      variant="default"
                      aria-label={`Bajar a ${name}`}
                      disabled={i === value.length - 1}
                      onClick={() => move(i, 1)}
                    >
                      <IconArrowDown size={16} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label={removeLabel} withArrow>
                    <ActionIcon
                      variant="default"
                      aria-label={`Quitar a ${name}`}
                      onClick={() => onChange(value.filter((x) => x !== id))}
                    >
                      <IconX size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Group>
            );
          })}
        </Stack>
      )}
      {members.length === 0 ? (
        <Text size="sm" c="dimmed">
          Todavía no hay personas en el equipo: cargalas primero en Equipo, sección Personas.
        </Text>
      ) : (
        available.length > 0 && (
          <Select
            aria-label={addLabel}
            placeholder="Agregar persona"
            data={available.map((m) => ({ value: m.id, label: m.name }))}
            value={null}
            onChange={(id) => id && onChange([...value, id])}
            searchable
            leftSection={<IconPlus size={16} />}
          />
        )
      )}
    </>
  );
}
