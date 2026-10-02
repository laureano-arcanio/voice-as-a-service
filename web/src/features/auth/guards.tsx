import { Center, Loader, Stack, Text, Title, Button } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link, Navigate, useLocation } from 'react-router';
import type { Role } from '@/api/types';
import { errorMessage } from '@/api/errors';
import { useMe } from './api';

export function FullPageLoader() {
  return (
    <Center h="100vh">
      <Loader />
    </Center>
  );
}

/** Rutas con sesion: sin usuario, a /login (recordando a donde iba). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe();
  const location = useLocation();
  if (me.isPending) return <FullPageLoader />;
  if (me.isError) {
    return (
      <Center h="100vh">
        <Stack align="center">
          <Text c="red">{errorMessage(me.error)}</Text>
          <Button onClick={() => void me.refetch()}>Reintentar</Button>
        </Stack>
      </Center>
    );
  }
  if (!me.data) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}

export function Forbidden() {
  return (
    <Stack align="center" py="xl" gap="xs">
      <Title order={3}>Sin acceso</Title>
      <Text c="dimmed">Tu usuario no tiene acceso a esta sección.</Text>
      <Button component={Link} to="/" variant="default">
        Ir al inicio
      </Button>
    </Stack>
  );
}

/** Solo para un rol; si no, aviso de sin acceso. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { data } = useMe();
  if (!data || data.role !== role) return <Forbidden />;
  return <>{children}</>;
}
