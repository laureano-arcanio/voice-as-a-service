import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { navItemsFor } from '@/components/nav';
import { DevelopersPage } from './DevelopersPage';
import { inferenceExample } from './examples';

const KEY = {
  id: 'k1',
  client_id: 'c-1',
  name: 'CRM',
  prefix: 'vaas_abc',
  scopes: ['calls', 'llm'],
  created_at: '2026-10-01T00:00:00Z',
  last_used_at: null,
  revoked_at: null,
};
const USAGE = {
  month: '2026-10',
  period_start: '2026-10-01',
  period_end: '2026-11-01',
  rate_limit: 60,
  llm_input_tokens: { used: 0, limit: 1000, remaining: 1000 },
  llm_output_tokens: { used: 0, limit: 1000, remaining: 1000 },
  tts_minutes: { used: 0, limit: 10, remaining: 10 },
  stt_minutes: { used: 0, limit: 10, remaining: 10 },
  requests: { llm: 0, stt: 0, tts: 0 },
  keys: [],
};

function mockApi() {
  const created: unknown[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(String(input));
      const path = new URL(req.url).pathname;
      if (path.endsWith('/inference-usage')) return jsonResponse(USAGE);
      if (path.endsWith('/api-keys') && req.method === 'POST') {
        const body = await req.json();
        created.push(body);
        return jsonResponse({ ...KEY, name: body.name, scopes: body.scopes, key: 'vaas_secreta123' }, 201);
      }
      if (path.endsWith('/api-keys')) return jsonResponse([KEY]);
      return jsonResponse({}, 404);
    }),
  );
  return created;
}

describe('DevelopersPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('está en el menú del cliente y no en el del admin', () => {
    expect(navItemsFor('client').some((i) => i.to === '/developers')).toBe(true);
    expect(navItemsFor('admin').some((i) => i.to === '/developers')).toBe(false);
  });

  it('muestra las keys con su alcance, el consumo y la conexión', async () => {
    mockApi();
    renderWithProviders(<DevelopersPage />, { me: CLIENT_USER });
    expect(await screen.findByText('CRM')).toBeInTheDocument();
    const row = screen.getByText('CRM').closest('tr')!;
    expect(within(row).getByText('calls')).toBeInTheDocument();
    expect(within(row).getByText('llm')).toBeInTheDocument();
    expect(await screen.findByText('Consumo de la API')).toBeInTheDocument();
    expect(screen.getByText(`${location.origin}/api/v1/inference`)).toBeInTheDocument();
    expect(screen.getByText(/POST \/audio\/transcriptions/)).toBeInTheDocument();
  });

  it('crea una key con el alcance elegido y muestra los ejemplos de esos motores', async () => {
    const created = mockApi();
    renderWithProviders(<DevelopersPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Nueva API key/ }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Bot');
    // Por defecto solo "calls"; se suman STT y TTS y se saca calls.
    await userEvent.click(screen.getByRole('checkbox', { name: /Transcripción \(STT\)/ }));
    await userEvent.click(screen.getByRole('checkbox', { name: /Síntesis \(TTS\)/ }));
    await userEvent.click(screen.getByRole('checkbox', { name: /Llamadas y agentes/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear' }));
    await waitFor(() => expect(created).toEqual([{ name: 'Bot', scopes: ['stt', 'tts'] }]));
    expect(await screen.findByText('vaas_secreta123')).toBeInTheDocument();
    const dialog = within(screen.getByRole('dialog'));
    expect(dialog.getByRole('tab', { name: 'Transcripción (STT)' })).toBeInTheDocument();
    expect(dialog.getByRole('tab', { name: 'Síntesis (TTS)' })).toBeInTheDocument();
    expect(dialog.queryByRole('tab', { name: 'LLM (chat)' })).not.toBeInTheDocument();
    expect(dialog.queryByRole('tab', { name: 'Lanzar una llamada' })).not.toBeInTheDocument();
  });

  it('no deja crear una key sin ningún alcance', async () => {
    mockApi();
    renderWithProviders(<DevelopersPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Nueva API key/ }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Nada');
    await userEvent.click(screen.getByRole('checkbox', { name: /Llamadas y agentes/ }));
    expect(screen.getByRole('button', { name: 'Crear' })).toBeDisabled();
  });
});

describe('ejemplos', () => {
  it('llevan la URL base y la key', () => {
    for (const kind of ['llm', 'stt', 'tts', 'python'] as const) {
      const code = inferenceExample(kind, 'https://app.atentina.com.ar', 'vaas_x');
      expect(code).toContain('https://app.atentina.com.ar/api/v1/inference');
      expect(code).toContain('vaas_x');
    }
  });
});
