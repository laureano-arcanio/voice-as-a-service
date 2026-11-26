import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AgentDetail, LlmConnection } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ModelRunModal } from './ModelRunModal';

const CONN: LlmConnection = {
  id: 'k-1',
  client_id: 'c-1',
  name: 'Mi OpenRouter',
  kind: 'openrouter',
  base_url: 'https://openrouter.ai/api/v1',
  last4: 'or91',
  default_model: 'vendor/model',
  json_mode: 'json_schema',
  created_by: null,
  created_at: '2026-10-15T12:00:00Z',
  last_test_at: null,
  last_test_ok: null,
  last_test_detail: '',
  used_by: 0,
};

const AGENT = { id: 'ag-1', client_id: 'c-1', name: 'Sofía' } as unknown as AgentDetail;

const RUN = {
  id: 'r1',
  client_id: 'c-1',
  agent_id: 'ag-1',
  status: 'queued',
  repetitions: 5,
  variants: [],
  cases: [],
  results: null,
  done: 0,
  total: 15,
  input_tokens: 0,
  output_tokens: 0,
  error: null,
  created_at: '2026-11-20T10:00:00Z',
  started_at: null,
  finished_at: null,
  cancel_requested_at: null,
};

const cases = (n: number) =>
  Array.from({ length: n }, (_, i) => ({
    id: `c${i}`,
    agent_id: 'ag-1',
    name: `Caso ${i + 1}`,
    channel: 'voice',
    known_failure: false,
    created_at: '2026-11-20T10:00:00Z',
    updated_at: '2026-11-20T10:00:00Z',
    last_run: null,
  }));

function mockApi(caseCount: number, bodies: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const req = input instanceof Request ? input : new Request(input, init);
      const path = new URL(req.url).pathname;
      if (path === '/api/v1/clients/c-1/llm-connections') return jsonResponse([CONN]);
      if (path === '/api/v1/clients/c-1/llm-connections/k-1/models') return jsonResponse(['vendor/model']);
      if (path === '/api/v1/llm/openrouter-providers') return jsonResponse([]);
      if (path === '/api/v1/agents/ag-1/test-cases') return jsonResponse(cases(caseCount));
      if (path === '/api/v1/agents/ag-1/test-runs' && req.method === 'POST') {
        bodies.push(JSON.parse(await req.text()));
        return jsonResponse(RUN, 202);
      }
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

/** El <input> de un campo de Mantine (getByLabelText también trae el div de la familia Combobox). */
function fieldInput(root: HTMLElement, label: string): HTMLInputElement {
  const found = within(root).getAllByLabelText(label).find((el) => el instanceof HTMLInputElement);
  if (!found) throw new Error(`sin input para ${label}`);
  return found as HTMLInputElement;
}

afterEach(() => vi.unstubAllGlobals());

describe('ModelRunModal', () => {
  it('arma el cuerpo con dos filas y el LLM propio sin `model`', async () => {
    const bodies: unknown[] = [];
    mockApi(1, bodies);
    renderWithProviders(<ModelRunModal agent={AGENT} opened onClose={() => {}} />, { me: CLIENT_USER });
    await userEvent.click(screen.getByRole('button', { name: 'Agregar modelo' }));
    const row2 = screen.getByTestId('model-row-1');
    await userEvent.click(fieldInput(row2, 'Contesta'));
    // Las opciones de los dos Select están en el DOM: la última es la de la fila nueva.
    const options = await screen.findAllByRole('option', { name: /Mi OpenRouter/, hidden: true });
    await userEvent.click(options[options.length - 1]);
    expect(await screen.findByText(/15 turnos de 300/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Correr' }));
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toEqual({
      repetitions: 5,
      models: [{ connection_id: null }, { connection_id: 'k-1', model: 'vendor/model' }],
      published_fallback: true,
    });
  });

  it('con más de 300 turnos deshabilita «Correr»', async () => {
    const bodies: unknown[] = [];
    mockApi(11, bodies);
    renderWithProviders(<ModelRunModal agent={AGENT} opened onClose={() => {}} />, { me: CLIENT_USER });
    await userEvent.click(screen.getByRole('button', { name: 'Agregar modelo' }));
    await userEvent.click(screen.getByRole('radio', { name: '10×' }));
    expect(await screen.findByText(/330 turnos de 300/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Correr' })).toBeDisabled();
    expect(bodies).toHaveLength(0);
  });
});
