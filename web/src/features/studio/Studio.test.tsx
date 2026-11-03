import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { navItemsFor } from '@/components/nav';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { SpeechPage } from './SpeechPage';
import { TranscribePage } from './TranscribePage';

const ITEM = {
  id: 's-1',
  kind: 'tts',
  origin: 'studio',
  status: 'done',
  title: 'Hola, ¿qué tal?',
  voice: 'sofia',
  progress: 100,
  audio_seconds: 12,
  billed_seconds: 12,
  error: null,
  created_at: '2026-11-03T12:00:00',
  finished_at: '2026-11-03T12:01:00',
  excerpt: 'Hola, ¿qué tal?',
  text: null,
};

function stubApi(routes: Record<string, unknown>) {
  const calls: { path: string; method: string; body: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: Request) => {
      const url = new URL(input.url);
      const body = input.method === 'POST' ? await input.clone().text() : null;
      calls.push({ path: url.pathname, method: input.method, body });
      const key = Object.keys(routes).find((k) => url.pathname.endsWith(k));
      return jsonResponse(key ? routes[key] : {});
    }),
  );
  return calls;
}

const USAGE = { inbound: { remaining_minutes: 7 } };
const VOICES = [{ nombre: 'sofia', genero: 'mujer', wer: 3, car_s: 16.8 }];

describe('Estudio', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('todos los planes tienen las dos pantallas en el menú, sin candado', () => {
    const items = navItemsFor('client');
    for (const to of ['/texto-a-voz', '/transcribir']) {
      const item = items.find((i) => i.to === to);
      expect(item).toBeDefined();
      expect(item?.feature).toBeUndefined();
    }
  });

  it('texto a voz: sintetiza con la voz elegida y muestra el historial con formatos y minutos', async () => {
    const calls = stubApi({
      '/voices': VOICES,
      '/studio/items': { items: [ITEM], total: 1 },
      '/studio/speech': { ...ITEM, status: 'queued' },
      '/usage': USAGE,
    });
    renderWithProviders(<SpeechPage />, { me: CLIENT_USER });
    expect(await screen.findByText('Hola, ¿qué tal?')).toBeInTheDocument();
    expect(await screen.findByText(/te quedan 7 este mes/)).toBeInTheDocument();

    const submit = screen.getByRole('button', { name: 'Sintetizar' });
    expect(submit).toBeDisabled();
    await userEvent.type(screen.getByRole('textbox', { name: 'Texto' }), 'Buen día');
    await waitFor(() => expect(submit).toBeEnabled());
    await userEvent.click(submit);
    await waitFor(() => {
      const post = calls.find((c) => c.method === 'POST');
      expect(JSON.parse(post?.body as string)).toEqual({ text: 'Buen día', voice: 'sofia' });
    });

    await userEvent.click(screen.getByRole('button', { name: 'Descargar el audio' }));
    const mp3 = await screen.findByText('MP3');
    expect(mp3.closest('a')).toHaveAttribute('href', '/api/v1/studio/items/s-1/audio?format=mp3&download=true');
    for (const format of ['WAV', 'OGG (Opus)', 'FLAC']) expect(screen.getByText(format)).toBeInTheDocument();
  });

  it('transcribir: muestra el texto guardado con copiar y descargar', async () => {
    const stt = { ...ITEM, kind: 'stt', voice: null, title: 'reunion.mp3', excerpt: 'Empezamos' };
    stubApi({
      '/studio/items': { items: [stt], total: 1 },
      '/studio/items/s-1': { ...stt, text: 'Empezamos la reunión.' },
      '/usage': USAGE,
    });
    renderWithProviders(<TranscribePage />, { me: CLIENT_USER });
    expect(await screen.findByText('reunion.mp3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Transcribir' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Descargar el audio' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Ver el texto' }));
    expect(await screen.findByText('Empezamos la reunión.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copiar el texto' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Descargar .txt' })).toBeInTheDocument();
  });

  it('un admin como el cliente ve el historial y no puede generar ni borrar', async () => {
    stubApi({ '/voices': VOICES, '/studio/items': { items: [ITEM], total: 1 }, '/usage': USAGE });
    renderWithProviders(<SpeechPage />, { me: { ...CLIENT_USER, support: true } });
    expect(await screen.findByText('Hola, ¿qué tal?')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Texto' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Sintetizar' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Borrar' })).not.toBeInTheDocument();
  });
});
