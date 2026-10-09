import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { TiersPage } from './TiersPage';

const TIER = {
  id: 't1',
  name: 'Free',
  description: '',
  max_concurrent_calls: 2,
  max_calls_per_hour: 20,
  max_calls_per_day: 20,
  max_calls_per_month: null,
  inbound_minutes: null,
  outbound_minutes: null,
  max_phone_numbers: 1,
  api_llm_input_tokens: 0,
  api_llm_output_tokens: 0,
  api_tts_minutes: 0,
  api_stt_minutes: 0,
  api_rate_limit: 60,
  created_at: '2026-10-01T00:00:00Z',
  clients_count: 0,
};

function mockApi() {
  const created: Record<string, unknown>[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(String(input));
      if (req.method === 'POST') {
        const body = await req.json();
        created.push(body);
        return jsonResponse({ ...TIER, ...body, id: 't2' }, 201);
      }
      return jsonResponse([TIER]);
    }),
  );
  return created;
}

describe('TiersPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('lista los límites de llamadas por hora, día y mes', async () => {
    mockApi();
    renderWithProviders(<TiersPage />, { me: ADMIN });
    expect(await screen.findByText('Free')).toBeInTheDocument();
    expect(screen.getByText('20 / 20 / Ilimitado')).toBeInTheDocument();
  });

  it('crea un tier con los límites de llamadas y los de la API por defecto', async () => {
    const created = mockApi();
    renderWithProviders(<TiersPage />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Nuevo tier/ }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Pro');
    await userEvent.type(screen.getByLabelText('Por hora'), '50');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toMatchObject({
      name: 'Pro',
      max_calls_per_hour: 50,
      max_calls_per_day: null,
      max_calls_per_month: null,
      max_concurrent_calls: null,
      api_llm_input_tokens: 0,
      api_rate_limit: 60,
    });
  });
});
