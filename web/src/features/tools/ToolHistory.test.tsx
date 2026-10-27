import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ToolHistory } from './ToolHistory';

afterEach(() => vi.unstubAllGlobals());

describe('ToolHistory', () => {
  it('lista las revisiones con su fecha y la definición, y marca la vigente', async () => {
    const fetch = vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      if (new URL(req.url).pathname === '/api/v1/clients/c-1/tools/reservar/versions')
        return jsonResponse([
          {
            revision: 2,
            type: 'http',
            definition: { description: 'Reserva v2.' },
            created_by: null,
            created_at: '2026-10-26T12:00:00Z',
          },
          {
            revision: 1,
            type: 'http',
            definition: { description: 'Reserva v1.' },
            created_by: null,
            created_at: '2026-10-25T12:00:00Z',
          },
        ]);
      return jsonResponse({ detail: 'no mock' }, 404);
    });
    vi.stubGlobal('fetch', fetch);
    renderWithProviders(
      <ToolHistory clientId="c-1" slug="reservar" current={2} opened onClose={() => {}} />,
      { me: CLIENT_USER },
    );
    expect(await screen.findByText('rev. 2')).toBeInTheDocument();
    expect(screen.getByText('rev. 1')).toBeInTheDocument();
    expect(screen.getByText('Vigente')).toBeInTheDocument();
    expect(screen.getByText(/"description": "Reserva v2."/)).toBeInTheDocument();
  });
});
