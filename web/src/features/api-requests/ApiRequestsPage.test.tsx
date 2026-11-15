import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ApiRequest, ApiRequestContent, ApiRequestPage } from '@/api/types';
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
  has_content: false,
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
    renderWithProviders(<ApiRequestsPage />, {
      me: ADMIN,
      path: '/?kind=tts&status=error&source=voice_test_landing&range=1',
    });
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

describe('ApiRequestsPage: contenido guardado', () => {
  afterEach(() => vi.unstubAllGlobals());

  const withContent = (r: ApiRequest): ApiRequest => ({ ...r, has_content: true });
  const CONTENTS: Record<string, ApiRequestContent> = {
    r1: {
      id: 'r1',
      kind: 'llm',
      source: 'api',
      created_at: BASE.created_at,
      request: { messages: [{ role: 'user', content: 'hola' }] },
      response: { content: 'buen día', finish_reason: 'stop' },
      input_audio: null,
      output_audio: null,
      truncated: false,
    },
    r2: {
      id: 'r2',
      kind: 'stt',
      source: 'api',
      created_at: BASE.created_at,
      request: null,
      response: { text: 'texto transcripto' },
      input_audio: { content_type: 'audio/mpeg', bytes: 2048 },
      output_audio: null,
      truncated: false,
    },
    r3: {
      id: 'r3',
      kind: 'tts',
      source: 'api',
      created_at: BASE.created_at,
      request: { input: 'hola mundo', voice: 'sofia' },
      response: null,
      input_audio: null,
      output_audio: { content_type: 'audio/wav', bytes: 480000 },
      truncated: true,
    },
    r4: {
      id: 'r4',
      kind: 'tts',
      source: 'voice_test_landing',
      created_at: BASE.created_at,
      request: { input: 'prueba de la landing', voice: 'sofia' },
      response: null,
      input_audio: null,
      output_audio: { content_type: 'audio/wav', bytes: 96000 },
      truncated: false,
    },
  };

  function stub(items: ApiRequest[]) {
    const calls: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        const url = new URL(req.url);
        calls.push(`${req.method} ${url.pathname}`);
        if (url.pathname === '/api/v1/api-requests')
          return Promise.resolve(jsonResponse({ ...PAGE, items, total: items.length }));
        const m = url.pathname.match(/^\/api\/v1\/api-requests\/(\w+)\/content$/);
        if (m && req.method === 'GET') return Promise.resolve(jsonResponse(CONTENTS[m[1]!]));
        if (m && req.method === 'DELETE') return Promise.resolve(new Response(null, { status: 204 }));
        return Promise.resolve(jsonResponse([]));
      }),
    );
    return calls;
  }

  const [r1, r2, r3, r4] = PAGE.items as [ApiRequest, ApiRequest, ApiRequest, ApiRequest];

  it('LLM: pedido y respuesta en JSON, sin reproductor', async () => {
    stub([withContent(r1)]);
    renderWithProviders(<ApiRequestsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Ver/ }));
    const dlg = await screen.findByRole('dialog');
    expect(await within(dlg).findByText(/"content": "hola"/)).toBeInTheDocument();
    expect(within(dlg).getByText(/"finish_reason": "stop"/)).toBeInTheDocument();
    expect(dlg.querySelector('audio')).toBeNull();
  });

  it('STT: audio enviado con su descarga y la respuesta', async () => {
    stub([withContent(r2)]);
    renderWithProviders(<ApiRequestsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Ver/ }));
    const dlg = await screen.findByRole('dialog');
    expect(await within(dlg).findByText(/texto transcripto/)).toBeInTheDocument();
    expect(dlg.querySelector('audio')).toHaveAttribute('src', '/api/v1/api-requests/r2/audio/input');
    expect(within(dlg).getByRole('link', { name: /Descargar/ })).toHaveAttribute(
      'href',
      '/api/v1/api-requests/r2/audio/input?download=true',
    );
  });

  it('TTS: audio generado y aviso si se cortó en el tope', async () => {
    stub([withContent(r3)]);
    renderWithProviders(<ApiRequestsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Ver/ }));
    const dlg = await screen.findByRole('dialog');
    expect(await within(dlg).findByText(/hola mundo/)).toBeInTheDocument();
    expect(dlg.querySelector('audio')).toHaveAttribute('src', '/api/v1/api-requests/r3/audio/output');
    expect(within(dlg).getByText(/audio guardado está cortado/)).toBeInTheDocument();
  });

  it('prueba de voz de la landing: el admin la ve con su origen y la escucha', async () => {
    stub([withContent({ ...r4, source: 'voice_test_landing' })]);
    renderWithProviders(<ApiRequestsPage />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Ver/ }));
    const dlg = await screen.findByRole('dialog');
    expect(await within(dlg).findByText(/prueba de la landing/)).toBeInTheDocument();
    expect(within(dlg).getByText('Prueba de voz · landing')).toBeInTheDocument();
    expect(dlg.querySelector('audio')).toHaveAttribute('src', '/api/v1/api-requests/r4/audio/output');
  });

  it('una fila sin contenido dice que no hay y no lo pide', async () => {
    const calls = stub([r1]);
    renderWithProviders(<ApiRequestsPage />, { me: CLIENT_USER });
    expect(screen.queryByRole('button', { name: /Ver/ })).not.toBeInTheDocument();
    await userEvent.click(await screen.findByText('120 / 45'));
    const dlg = await screen.findByRole('dialog');
    expect(within(dlg).getByText('Sin contenido guardado.')).toBeInTheDocument();
    expect(calls.some((c) => c.endsWith('/content'))).toBe(false);
  });

  it('borrar pide confirmación, borra y cierra', async () => {
    const calls = stub([withContent(r1)]);
    renderWithProviders(<ApiRequestsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Ver/ }));
    const dlg = await screen.findByRole('dialog');
    await userEvent.click(await within(dlg).findByRole('button', { name: /Borrar contenido/ }));
    // Sin confirmar no se borra.
    expect(calls).not.toContain('DELETE /api/v1/api-requests/r1/content');
    await userEvent.click(await screen.findByRole('button', { name: 'Borrar', hidden: true }));
    await waitFor(() => expect(calls).toContain('DELETE /api/v1/api-requests/r1/content'));
    // La lista se vuelve a pedir.
    await waitFor(() =>
      expect(calls.filter((c) => c === 'GET /api/v1/api-requests').length).toBeGreaterThan(1),
    );
  });
});
