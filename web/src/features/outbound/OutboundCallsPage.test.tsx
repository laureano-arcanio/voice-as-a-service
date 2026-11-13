import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AgentDetail } from '@/api/types';
import { CATALOG } from '@/components/variables/fixtures';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { OutboundCallsPage } from './OutboundCallsPage';

const PLAN = {
  client_id: 'c-1',
  tier_name: 'Sucursal',
  free: false,
  features: { outbound_calls: { enabled: true, reason: null } },
};

const AGENT = {
  id: 'ag-1',
  client_id: 'c-1',
  name: 'Cobranzas',
  slug: 'cobranzas',
  description: '',
  version: 1,
  archived: false,
  voice: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};

const DETAIL: AgentDetail = {
  ...AGENT,
  definition: {
    agent: { name: 'Cobranzas', language: 'es-AR' },
    prompt: 'Llamá para avisar por {{motivo}} a {{nombre_cliente}}.',
    variables: [{ name: 'nombre_cliente', default: '', description: 'Cómo se llama' }],
  },
};

function mockApi() {
  const calls: { method: string; path: string; body?: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      const body = req.method === 'POST' ? await req.clone().json() : undefined;
      calls.push({ method: req.method, path, body });
      const routes: Record<string, () => Response> = {
        'GET /api/v1/plan/features': () => jsonResponse(PLAN),
        'GET /api/v1/agents': () => jsonResponse([AGENT]),
        'GET /api/v1/agents/ag-1': () => jsonResponse(DETAIL),
        'GET /api/v1/variables/catalog': () => jsonResponse(CATALOG),
        'GET /api/v1/phone-numbers': () => jsonResponse([]),
        'GET /api/v1/calls': () => jsonResponse({ items: [], total: 0 }),
        'POST /api/v1/calls': () => jsonResponse({ conversation_id: 'cv-1' }, 201),
      };
      const route = routes[`${req.method} ${path}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('llamada saliente suelta', () => {
  it('manda el motivo como variable y no como context', async () => {
    const calls = mockApi();
    renderWithProviders(<OutboundCallsPage />, { me: CLIENT_USER });
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/agents')).toBe(true));

    await userEvent.click(await screen.findByRole('textbox', { name: 'Agente' }));
    await userEvent.click(await screen.findByRole('option', { name: /Cobranzas/, hidden: true }));
    await userEvent.click(screen.getByLabelText('Otro número'));
    await userEvent.type(screen.getByLabelText('Teléfono'), '+5493515551234');

    // El motivo es una fila de los valores de la llamada, siempre presente y prellenada vacía.
    const motivo = await screen.findByLabelText('Valor de motivo');
    expect(motivo).toHaveValue('');
    expect(screen.getByText(/El motivo lo lee si su prompt dice \{\{motivo\}\}/)).toBeInTheDocument();
    await userEvent.type(motivo, 'Pidió presupuesto');

    await userEvent.click(screen.getByRole('button', { name: 'Llamar' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    const body = calls.find((c) => c.method === 'POST')?.body as Record<string, unknown>;
    expect(body).toMatchObject({ agent_id: 'ag-1', phone: '+5493515551234' });
    expect(body.variables).toEqual({ motivo: 'Pidió presupuesto' });
    expect(body).not.toHaveProperty('context');
    expect(await screen.findByText('Llamada iniciada')).toBeInTheDocument();
  });
});
