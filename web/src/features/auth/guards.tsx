import { Center, Loader, Stack, Text, Title, Button } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link, Navigate, useLocation } from 'react-router';
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

/** Panel del cliente: un admin que no entró a un cliente va a la administración. */
export function RequireClientArea({ children }: { children: ReactNode }) {
  const { data } = useMe();
  if (data?.role === 'admin') return <Navigate to="/admin" replace />;
  return <>{children}</>;
}

/** Administración: solo admins. Un admin dentro de un cliente (me.role === 'client') también va al panel del
 * cliente: se sale con "Volver a administración" (salir acá cortaría la entrada, que cambia `me` antes de navegar). */
export function RequireAdminArea({ children }: { children: ReactNode }) {
  const { data } = useMe();
  if (data?.role !== 'admin') return <Navigate to="/" replace />;
  return <>{children}</>;
}
