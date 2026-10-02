import { Group, Stack, Text, Title } from '@mantine/core';
import { useDocumentTitle } from '@mantine/hooks';
import type { ReactNode } from 'react';

export function PageHeader({
  title,
  description,
  actions,
  above,
  docTitle,
}: {
  title: ReactNode;
  /** Titulo de la pestaña si `title` no es texto. */
  docTitle?: string;
  description?: ReactNode;
  actions?: ReactNode;
  above?: ReactNode;
}) {
  const tabTitle = typeof title === 'string' ? title : docTitle;
  useDocumentTitle(tabTitle ? `${tabTitle} · Atentina` : 'Atentina');
  return (
    <Stack gap={4} mb="md">
      {above}
      <Group justify="space-between" align="flex-end" gap="sm">
        <Stack gap={4} style={{ flex: 1, minWidth: 240 }}>
          <Title order={2}>{title}</Title>
          {description && (
            <Text c="dimmed" size="sm">
              {description}
            </Text>
          )}
        </Stack>
        {actions && <Group gap="xs">{actions}</Group>}
      </Group>
    </Stack>
  );
}
