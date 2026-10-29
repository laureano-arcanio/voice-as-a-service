import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CallSummary } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ConversationsPage } from './ConversationsPage';

const CALL: CallSummary = {
  id: 'cv-1',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: 'ag-1',
  agent_name: 'Ventas',
  agent_version: 1,
  workflow_status: 'completed',
  created_at: '2026-10-12T12:00:00Z',
  contact_name: 'Ana',
  company: 'Acme SA',
  outcome: 'Turno agendado',
  goal: true,
  captured: 3,
  required: 3,
  mode: 'saliente',
  phone: '+5491155551234',
  status: 'finalizada',
  duration_seconds: 65,
  ended_reason: 'completed',
  latency_avg: 1.2,
};

function mockApi(routes: Record<string, () => Response>) {
  const calls: { method: string; path: string; body?: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      const body = req.method === 'POST' ? await req.clone().json() : undefined;
      calls.push({ method: req.method, path, body });
      const route = routes[`${req.method} ${path}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

const listRoutes = (items: CallSummary[], deleted = 1) => ({
  'GET /api/v1/calls': () => jsonResponse({ items, total: items.length }),
  'GET /api/v1/agents': () => jsonResponse([]),
  'GET /api/v1/clients': () => jsonResponse([]),
  'POST /api/v1/calls/bulk-delete': () => jsonResponse({ deleted }),
});

afterEach(() => vi.unstubAllGlobals());

describe('conversaciones', () => {
  it('admin: selecciona y borra en bulk, confirmando antes', async () => {
    const calls = mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: ADMIN });

    const row = await screen.findByRole('checkbox', { name: /Seleccionar conversación/ });
    await userEvent.click(row);
    expect(screen.getByText('1 seleccionada')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Borrar seleccionadas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Borrar conversación' });
    expect(within(dialog).getByText(/No se puede deshacer/)).toBeInTheDocument();
    // Cancelar no borra nada.
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));
    expect(calls.some((c) => c.method === 'POST')).toBe(false);

    await userEvent.click(screen.getByRole('button', { name: 'Borrar seleccionadas' }));
    const again = await screen.findByRole('dialog', { name: 'Borrar conversación' });
    await userEvent.click(within(again).getByRole('button', { name: 'Borrar' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/bulk-delete'))).toBe(true),
    );
    const post = calls.find((c) => c.method === 'POST');
    expect(post?.body).toEqual({ ids: ['cv-1'] });
  });

  it('admin: el icono de la fila borra esa conversación, con confirmación', async () => {
    const calls = mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: ADMIN });

    await userEvent.click(await screen.findByRole('button', { name: 'Borrar conversación' }));
    const dialog = await screen.findByRole('dialog', { name: 'Borrar conversación' });
    expect(within(dialog).getByText(/Se borra la conversación/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Borrar' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ ids: ['cv-1'] });
  });

  it('cliente: sin selección ni borrado', async () => {
    mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });

    expect(await screen.findByRole('link', { name: 'Ver conversación' })).toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Borrar conversación' })).not.toBeInTheDocument();
  });

  it('filtra por campaña: las llamadas que hizo y las que abrió', async () => {
    const urls: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        const url = new URL(req.url);
        urls.push(`${url.pathname}${url.search}`);
        if (url.pathname === '/api/v1/calls') return jsonResponse({ items: [CALL], total: 1 });
        if (url.pathname === '/api/v1/campaigns')
          return jsonResponse([{ id: 'cmp-9', name: 'Cobranza octubre', channel: 'voice' }]);
        return jsonResponse([]);
      }),
    );
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('textbox', { name: 'Campaña' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Cobranza octubre · Llamadas', hidden: true }),
    );
    await waitFor(() =>
      expect(urls.some((u) => u.startsWith('/api/v1/calls') && u.includes('campaign_id=cmp-9'))).toBe(true),
    );
  });
});
