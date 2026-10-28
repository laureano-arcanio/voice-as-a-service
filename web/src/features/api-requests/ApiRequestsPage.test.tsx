import { screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiRequest, ApiRequestPage } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ApiRequestsPage } from './ApiRequestsPage';

const BASE: ApiRequest = {
  id: 'r1',
  created_at: '2026-10-22T13:05:09+00:00',
  client_id: 'c-1',
  client_name: 'Acme',
  api_key_id: 'k1',
  api_key_name: 'CRM',
  api_key_prefix: 'vaas_abc',
  kind: 'llm',
  stream: true,
  status: 'ok',
  http_status: 200,
  error_code: null,
  duration_ms: 824,
  ttfb_ms: 32,
  input_tokens: 120,
  output_tokens: 45,
  audio_seconds: null,
  characters: null,
  voice: null,
  response_format: null,
  source: 'api',
};

const PAGE: ApiRequestPage = {
  items: [
    BASE,
    {
      ...BASE,
      id: 'r2',
      kind: 'tts',
      stream: false,
      voice: 'sofia',
      response_format: 'wav',
      duration_ms: 2100,
      ttfb_ms: 2095,
      input_tokens: null,
      output_tokens: null,
      audio_seconds: 10.2,
      characters: 194,
    },
    {
      ...BASE,
      id: 'r3',
      kind: 'stt',
      stream: false,
      status: 'rejected',
      http_status: 429,
      error_code: 'api_stt_minutes',
      duration_ms: 0,
      ttfb_ms: null,
      input_tokens: null,
      output_tokens: null,
    },
    {
      ...BASE,
      id: 'r4',
      kind: 'tts',
      source: 'voice_test_panel',
      api_key_id: null,
      api_key_name: null,
      api_key_prefix: null,
      voice: 'sofia',
      duration_ms: 700,
      ttfb_ms: 80,
      input_tokens: null,
      output_tokens: null,
      audio_seconds: 3.1,
      characters: 60,
    },
  ],
  total: 4,
  summary: {
    requests: 3,
    by_status: { ok: 2, cut: 0, error: 0, rejected: 1 },
    by_kind: { llm: 1, stt: 1, tts: 1 },
    input_tokens: 120,
    output_tokens: 45,
    stt_seconds: 0,
    tts_seconds: 10.2,
    avg_duration_ms: 1462,
  },
};

function stubApi() {
  const urls: URL[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      urls.push(url);
      if (url.pathname === '/api/v1/api-requests') return Promise.resolve(jsonResponse(PAGE));
      return Promise.resolve(jsonResponse([]));
    }),
  );
  return urls;
}

describe('ApiRequestsPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('el cliente ve sus pedidos con tipo, duración y consumo, sin datos internos', async () => {
    const urls = stubApi();
    renderWithProviders(<ApiRequestsPage />, { me: CLIENT_USER });
    expect(await screen.findByText('120 / 45')).toBeInTheDocument();
    expect(screen.getByText('824 ms')).toBeInTheDocument();
    expect(screen.getByText('10,2 s')).toBeInTheDocument();
    expect(screen.getByText('de audio · 194 caracteres')).toBeInTheDocument();
    // La prueba de voz del panel, sin API key: el origen la aclara.
    expect(within(screen.getByRole('table')).getByText('Prueba de voz · panel')).toBeInTheDocument();
    expect(within(screen.getByRole('table')).getByText('Rechazado por el plan')).toBeInTheDocument();
    expect(screen.queryByText('Primer byte')).not.toBeInTheDocument();
    expect(screen.queryByText('429 api_stt_minutes')).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
    const list = urls.find((u) => u.pathname === '/api/v1/api-requests')!;
    expect(list.searchParams.get('client_id')).toBeNull(); // la API lo acota a su cliente
  });

  it('el admin ve el cliente, el primer byte y el código de error, y filtra por la URL', async () => {
    const urls = stubApi();
    renderWithProviders(<ApiRequestsPage />, { me: ADMIN, path: '/?kind=tts&status=error&source=voice_test_landing&range=1' });
    expect(await screen.findByText('429 api_stt_minutes')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Cliente' })).toBeInTheDocument();
    expect(screen.getByText('32 ms')).toBeInTheDocument();
    const list = urls.find((u) => u.pathname === '/api/v1/api-requests')!;
    expect(list.searchParams.getAll('kind')).toEqual(['tts']);
    expect(list.searchParams.getAll('status')).toEqual(['error']);
    expect(list.searchParams.getAll('source')).toEqual(['voice_test_landing']);
    expect(list.searchParams.get('date_from')).toBe(list.searchParams.get('date_to'));
  });
});
