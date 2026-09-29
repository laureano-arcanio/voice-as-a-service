import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { ModalsProvider } from '@mantine/modals';
import { Notifications, notifications } from '@mantine/notifications';
import { QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { RouterProvider } from 'react-router';
import { setUnauthorizedHandler } from '@/api/client';
import { meKey } from '@/features/auth/api';
import { createQueryClient } from '@/queryClient';
import { router } from '@/router';
import { cssVariablesResolver, theme } from '@/theme';

export function App() {
  const [queryClient] = useState(createQueryClient);

  // Un 401 con la sesion abierta (vencio o se desactivo el usuario): fuera y a /login.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (!queryClient.getQueryData(meKey)) return;
      queryClient.clear();
      queryClient.setQueryData(meKey, null);
      notifications.show({ id: 'session', color: 'yellow', message: 'Tu sesión venció. Ingresá de nuevo.' });
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  return (
    <MantineProvider theme={theme} cssVariablesResolver={cssVariablesResolver} defaultColorScheme="auto">
      <DatesProvider settings={{ locale: 'es', firstDayOfWeek: 1 }}>
        <QueryClientProvider client={queryClient}>
          <ModalsProvider labels={{ confirm: 'Confirmar', cancel: 'Cancelar' }}>
            <Notifications position="top-right" />
            <RouterProvider router={router} />
          </ModalsProvider>
        </QueryClientProvider>
      </DatesProvider>
    </MantineProvider>
  );
}
