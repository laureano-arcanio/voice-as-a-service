import { Alert, Button, Center, Group, Loader, Text } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import type { ReactNode } from 'react';
import { errorMessage } from '@/api/errors';

interface QueryLike<T> {
  data: T | undefined;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/** Cargando / error / datos de una query, sin repetir el patron en cada pagina. */
export function QueryState<T>({
  query,
  children,
  loader,
}: {
  query: QueryLike<T>;
  children: (data: T) => ReactNode;
  loader?: ReactNode;
}) {
  if (query.isPending) {
    return (
      loader ?? (
        <Center py="xl">
          <Loader size="sm" />
        </Center>
      )
    );
  }
  if (query.isError || query.data === undefined)
    return <ErrorAlert error={query.error} onRetry={query.refetch} />;
  return <>{children(query.data)}</>;
}

export function ErrorAlert({
  error,
  onRetry,
  title,
}: {
  error: unknown;
  onRetry?: () => unknown;
  title?: string;
}) {
  return (
    <Alert color="red" icon={<IconAlertCircle size={18} />} title={title}>
      <Group justify="space-between" gap="xs">
        <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
          {errorMessage(error)}
        </Text>
        {onRetry && (
          <Button size="xs" variant="light" color="red" onClick={() => void onRetry()}>
            Reintentar
          </Button>
        )}
      </Group>
    </Alert>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <Text c="dimmed" size="sm" ta="center" py="lg">
      {children}
    </Text>
  );
}
