import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Agent, Onboarding } from '@/api/types';
import { AppLayout } from '@/components/AppLayout';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { HomePage } from './HomePage';

const STATUS: Onboarding = {
  has_agents: false,
  industry: null,
  website: '',
  phone: '+5491155551234',
  phone_verified: false,
  verify_available: true,
  trial: { calls_used: 0, calls_max: 3, seconds_used: 0, seconds_max: 300 },
};

const AGENT: Agent = {
  id: 'ag-1',
  client_id: 'c-1',
  name: 'Lucas · atención',
  slug: 'lucas_atencion',
  description: '',
  version: 1,
  archived: false,
  voice: 'lucas',
  objective: 'Atender a quien se comunica con el gimnasio.',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};

function mockApi(routes: Record<string, () => Response>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const text = req.method === 'GET' ? '' : await req.clone().text();
      calls.push({ method: req.method, path: url.pathname, body: text ? JSON.parse(text) : null });
      const route = routes[`${req.method} ${url.pathname}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

const layout = (me = CLIENT_USER, path = '/inicio') =>
  renderWithProviders(<></>, {
    me,
    path,
    routes: [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { path: 'inicio', element: <p>Panel</p> },
          { path: 'plan', element: <p>Pantalla del plan</p> },
        ],
      },
    ],
  });

afterEach(() => vi.unstubAllGlobals());

describe('asistente de primera vez', () => {
  it('sin agentes muestra el asistente; elige rubro y voz y crea el agente', async () => {
    const calls = mockApi({
      'GET /api/v1/onboarding': () => jsonResponse(STATUS),
      'GET /api/v1/onboarding/industries': () =>
        jsonResponse([
          { id: 'gimnasio', label: 'Gimnasios y clubes', template_id: 'gimnasio' },
          { id: 'otro', label: 'Otro rubro', template_id: 'asistente' },
        ]),
      'POST /api/v1/onboarding/agent': () => jsonResponse({ ...AGENT, definition: {} }, 201),
    });
    layout();
    expect(await screen.findByText('Armemos el agente de Acme')).toBeInTheDocument();
    expect(screen.queryByText('Panel')).not.toBeInTheDocument();
    const next = await screen.findByRole('button', { name: /Elegir la voz/ });
    expect(next).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: /Gimnasios y clubes/ }));
    await userEvent.click(next);
    expect(await screen.findByText('Elegí la voz de tu agente')).toBeInTheDocument();
    expect(screen.getAllByRole('img', { name: /Retrato de/ })).toHaveLength(6);
    await userEvent.click(screen.getByRole('button', { name: /Lucas Amable/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear mi agente con Lucas' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ industry: 'gimnasio', voice: 'lucas', website: '' }),
    );
  });

  it('con agentes, o entrando como el cliente, muestra el panel', async () => {
    mockApi({ 'GET /api/v1/onboarding': () => jsonResponse({ ...STATUS, has_agents: true }) });
    layout();
    expect(await screen.findByText('Panel')).toBeInTheDocument();
  });

  it('el plan se abre aunque no haya agentes', async () => {
    mockApi({ 'GET /api/v1/onboarding': () => jsonResponse(STATUS) });
    layout(CLIENT_USER, '/plan');
    expect(await screen.findByText('Pantalla del plan')).toBeInTheDocument();
  });

  it('un admin en soporte no ve el asistente', async () => {
    const calls = mockApi({});
    layout({ ...ADMIN, role: 'client', client_id: 'c-1', client_name: 'Acme', support: true });
    expect(await screen.findByText('Panel')).toBeInTheDocument();
    expect(calls.some((c) => c.path === '/api/v1/onboarding')).toBe(false);
  });
});

describe('Inicio', () => {
  it('muestra los agentes con sus accesos y los próximos pasos', async () => {
    mockApi({
      'GET /api/v1/onboarding': () => jsonResponse({ ...STATUS, has_agents: true }),
      'GET /api/v1/agents': () => jsonResponse([AGENT]),
      'GET /api/v1/calls': () => jsonResponse({ items: [], total: 0 }),
    });
    renderWithProviders(<HomePage />, { me: CLIENT_USER, path: '/inicio?nuevo=ag-1' });
    expect(await screen.findByText('Lucas · atención')).toBeInTheDocument();
    expect(screen.getByText('¡Tu agente ya está listo!')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Hablarle ahora' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Editar' })).toHaveAttribute('href', '/agents/ag-1?tab=conversacion');
    expect(screen.getByText('Te faltan 3')).toBeInTheDocument();
  });
});
