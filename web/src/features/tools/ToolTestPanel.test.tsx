import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { TEMPLATE_VARS } from './draft';
import { ToolTestPanel } from './ToolTestPanel';

afterEach(() => vi.unstubAllGlobals());

describe('ToolTestPanel', () => {
  it('manda el número de ejemplo como from y como phone ({{call.phone}} no queda vacío)', async () => {
    const bodies: unknown[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const req = input instanceof Request ? input : new Request(input, init);
        const path = new URL(req.url).pathname;
        if (path === '/api/v1/clients/c-1/tools/test') {
          bodies.push(await req.json());
          return jsonResponse({
            ok: true,
            status: 200,
            ms: 3,
            data: {},
            error: null,
            llm: '{}',
            request: null,
            logs: [],
            assigned: {},
          });
        }
        return jsonResponse([]);
      }),
    );
    renderWithProviders(
      <ToolTestPanel
        clientId="c-1"
        type="http"
        definition={{ description: 'x', http: { method: 'POST', url: 'https://x.com/a' } }}
        secrets={[]}
      />,
      { me: CLIENT_USER },
    );
    await userEvent.type(screen.getByLabelText(/Número de quien llama/), '+5491100000000');
    await userEvent.click(screen.getByRole('button', { name: 'Probar herramienta' }));
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      call: { from: '+5491100000000', phone: '+5491100000000', channel: 'voice', mode: 'inbound' },
    });
  });

  it('el menú de variables ofrece {{call.phone}}', () => {
    const all = TEMPLATE_VARS.flatMap((g) => g.items.map((i) => i.value));
    expect(all).toContain('{{call.phone}}');
  });
});
