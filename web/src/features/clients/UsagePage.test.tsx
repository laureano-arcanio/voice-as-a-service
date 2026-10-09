import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { UsagePage } from './UsagePage';

const CALLS_USAGE = {
  month: '2026-10',
  period_start: '2026-10-01T03:00:00Z',
  period_end: '2026-11-01T03:00:00Z',
  active_calls: 1,
  max_concurrent_calls: 4,
  inbound: { used_seconds: 600, used_minutes: 10, limit_minutes: 100, remaining_minutes: 90 },
  outbound: { used_seconds: 0, used_minutes: 0, limit_minutes: null, remaining_minutes: null },
  phone_numbers: { used: 1, limit: 2 },
  calls_hour: { used: 0, limit: null },
  calls_day: { used: 0, limit: null },
  calls_month: { used: 0, limit: null },
};
const API_USAGE = {
  month: '2026-10',
  period_start: '2026-10-01',
  period_end: '2026-11-01',
  rate_limit: null,
  llm_input_tokens: { used: 500, limit: 1000, remaining: 500 },
  llm_output_tokens: { used: 0, limit: null, remaining: null },
  tts_minutes: { used: 1.5, limit: 10, remaining: 8.5 },
  stt_minutes: { used: 0, limit: 10, remaining: 10 },
  requests: { llm: 2, stt: 0, tts: 1 },
  keys: [],
};

describe('UsagePage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('muestra el consumo de llamadas y el de la API del cliente, del mismo mes', async () => {
    const urls: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        urls.push(url.pathname);
        return jsonResponse(url.pathname.endsWith('/inference-usage') ? API_USAGE : CALLS_USAGE);
      }),
    );
    renderWithProviders(<UsagePage />, { me: CLIENT_USER });
    expect(await screen.findByRole('heading', { name: 'Consumos' })).toBeInTheDocument();
    expect(await screen.findByText('Minutos entrantes')).toBeInTheDocument();
    expect(await screen.findByText('Consumo de la API')).toBeInTheDocument();
    expect(await screen.findByText('LLM · tokens de entrada')).toBeInTheDocument();
    expect(urls).toContain('/api/v1/clients/c-1/usage');
    expect(urls).toContain('/api/v1/clients/c-1/inference-usage');
  });
});
