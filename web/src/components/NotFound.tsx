import { Button, Stack, Text, Title } from '@mantine/core';
import { Link, isRouteErrorResponse, useRouteError } from 'react-router';

export function NotFound() {
  return (
    <Stack align="center" py={60} gap="xs">
      <Title order={1} c="amber.6">
        404
      </Title>
      <Title order={3}>No encontramos esta página</Title>
      <Text c="dimmed">Puede que el link esté mal o que ya no exista.</Text>
      <Button component={Link} to="/" mt="md">
        Ir al inicio
      </Button>
    </Stack>
  );
}

/** Error inesperado al renderizar una ruta. */
export function RouteError() {
  const error = useRouteError();
  if (isRouteErrorResponse(error) && error.status === 404) return <NotFound />;
  return (
    <Stack align="center" py={60} gap="xs" px="md">
      <Title order={3}>Algo salió mal</Title>
      <Text c="dimmed" ta="center">
        {error instanceof Error ? error.message : 'Error inesperado.'}
      </Text>
      <Button onClick={() => location.reload()} mt="md">
        Recargar
      </Button>
    </Stack>
  );
}
