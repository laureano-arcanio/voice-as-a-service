import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Agent } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { TestCallButton } from './TestCallButton';

const AGENT = {
  id: 'a1',
  client_id: 'c-1',
  name: 'Recepción',
  slug: 'a1',
  description: '',
  objective: '',
  call_link_url: null,
  version: 1,
  archived: false,
  engine: 'classic',
  voice: 'sofia',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
} as Agent;

function mockApi(waiting: string | null) {
  const posts: unknown[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      if (url.pathname === '/api/v1/calls' && req.method === 'GET') {
        expect(url.searchParams.get('mode')).toBe('prueba');
        expect(url.searchParams.getAll('status')).toEqual(['pendiente', 'sonando']);
        return jsonResponse({ items: waiting ? [{ id: waiting }] : [], total: waiting ? 1 : 0 });
      }
      if (url.pathname === '/api/v1/calls' && req.method === 'POST') {
        posts.push(await req.json());
        return jsonResponse(
          { conversation_id: 'nueva', room: 'call-nueva', mode: 'prueba', join_url: 'x' },
          201,
        );
      }
      if (url.pathname === '/api/v1/plan/features')
        return jsonResponse({ client_id: 'c-1', tier_name: 'Pyme', free: false, features: {} });
      return jsonResponse([]);
    }),
  );
  return posts;
}

function renderButton() {
  return renderWithProviders(<TestCallButton agent={AGENT} />, {
    me: CLIENT_USER,
    routes: [
      { path: '/probar', element: <TestCallButton agent={AGENT} /> },
      { path: '/calls/:id/hablar', element: <p>pantalla de la llamada</p> },
    ],
    path: '/probar',
  });
}

describe('TestCallButton', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('entra a la prueba que espera conexión sin crear otra', async () => {
    const posts = mockApi('espera');
    const { router } = renderButton();
    await userEvent.click(await screen.findByRole('button', { name: 'Probar agente' }));
    expect(await screen.findByText('pantalla de la llamada')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/calls/espera/hablar');
    expect(posts).toHaveLength(0);
  });

  it('sin una esperando, la crea y la abre', async () => {
    const posts = mockApi(null);
    const { router } = renderButton();
    await userEvent.click(await screen.findByRole('button', { name: 'Probar agente' }));
    expect(await screen.findByText('pantalla de la llamada')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/calls/nueva/hablar');
    expect(posts).toEqual([expect.objectContaining({ agent_id: 'a1', phone: null })]);
  });
});
