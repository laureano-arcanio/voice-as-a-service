import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { LlmConnection } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { LlmConnectionsSection } from './LlmConnectionsSection';

const BASE = '/api/v1/clients/c-1/llm-connections';

const conn = (over: Partial<LlmConnection> = {}): LlmConnection => ({
  id: 'k-1',
  client_id: 'c-1',
  name: 'Mi OpenRouter',
  kind: 'openrouter',
  base_url: 'https://openrouter.ai/api/v1',
  last4: '1234',
  default_model: 'openai/gpt-4.1-mini',
  json_mode: 'json_schema',
  created_by: 'u-client',
  created_at: '2026-10-15T12:00:00Z',
  last_test_at: '2026-10-15T12:01:00Z',
  last_test_ok: true,
  last_test_detail: 'json_schema · 410 ms',
  used_by: 2,
  ...over,
});

interface Calls {
  method: string;
  path: string;
  body: unknown;
}

function mockApi(initial: LlmConnection[], tested?: Partial<LlmConnection>) {
  const calls: Calls[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const text = req.method === 'GET' ? '' : await req.clone().text();
      calls.push({ method: req.method, path: url.pathname, body: text ? JSON.parse(text) : null });
      const key = `${req.method} ${url.pathname}`;
      if (key === `GET ${BASE}`) return jsonResponse(initial);
      if (key === `POST ${BASE}`)
        return jsonResponse(conn({ id: 'k-new', name: 'Claude', kind: 'anthropic', last4: 'zz99', last_test_ok: null, last_test_detail: '', used_by: 0 }), 201);
      if (key === `POST ${BASE}/k-new/test` || key === `POST ${BASE}/k-1/test`)
        return jsonResponse(conn({ id: 'k-new', ...tested }));
      if (key === `DELETE ${BASE}/k-1`) return new Response(null, { status: 204 });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('LlmConnectionsSection', () => {
  it('sin conexiones explica que se usa el servidor Atentina', async () => {
    mockApi([]);
    renderWithProviders(<LlmConnectionsSection clientId="c-1" />, { me: CLIENT_USER });
    expect(await screen.findByText(/Sin conexiones: los agentes usan el Servidor Atentina/)).toBeInTheDocument();
  });

  it('lista la conexión con su clave enmascarada, estado y agentes que la usan', async () => {
    mockApi([conn(), conn({ id: 'k-2', name: 'Claude', kind: 'anthropic', last4: 'abcd', last_test_ok: false, last_test_detail: 'clave inválida o sin permiso', used_by: 0 })]);
    renderWithProviders(<LlmConnectionsSection clientId="c-1" />, { me: ADMIN });
    expect(await screen.findByText('Mi OpenRouter')).toBeInTheDocument();
    expect(screen.getByText('…1234')).toBeInTheDocument();
    expect(screen.getByText('Funciona')).toBeInTheDocument();
    expect(screen.getByText('Falló la prueba')).toBeInTheDocument();
    expect(screen.getByText('clave inválida o sin permiso')).toBeInTheDocument();
    expect(screen.queryByText(/sk-/)).not.toBeInTheDocument();
  });

  it('crea una conexión de Anthropic y la prueba enseguida', async () => {
    const calls = mockApi([], { last_test_ok: true, last_test_detail: 'json_schema · 380 ms' });
    renderWithProviders(<LlmConnectionsSection clientId="c-1" />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Nueva conexión/ }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/Nombre/), 'Claude');
    await userEvent.type(within(dialog).getByLabelText(/API key/), 'sk-ant-api03-zz99');
    await userEvent.type(within(dialog).getByLabelText(/Modelo por defecto/), 'claude-haiku-5-5');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar y probar' }));
    await waitFor(() => expect(calls.some((c) => c.path === `${BASE}/k-new/test`)).toBe(true));
    const created = calls.find((c) => c.method === 'POST' && c.path === BASE)!;
    expect(created.body).toEqual({
      name: 'Claude',
      kind: 'anthropic',
      api_key: 'sk-ant-api03-zz99',
      default_model: 'claude-haiku-5-5',
    });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('una conexión OpenAI compatible pide la URL base', async () => {
    mockApi([]);
    renderWithProviders(<LlmConnectionsSection clientId="c-1" />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Nueva conexión/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).queryByLabelText(/URL base/)).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('radio', { name: /OpenAI compatible/ }));
    expect(within(dialog).getByLabelText(/URL base/)).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Guardar y probar' })).toBeDisabled();
  });

  it('avisa cuántos agentes la usan antes de darla de baja', async () => {
    const calls = mockApi([conn()]);
    renderWithProviders(<LlmConnectionsSection clientId="c-1" />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Dar de baja' }));
    expect(await screen.findByText(/2 agentes la usan y pasan a contestar con el servidor Atentina/)).toBeInTheDocument();
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Dar de baja' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE' && c.path === `${BASE}/k-1`)).toBe(true));
  });
});
