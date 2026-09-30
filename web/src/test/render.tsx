import { MantineProvider } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router';
import type { Me } from '@/api/types';
import { meKey } from '@/features/auth/api';
import { theme } from '@/theme';

export const ADMIN: Me = {
  id: 'u-admin',
  email: 'admin@atentina.com.ar',
  name: 'Admin',
  role: 'admin',
  client_id: null,
  client_name: null,
};

export const CLIENT_USER: Me = {
  id: 'u-client',
  email: 'ana@acme.com',
  name: 'Ana',
  role: 'client',
  client_id: 'c-1',
  client_name: 'Acme',
};

/** Renderiza con Mantine, React Query (con `me` precargado si se pasa) y un router en memoria. */
export function renderWithProviders(
  ui: ReactElement,
  { me, path = '/', routes }: { me?: Me | null; path?: string; routes?: RouteObject[] } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  if (me !== undefined) queryClient.setQueryData(meKey, me);
  const router = createMemoryRouter(routes ?? [{ path: '*', element: ui }], { initialEntries: [path] });
  const result = render(
    <MantineProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <ModalsProvider>
          <RouterProvider router={router} />
        </ModalsProvider>
      </QueryClientProvider>
    </MantineProvider>,
  );
  return { ...result, queryClient, router };
}

/** Respuesta JSON para mockear fetch. */
export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}
