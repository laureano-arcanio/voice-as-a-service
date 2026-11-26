import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AgentDetail } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { CaseDetail } from './CaseDetail';

const AGENT = {
  id: 'ag-1',
  client_id: 'c-1',
  name: 'Recepción',
  slug: 'recepcion',
  version: 3,
  archived: false,
  definition: { tools: [] },
} as unknown as AgentDetail;

const DETAIL = {
  id: 'tc-1',
  client_id: 'c-1',
  agent_id: 'ag-1',
  name: 'Salidas a Castelli',
  source_conversation_id: null,
  source_message_index: 1,
  source_agent_version: 3,
  channel: 'voice',
  known_failure: false,
  checks: [{ type: 'usa_herramienta', tool: 'salidas' }],
  tool_results: [{ name: 'salidas', result: '{"hay_lugar": 1}' }],
  snapshot: {
    messages: [{ role: 'assistant', text: 'Hola, soy Sofía.' }],
    user_message: '¿Hay salidas a Castelli?',
  },
  created_at: '2026-11-20T10:00:00Z',
  updated_at: '2026-11-20T10:00:00Z',
  history: [],
  last_run: null,
};

function mockApi() {
  const calls: { method: string; path: string; body: Record<string, unknown> | null }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const text = req.method === 'GET' ? '' : await req.clone().text();
      calls.push({ method: req.method, path: url.pathname, body: text ? JSON.parse(text) : null });
      if (url.pathname === '/api/v1/agents/ag-1/test-cases/tc-1' && req.method === 'GET')
        return jsonResponse(DETAIL);
      if (url.pathname === '/api/v1/agents/ag-1/test-cases/tc-1' && req.method === 'PATCH')
        return jsonResponse({ ...DETAIL, ...(calls.at(-1)?.body ?? {}), updated_at: '2026-11-20T11:00:00Z' });
      if (url.pathname === '/api/v1/agents/ag-1/test-cases/tc-1' && req.method === 'DELETE')
        return new Response(null, { status: 204 });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('CaseDetail', () => {
  it('editar los chequeos guarda el PATCH y borrar pide confirmación', async () => {
    const calls = mockApi();
    renderWithProviders(<CaseDetail agent={AGENT} caseId="tc-1" opened onClose={() => {}} />, {
      me: CLIENT_USER,
    });
    await screen.findByText('Salidas a Castelli');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar chequeos' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true));
    expect(calls.find((c) => c.method === 'PATCH')?.body).toMatchObject({
      checks: [{ type: 'usa_herramienta', tool: 'salidas' }],
      known_failure: false,
    });

    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }));
    await screen.findByText('Se borra el caso y su historial de corridas. Las conversaciones no se tocan.');
    const confirm = screen
      .getAllByRole('button', { name: 'Borrar' })
      .find((b) => b.closest('[role="dialog"]')?.textContent?.includes('Se borra el caso'));
    await userEvent.click(confirm!);
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true));
  });
});
