import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Agent } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { TestAgentsPage } from './TestAgentsPage';

const agent = (id: string, name: string, objective: string): Agent => ({
  id,
  client_id: 'c-1',
  name,
  slug: id,
  description: '',
  objective,
  call_link_url: null,
  version: 1,
  archived: false,
  voice: 'sofia',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
});

afterEach(() => vi.unstubAllGlobals());

describe('TestAgentsPage', () => {
  it('muestra los agentes con su objetivo y prueba el elegido', async () => {
    const paths: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        const path = new URL(req.url).pathname;
        paths.push(path);
        if (path === '/api/v1/agents')
          return jsonResponse([agent('a1', 'Recepción', 'Atender consultas'), agent('a2', 'Turnos', 'Dar turnos')]);
        return jsonResponse({ detail: 'no mock' }, 404);
      }),
    );
    renderWithProviders(<TestAgentsPage />, { me: CLIENT_USER });

    expect(await screen.findByText('Atender consultas')).toBeInTheDocument();
    expect(screen.getByText('Dar turnos')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Recepción/ })).toBeChecked();
    expect(paths).toContain('/api/v1/agents/a1/call-link');

    await userEvent.click(screen.getByRole('radio', { name: /Turnos/ }));
    expect(screen.getByRole('radio', { name: /Turnos/ })).toBeChecked();
    expect(paths).toContain('/api/v1/agents/a2/call-link');
  });
});
