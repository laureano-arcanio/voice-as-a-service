import { Badge, Tooltip } from '@mantine/core';
import { Dash } from '@/components/Badges';
import { MESSAGE_STATUS, STAGES } from '../format';
import type { MessageStatus, Stage } from '../types';

export function StageBadge({ stage }: { stage: Stage | null | undefined }) {
  if (!stage) return <Dash />;
  const l = STAGES[stage] ?? { label: stage, color: 'gray' };
  return <Badge color={l.color}>{l.label}</Badge>;
}

export function MessageStatusBadge({ status, error }: { status: MessageStatus; error?: string | null }) {
  const l = MESSAGE_STATUS[status] ?? { label: status, color: 'gray' };
  const badge = <Badge color={l.color}>{l.label}</Badge>;
  return error ? (
    <Tooltip label={error} withArrow multiline maw={320}>
      {badge}
    </Tooltip>
  ) : (
    badge
  );
}
