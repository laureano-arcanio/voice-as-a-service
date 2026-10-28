// Raíz de la app del teléfono (telefono.html): los providers del panel, con un router en memoria para el ingreso
// y "Olvidé mi clave" (la URL queda siempre en `/`, en su host o en /movil del panel).
import { Button, Center, MantineProvider, Stack, Text, Title } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { Notifications, notifications } from '@mantine/notifications';
import { QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode, useEffect, useMemo, useState } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { setUnauthorizedHandler } from '@/api/client';
import { useBranding } from '@/branding/context';
import { BrandingProvider } from '@/branding/Provider';
import { brandCssVariables, brandTheme } from '@/branding/theme';
import { meKey, resetSession, useCurrentUser, useLogout } from '@/features/auth/api';
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage';
import { RequireAuth } from '@/features/auth/guards';
import { LoginPage } from '@/features/auth/LoginPage';
import { CallProvider } from '@/features/phone/CallProvider';
import { createQueryClient } from '@/queryClient';
import { PhoneApp } from './PhoneApp';

/** Solo para usuarios de un cliente: el admin no tiene teléfono (entra al panel). */
function ClientOnly({ children }: { children: ReactNode }) {
  const me = useCurrentUser();
  const logout = useLogout();
  if (me.role === 'client') return <>{children}</>;
  return (
    <Center mih="100dvh" p="md">
      <Stack align="center" gap="xs" maw={360} ta="center">
        <Title order={3}>Teléfono del equipo</Title>
        <Text c="dimmed">Es para los usuarios de una empresa. Ingresá con tu usuario del equipo.</Text>
        <Button variant="default" onClick={() => logout.mutate()} loading={logout.isPending}>
          Cerrar sesión
        </Button>
      </Stack>
    </Center>
  );
}

const phoneRoutes = [
  { path: '/login', element: <LoginPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  {
    path: '*',
    element: (
      <RequireAuth>
        <ClientOnly>
          <CallProvider>
            <PhoneApp />
          </CallProvider>
        </ClientOnly>
      </RequireAuth>
    ),
  },
];

function Themed() {
  const branding = useBranding();
  const theme = useMemo(() => brandTheme(branding), [branding]);
  const cssVariables = useMemo(() => brandCssVariables(branding), [branding]);
  const [router] = useState(() => createMemoryRouter(phoneRoutes));
  return (
    <MantineProvider theme={theme} cssVariablesResolver={cssVariables} forceColorScheme="light">
      <ModalsProvider labels={{ confirm: 'Confirmar', cancel: 'Cancelar' }}>
        <Notifications position="top-center" />
        <RouterProvider router={router} />
      </ModalsProvider>
    </MantineProvider>
  );
}

export function PhoneRoot() {
  const [queryClient] = useState(createQueryClient);

  // Un 401 con la sesión abierta: fuera y al ingreso (como en el panel, App.tsx).
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (!queryClient.getQueryData(meKey)) return;
      resetSession(queryClient, null);
      notifications.show({ id: 'session', color: 'yellow', message: 'Tu sesión venció. Ingresá de nuevo.' });
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrandingProvider>
        <Themed />
      </BrandingProvider>
    </QueryClientProvider>
  );
}
