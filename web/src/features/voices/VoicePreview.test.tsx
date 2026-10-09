import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PCM_SAMPLE_RATE } from '@/lib/pcmPlayer';
import { renderWithProviders } from '@/test/render';
import { VoicePreview } from './VoicePreview';

const contexts: FakeAudioContext[] = [];

/** AudioContext minimo (jsdom no trae): lo programado "suena" hasta que el test lo termina. */
class FakeAudioContext {
  currentTime = 0;
  state: 'running' | 'suspended' = 'suspended';
  destination = {};
  sources: { onended: (() => void) | null }[] = [];
  resume = vi.fn(async () => {
    this.state = 'running';
  });
  suspend = vi.fn(async () => {
    this.state = 'suspended';
  });
  close = vi.fn(async () => undefined);
  constructor() {
    contexts.push(this);
  }
  createBuffer(_c: number, length: number, rate: number) {
    const data = new Float32Array(length);
    return { duration: length / rate, getChannelData: () => data };
  }
  createBufferSource() {
    const source = {
      buffer: null,
      onended: null as (() => void) | null,
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    };
    this.sources.push(source);
    return source;
  }
  finishAll() {
    this.sources.forEach((s) => s.onended?.());
  }
}

function pcmResponse(seconds: number) {
  const bytes = new Uint8Array(seconds * PCM_SAMPLE_RATE * 2);
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      c.enqueue(bytes.subarray(0, 3840)); // como el motor: un bloque chico y despues uno grande
      c.enqueue(bytes.subarray(3840));
      c.close();
    },
  });
  return new Response(stream, { status: 200, headers: { 'Content-Type': 'audio/pcm' } });
}

describe('VoicePreview', () => {
  const play = vi.fn(async () => undefined);
  const bodies: unknown[] = [];

  beforeEach(() => {
    contexts.length = 0;
    bodies.length = 0;
    vi.stubGlobal('AudioContext', FakeAudioContext);
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(String(input));
        bodies.push(await req.json());
        return pcmResponse(2);
      }),
    );
    URL.createObjectURL = vi.fn(() => 'blob:wav');
    URL.revokeObjectURL = vi.fn();
    HTMLMediaElement.prototype.play = play;
    HTMLMediaElement.prototype.pause = vi.fn();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    play.mockClear();
  });

  it('pide PCM, suena mientras se genera, pausa y continua, y repite desde el WAV guardado sin regenerar', async () => {
    renderWithProviders(<VoicePreview voice="sofia" />);
    await userEvent.click(screen.getByRole('button', { name: 'Reproducir' }));

    // Suena apenas hay colchon: el boton pasa a Pausar y pidio PCM en streaming.
    expect(await screen.findByRole('button', { name: 'Pausar' })).toBeInTheDocument();
    expect(bodies).toHaveLength(1);
    expect(bodies[0]).toMatchObject({ voice: 'sofia', format: 'pcm' });
    expect(await screen.findByText(/empezó a sonar a los .* s · generado en/)).toBeInTheDocument();

    // Pausa y continua sobre el mismo audio.
    await userEvent.click(screen.getByRole('button', { name: 'Pausar' }));
    expect(contexts[0].suspend).toHaveBeenCalled();
    await userEvent.click(await screen.findByRole('button', { name: 'Reproducir' }));
    expect(await screen.findByRole('button', { name: 'Pausar' })).toBeInTheDocument();
    expect(bodies).toHaveLength(1);

    // Termina de sonar: queda listo para repetir, y repetir no vuelve a generar.
    contexts[0].finishAll();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Reproducir' })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Reproducir' }));
    await waitFor(() => expect(play).toHaveBeenCalledTimes(1));
    expect(bodies).toHaveLength(1);
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
  });

  it('un error del servidor se muestra y deja volver a intentar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: 'Voz inexistente: x' }), {
            status: 422,
            headers: { 'Content-Type': 'application/json' },
          }),
      ),
    );
    renderWithProviders(<VoicePreview voice="sofia" />);
    await userEvent.click(screen.getByRole('button', { name: 'Reproducir' }));
    expect(await screen.findByText(/No se pudo generar el audio: Voz inexistente/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reproducir' })).toBeEnabled();
  });

  it('sin voz no pide nada', async () => {
    renderWithProviders(<VoicePreview voice={null} />);
    await userEvent.click(screen.getByRole('button', { name: 'Reproducir' }));
    expect(await screen.findByText('Elegí una voz.')).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });
});
