import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { ModalsProvider } from '@mantine/modals';
import { Notifications, notifications } from '@mantine/notifications';
import { QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { RouterProvider } from 'react-router';
import { setUnauthorizedHandler } from '@/api/client';
import { useBranding } from '@/branding/context';
import { BrandingProvider } from '@/branding/Provider';
import { brandCssVariables, brandTheme } from '@/branding/theme';
import { meKey, resetSession } from '@/features/auth/api';
import { createQueryClient } from '@/queryClient';
import { router } from '@/router';

/** Mantine con el tema de Atentina o, para un cliente con marca blanca, el suyo (docs/MARCA_BLANCA_PLAN.md). */
function Themed() {
  const branding = useBranding();
  const theme = useMemo(() => brandTheme(branding), [branding]);
  const cssVariables = useMemo(() => brandCssVariables(branding), [branding]);
  return (
    <MantineProvider theme={theme} cssVariablesResolver={cssVariables} forceColorScheme="light">
      <DatesProvider settings={{ locale: 'es', firstDayOfWeek: 1 }}>
        <ModalsProvider labels={{ confirm: 'Confirmar', cancel: 'Cancelar' }}>
          <Notifications position="top-right" />
          <RouterProvider router={router} />
        </ModalsProvider>
      </DatesProvider>
    </MantineProvider>
  );
}

export function App() {
  const [queryClient] = useState(createQueryClient);

  // Un 401 con la sesion abierta (vencio o se desactivo el usuario): fuera y a /login.
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
