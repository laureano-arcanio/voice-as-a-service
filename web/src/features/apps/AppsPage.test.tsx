import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { App } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { parseParams } from './params';
import { AppsPage } from './AppsPage';

const APP: App = {
  id: 'app-1',
  slug: 'sugym-gestion',
  name: 'SUGYM · Gestión',
  client_id: null,
  client_name: null,
  base_url: 'http://app-sugym-gestion:8000',
  version: '0.1.0',
  status: 'ok',
  last_error: null,
  last_health_at: '2026-10-12T11:00:00Z',
  created_at: '2026-10-12T10:00:00Z',
  views: [{ name: 'minuta', title: 'Minuta del día', description: 'Los que vinieron en el día.' }],
  tools: [
    { name: 'buscar_alumno', kind: 'read', description: 'Busca alumnos por nombre.' },
    { name: 'baja_alumno', kind: 'destructive', description: 'Da de baja un alumno.' },
  ],
};

type Route = (url: URL, req: Request) => Response | Promise<Response>;

function mockApi(routes: Record<string, Route>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const text = req.method === 'GET' ? '' : await req.clone().text();
      calls.push({ method: req.method, path: url.pathname, body: text ? JSON.parse(text) : null });
      const route = routes[`${req.method} ${url.pathname}`];
      return route ? route(url, req) : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('parseParams', () => {
  it('lee nombre=valor separados por & o coma', () => {
    expect(parseParams('')).toEqual({});
    expect(parseParams('fecha=2026-10-12')).toEqual({ fecha: '2026-10-12' });
    expect(parseParams(' fecha = 2026-10-12 & dias=7, x=1')).toEqual({
      fecha: '2026-10-12',
      dias: '7',
      x: '1',
    });
  });
  it('rechaza lo que no se entiende', () => {
    expect(parseParams('2026-10-12')).toBeNull();
    expect(parseParams('fecha=')).toBeNull();
    expect(parseParams('mal-nombre=1')).toBeNull();
  });
});

describe('AppsPage', () => {
  it('admin: inventario con estado, detalle de herramientas y asignar', async () => {
    const calls = mockApi({
      'GET /api/v1/apps': () => jsonResponse([APP]),
      'GET /api/v1/clients': () => jsonResponse([{ id: 'c-1', name: 'SUGYM' }]),
      'POST /api/v1/apps/app-1/assign': () =>
        jsonResponse({ ...APP, client_id: 'c-1', client_name: 'SUGYM' }),
    });
    renderWithProviders(<AppsPage />, { me: ADMIN });

    expect(await screen.findByText('SUGYM · Gestión')).toBeInTheDocument();
    expect(screen.getByText('sugym-gestion')).toBeInTheDocument();
    expect(screen.getByText('Responde')).toBeInTheDocument();
    expect(screen.getByText('Libre')).toBeInTheDocument();
    // Sin cliente no hay links.
    expect(screen.queryByRole('button', { name: /Link a una vista/ })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /1 vista · 2 herramientas/ }));
    expect(screen.getByText('baja_alumno')).toBeInTheDocument();
    expect(screen.getByText('Borra')).toBeInTheDocument();
    expect(screen.getByText(/las confirma con la persona/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Asignar' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('textbox', { name: 'Cliente' }));
    await userEvent.click((await screen.findAllByRole('option', { name: 'SUGYM', hidden: true })).at(-1)!);
    await userEvent.click(within(dialog).getByRole('button', { name: 'Asignar' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')).toEqual({
        method: 'POST',
        path: '/api/v1/apps/app-1/assign',
        body: { client_id: 'c-1' },
      }),
    );
  });

  it('admin: sin apps explica como registrarlas', async () => {
    mockApi({ 'GET /api/v1/apps': () => jsonResponse([]), 'GET /api/v1/clients': () => jsonResponse([]) });
    renderWithProviders(<AppsPage />, { me: ADMIN });
    expect(await screen.findByText(/make register/)).toBeInTheDocument();
  });

  it('cliente: sin columna de cliente; crea un link y lo muestra una vez', async () => {
    const mine = { ...APP, client_id: 'c-1', client_name: 'SUGYM' };
    const calls = mockApi({
      'GET /api/v1/apps': () => jsonResponse([mine]),
      'POST /api/v1/apps/app-1/links': () =>
        jsonResponse(
          {
            id: 'l-1',
            view: 'minuta',
            params: { fecha: '2026-10-12' },
            created_by: 'user:u-client',
            created_at: '2026-10-12T11:00:00Z',
            expires_at: '2026-10-19T11:00:00Z',
            revoked_at: null,
            opens: 0,
            last_opened_at: null,
            url: 'https://apps.atentina.com.ar/sugym/sugym-gestion/minuta/?fecha=2026-10-12&k=abc',
          },
          201,
        ),
    });
    renderWithProviders(<AppsPage />, { me: CLIENT_USER });

    expect(await screen.findByText('SUGYM · Gestión')).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
    expect(screen.queryByText('sugym-gestion')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Asignar' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Link a una vista/ }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText('Parámetros'), 'fecha=2026-10-12');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear link' }));
    expect(await within(dialog).findByText(/k=abc/)).toBeInTheDocument();
    expect(within(dialog).getByText(/no se vuelve a mostrar/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      view: 'minuta',
      params: { fecha: '2026-10-12' },
    });
  });
});
