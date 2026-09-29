import { Badge, Group, Text } from '@mantine/core';
import { CALL_MODE, CALL_STATUS, WORKFLOW_STATUS, type Label } from '@/lib/labels';

function MappedBadge({ map, value }: { map: Record<string, Label>; value: string | null | undefined }) {
  if (!value)
    return (
      <Text span inherit c="dimmed">
        –
      </Text>
    );
  const l = map[value] ?? { label: value, color: 'gray' };
  return <Badge color={l.color}>{l.label}</Badge>;
}

export function CallStatusBadge({ status }: { status: string | null | undefined }) {
  return <MappedBadge map={CALL_STATUS} value={status} />;
}

export function WorkflowBadge({ status }: { status: string | null | undefined }) {
  return <MappedBadge map={WORKFLOW_STATUS} value={status} />;
}

/** Modo de la llamada con el telefono al lado. */
export function OriginBadge({ mode, phone }: { mode: string | null | undefined; phone?: string | null }) {
  return (
    <Group gap={6} wrap="nowrap">
      <MappedBadge map={CALL_MODE} value={mode} />
      {phone && (
        <Text span size="xs" c="dimmed" className="mono">
          {phone}
        </Text>
      )}
    </Group>
  );
}

export function OutcomeBadge({ label, goal }: { label: string | null | undefined; goal: boolean }) {
  if (!label)
    return (
      <Text span inherit c="dimmed">
        –
      </Text>
    );
  return (
    <Badge
      color={goal ? 'green' : 'gray'}
      variant={goal ? 'filled' : 'light'}
      style={{ textTransform: 'none' }}
    >
      {label}
    </Badge>
  );
}

export function ActiveBadge({
  active,
  on = 'Activo',
  off = 'Inactivo',
}: {
  active: boolean;
  on?: string;
  off?: string;
}) {
  return <Badge color={active ? 'green' : 'gray'}>{active ? on : off}</Badge>;
}
