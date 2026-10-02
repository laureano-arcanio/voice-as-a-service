import { Badge, Group, Text } from '@mantine/core';
import { IconCheck } from '@tabler/icons-react';
import type { ReactNode } from 'react';
import { CALL_MODE, CALL_STATUS, WORKFLOW_STATUS, type Label } from '@/lib/labels';

/** Valor faltante: raya en dimmed. */
export function Dash() {
  return (
    <Text span inherit c="dimmed">
      –
    </Text>
  );
}

/** En curso: pildora azul con el punto que pulsa. */
export function LiveBadge({ children }: { children: ReactNode }) {
  return (
    <Badge color="blue" leftSection={<span className="live-dot" aria-hidden />}>
      {children}
    </Badge>
  );
}

function MappedBadge({ map, value }: { map: Record<string, Label>; value: string | null | undefined }) {
  if (!value) return <Dash />;
  const l = map[value] ?? { label: value, color: 'gray' };
  return <Badge color={l.color}>{l.label}</Badge>;
}

export function CallStatusBadge({ status }: { status: string | null | undefined }) {
  if (status === 'sonando' || status === 'en_curso')
    return <LiveBadge>{CALL_STATUS[status].label}</LiveBadge>;
  return <MappedBadge map={CALL_STATUS} value={status} />;
}

export function WorkflowBadge({ status }: { status: string | null | undefined }) {
  return <MappedBadge map={WORKFLOW_STATUS} value={status} />;
}

/** Modo de la llamada con el telefono al lado (o debajo, con `wrap`, si no entra). */
export function OriginBadge({
  mode,
  phone,
  wrap = false,
}: {
  mode: string | null | undefined;
  phone?: string | null;
  wrap?: boolean;
}) {
  return (
    <Group gap={6} wrap={wrap ? 'wrap' : 'nowrap'}>
      <MappedBadge map={CALL_MODE} value={mode} />
      {phone && (
        <Text span c="dimmed" className="mono">
          {phone}
        </Text>
      )}
    </Group>
  );
}

/** Resultado de la conversacion: verde y con check si cumple el objetivo. */
export function OutcomeBadge({ label, goal }: { label: string | null | undefined; goal: boolean }) {
  if (!label) return <Dash />;
  return (
    <Badge
      color={goal ? 'green' : 'gray'}
      leftSection={goal ? <IconCheck size={12} aria-hidden /> : undefined}
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
