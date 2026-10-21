import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { ModalsProvider } from '@mantine/modals';
import { Notifications } from '@mantine/notifications';
import { QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { RouterProvider } from 'react-router';
import { createQueryClient } from '@/queryClient';
import { cssVariablesResolver, theme } from '@/theme';
import { useApiKey } from './api';
import { KeyGate } from './KeyGate';
import { crmRouter } from './router';

export function CrmApp() {
  const [queryClient] = useState(createQueryClient);
  const key = useApiKey();
  return (
    <MantineProvider theme={theme} cssVariablesResolver={cssVariablesResolver} forceColorScheme="light">
      <DatesProvider settings={{ locale: 'es', firstDayOfWeek: 1 }}>
        <QueryClientProvider client={queryClient}>
          <ModalsProvider labels={{ confirm: 'Confirmar', cancel: 'Cancelar' }}>
            <Notifications position="top-right" />
            {key ? <RouterProvider router={crmRouter} /> : <KeyGate onSaved={() => queryClient.clear()} />}
          </ModalsProvider>
        </QueryClientProvider>
      </DatesProvider>
    </MantineProvider>
  );
}
