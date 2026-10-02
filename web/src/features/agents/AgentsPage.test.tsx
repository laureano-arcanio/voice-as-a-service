import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Agent, AgentTemplate } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { AgentsPage } from './AgentsPage';

const AGENT: Agent = {
  id: 'ag-1',
  client_id: 'c-1',
  name: 'Recepción',
  slug: 'recepcion',
  description: '',
  version: 1,
  archived: false,
  engine: 'classic',
  voice: 'sofia',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};

const TEMPLATE: AgentTemplate = {
  id: 'asistente',
  engine: 'classic',
  agent: 'Asistente, asistente virtual',
  voice: 'sofia',
  objective: 'Atender y tomar el contacto.',
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

afterEach(() => vi.unstubAllGlobals());

describe('AgentsPage', () => {
  it('cliente: crea un agente en su cuenta, sin elegir cliente, slug ni motor', async () => {
    const calls = mockApi({
      'GET /api/v1/agents': () => jsonResponse([]),
      'GET /api/v1/agent-templates': () => jsonResponse([TEMPLATE]),
      'POST /api/v1/agents': () => jsonResponse({ ...AGENT, definition: {} }, 201),
    });
    renderWithProviders(<AgentsPage />, { me: CLIENT_USER });

    // Vacio: explica el proximo paso y ofrece la accion.
    expect(await screen.findByText(/No tenés agentes activos/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Crear agente' }));

    const dialog = await screen.findByRole('dialog', { name: 'Nuevo agente' });
    expect(within(dialog).queryByLabelText('Cliente')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Slug')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('Motor')).not.toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText('Nombre'), 'Recepción');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear agente' }));

    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      client_id: null,
      name: 'Recepción',
      slug: null,
      description: '',
      engine: null,
      template_id: 'asistente',
    });
    // No pide la lista de clientes: no la necesita.
    expect(calls.some((c) => c.path === '/api/v1/clients')).toBe(false);
  });

  it('cliente: la lista no muestra columnas internas', async () => {
    mockApi({ 'GET /api/v1/agents': () => jsonResponse([AGENT]) });
    renderWithProviders(<AgentsPage />, { me: CLIENT_USER });
    expect(await screen.findByRole('link', { name: 'Recepción' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nuevo agente' })).toBeInTheDocument();
    for (const name of ['Slug', 'Cliente', 'Motor'])
      expect(screen.queryByRole('columnheader', { name })).not.toBeInTheDocument();
  });

  it('admin: el alta pide cliente y deja elegir slug y motor', async () => {
    mockApi({
      'GET /api/v1/agents': () => jsonResponse([AGENT]),
      'GET /api/v1/clients': () => jsonResponse([]),
      'GET /api/v1/agent-templates': () => jsonResponse([TEMPLATE]),
    });
    renderWithProviders(<AgentsPage />, { me: ADMIN });
    expect(await screen.findByRole('columnheader', { name: 'Motor' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Nuevo agente' }));
    const dialog = await screen.findByRole('dialog', { name: 'Nuevo agente' });
    expect(within(dialog).getByRole('textbox', { name: 'Cliente' })).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Slug')).toBeInTheDocument();
    expect(within(dialog).getByText('Motor')).toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText('Nombre'), 'Ventas');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear agente' }));
    expect(await within(dialog).findByText('Elegí un cliente')).toBeInTheDocument();
  });
});
