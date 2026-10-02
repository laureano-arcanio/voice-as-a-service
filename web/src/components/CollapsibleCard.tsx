import { Card, Collapse, Group, Title, UnstyledButton } from '@mantine/core';
import { IconChevronDown } from '@tabler/icons-react';
import type { ReactNode } from 'react';

/** Tarjeta que se pliega desde su titulo. El estado lo maneja quien la usa. */
export function CollapsibleCard({
  title,
  icon,
  opened,
  onToggle,
  children,
}: {
  title: string;
  icon?: ReactNode;
  opened: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <Card>
      <UnstyledButton className="card-toggle" onClick={onToggle} aria-expanded={opened}>
        <Group gap="xs" wrap="nowrap">
          {icon}
          <Title order={4}>{title}</Title>
        </Group>
        <IconChevronDown size={18} className="chevron" aria-hidden />
      </UnstyledButton>
      <Collapse in={opened}>
        <div style={{ paddingTop: 'var(--mantine-spacing-md)' }}>{children}</div>
      </Collapse>
    </Card>
  );
}
