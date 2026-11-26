import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { CompareModal } from './CompareModal';

const RUN = {
  id: 'r1',
  client_id: 'c-1',
  agent_id: 'ag-1',
  status: 'done',
  repetitions: 5,
  variants: [{ key: 'publicada', version: 1 }, { key: 'borrador', version: 2 }],
  cases: [{ id: 'c1', name: 'Horarios' }],
  done: 10,
  total: 10,
  input_tokens: 0,
  output_tokens: 0,
  error: null,
  created_at: '2026-11-20T10:00:00Z',
  started_at: '2026-11-20T10:00:00Z',
  finished_at: '2026-11-20T10:01:00Z',
  results: [
    {
      case_id: 'c1',
      name: 'Horarios',
      known_failure: false,
      variants: [
        { key: 'publicada', version: 1, passed: 5, total: 5, errors: 0, repetitions: [] },
        { key: 'borrador', version: 2, passed: 3, total: 5, errors: 0, repetitions: [] },
      ],
    },
  ],
};

afterEach(() => vi.unstubAllGlobals());

describe('CompareModal', () => {
  it('muestra publicada y cambios por caso y marca lo que empeora', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        if (new URL(req.url).pathname === '/api/v1/agents/ag-1/test-runs/r1') return jsonResponse(RUN);
        return jsonResponse({ detail: 'no mock' }, 404);
      }),
    );
    renderWithProviders(<CompareModal agentId="ag-1" runId="r1" opened onClose={() => {}} />, {
      me: CLIENT_USER,
    });
    expect(await screen.findByText('pasa 5/5')).toBeInTheDocument();
    expect(screen.getByText(/pasa 3\/5/)).toBeInTheDocument();
    expect(screen.getByText(/empeora/)).toBeInTheDocument();
  });

  it('avisa cuando parte de la comparación la contestó el respaldo local', async () => {
    const conRespaldo = {
      ...RUN,
      results: [
        {
          ...RUN.results[0],
          variants: [
            {
              key: 'publicada', version: 1, passed: 5, total: 5, errors: 0,
              fallbacks: 5, fallback_reasons: { 'BadRequestError 400': 5 }, repetitions: [],
            },
            {
              key: 'borrador', version: 2, passed: 3, total: 5, errors: 0,
              fallbacks: 2, fallback_reasons: { RuntimeError: 2 }, repetitions: [],
            },
          ],
        },
      ],
    };
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        if (new URL(req.url).pathname === '/api/v1/agents/ag-1/test-runs/r1') return jsonResponse(conRespaldo);
        return jsonResponse({ detail: 'no mock' }, 404);
      }),
    );
    renderWithProviders(<CompareModal agentId="ag-1" runId="r1" opened onClose={() => {}} />, {
      me: CLIENT_USER,
    });
    expect(
      await screen.findByText('Parte de la comparación la contestó el respaldo local, no el modelo configurado.'),
    ).toBeInTheDocument();
    expect(screen.getByText('pasa 5/5 · 5 respaldo')).toBeInTheDocument();
    expect(screen.getByText(/pasa 3\/5 · 2 respaldo/)).toBeInTheDocument();
  });

  it('una corrida con otros modelos muestra una columna por variante y su label', async () => {
    const conModelos = {
      ...RUN,
      variants: [
        { key: 'publicada', version: 1 },
        { key: 'm1', version: 1, label: 'OpenRouter · vendor/a' },
        { key: 'm2', version: 1, label: 'LLM de Atentina' },
      ],
      results: [
        {
          ...RUN.results[0],
          variants: [
            { key: 'publicada', version: 1, passed: 5, total: 5, errors: 0, repetitions: [] },
            {
              key: 'm1', version: 1, passed: 3, total: 5, errors: 0, repetitions: [],
              label: 'OpenRouter · vendor/a',
            },
            { key: 'm2', version: 1, passed: 5, total: 5, errors: 0, repetitions: [], label: 'LLM de Atentina' },
          ],
        },
      ],
    };
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        if (new URL(req.url).pathname === '/api/v1/agents/ag-1/test-runs/r1') return jsonResponse(conModelos);
        return jsonResponse({ detail: 'no mock' }, 404);
      }),
    );
    renderWithProviders(<CompareModal agentId="ag-1" runId="r1" opened onClose={() => {}} />, {
      me: CLIENT_USER,
    });
    expect(await screen.findByText('OpenRouter · vendor/a')).toBeInTheDocument();
    expect(screen.getByText('LLM de Atentina')).toBeInTheDocument();
    expect(screen.getAllByText('pasa 5/5')).toHaveLength(2);
    expect(screen.getByText(/pasa 3\/5/)).toBeInTheDocument();
    expect(screen.getByText(/empeora/)).toBeInTheDocument();
    // La corrida no pidió borrador: no aparece el aviso de «los cambios son iguales».
    expect(screen.queryByText(/Los cambios son iguales/)).not.toBeInTheDocument();
  });

  it('una corrida cancelada a mitad muestra lo que alcanzó a correr', async () => {
    const cancelled = {
      ...RUN,
      status: 'cancelled',
      done: 8,
      cancel_requested_at: '2026-11-20T10:00:20Z',
      results: [
        {
          ...RUN.results[0],
          variants: [
            { key: 'publicada', version: 1, passed: 5, total: 5, errors: 0, repetitions: [] },
            { key: 'borrador', version: 2, passed: 2, total: 3, errors: 0, repetitions: [] },
          ],
        },
      ],
    };
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        if (new URL(req.url).pathname === '/api/v1/agents/ag-1/test-runs/r1') return jsonResponse(cancelled);
        return jsonResponse({ detail: 'no mock' }, 404);
      }),
    );
    renderWithProviders(<CompareModal agentId="ag-1" runId="r1" opened onClose={() => {}} />, {
      me: CLIENT_USER,
    });
    expect(await screen.findByText('Cancelada')).toBeInTheDocument();
    expect(screen.getByText('pasa 5/5')).toBeInTheDocument();
    expect(screen.getByText(/pasa 2\/3/)).toBeInTheDocument();
    expect(screen.getByText(/empeora/)).toBeInTheDocument();
  });
});
