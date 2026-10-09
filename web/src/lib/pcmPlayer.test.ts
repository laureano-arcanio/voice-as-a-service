import { describe, expect, it, vi } from 'vitest';
import { int16ToFloat32, PCM_SAMPLE_RATE, PcmStreamPlayback, wavFromPcm } from './pcmPlayer';

/** AudioContext minimo: guarda cuando se programa cada bloque y deja terminarlos a mano. */
class FakeContext {
  currentTime = 0;
  destination = {};
  scheduled: { at: number; duration: number; samples: Float32Array; stop: ReturnType<typeof vi.fn> }[] = [];
  private sources: { onended: (() => void) | null }[] = [];

  createBuffer(_channels: number, length: number, rate: number) {
    const data = new Float32Array(length);
    return { duration: length / rate, getChannelData: () => data };
  }

  createBufferSource() {
    const entry = { at: 0, duration: 0, samples: new Float32Array(0) as Float32Array, stop: vi.fn() };
    const source = {
      buffer: null as { duration: number; getChannelData: (n: number) => Float32Array } | null,
      onended: null as (() => void) | null,
      connect: vi.fn(),
      stop: entry.stop,
      start: (at: number) => {
        entry.at = at;
        entry.duration = source.buffer!.duration;
        entry.samples = source.buffer!.getChannelData(0);
        this.scheduled.push(entry);
      },
    };
    this.sources.push(source);
    return source;
  }

  /** Termina de sonar todo lo programado. */
  finishAll() {
    this.sources.forEach((s) => s.onended?.());
  }
}

const asCtx = (c: FakeContext) => c as unknown as AudioContext;

/** PCM de `seconds` con un valor constante (para distinguir bloques). */
function pcm(seconds: number, value = 1000): Uint8Array {
  const out = new Uint8Array(Math.round(seconds * PCM_SAMPLE_RATE) * 2);
  const v = new DataView(out.buffer);
  for (let i = 0; i < out.length / 2; i++) v.setInt16(i * 2, value, true);
  return out;
}

/** Un stream que entrega los bloques que se le dan a mano, uno por uno. */
function controlled() {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const stream = new ReadableStream<Uint8Array>({ start: (c) => (controller = c) });
  return {
    stream,
    push: async (chunk: Uint8Array) => {
      controller.enqueue(chunk);
      await new Promise((r) => setTimeout(r, 0));
    },
    close: async () => {
      controller.close();
      await new Promise((r) => setTimeout(r, 0));
    },
  };
}

describe('int16ToFloat32 y wavFromPcm', () => {
  it('convierte Int16 little-endian a [-1, 1)', () => {
    const bytes = new Uint8Array([0x00, 0x80, 0x00, 0x00, 0xff, 0x7f]); // -32768, 0, 32767
    const out = int16ToFloat32(bytes);
    expect([out[0], out[1]]).toEqual([-1, 0]);
    expect(out[2]).toBeCloseTo(32767 / 32768, 6);
  });

  it('arma un WAV con el encabezado del PCM', () => {
    const wav = wavFromPcm(pcm(1));
    const v = new DataView(wav.buffer);
    expect(String.fromCharCode(...wav.subarray(0, 4))).toBe('RIFF');
    expect(v.getUint32(24, true)).toBe(24000);
    expect(v.getUint16(22, true)).toBe(1);
    expect(v.getUint16(34, true)).toBe(16);
    expect(v.getUint32(40, true)).toBe(48000);
    expect(wav.length).toBe(44 + 48000);
  });
});

describe('PcmStreamPlayback', () => {
  it('espera el colchon antes de empezar y encadena los bloques sin huecos', async () => {
    const ctx = new FakeContext();
    const { stream, push, close } = controlled();
    const onStart = vi.fn();
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0.5, onStart });

    await push(pcm(0.08)); // el primer bloque del motor es de ~80 ms: no alcanza el colchon
    expect(onStart).not.toHaveBeenCalled();
    expect(ctx.scheduled).toHaveLength(0);

    ctx.currentTime = 0.45;
    await push(pcm(2)); // llega el bloque de 2 s: ahora si
    expect(onStart).toHaveBeenCalledTimes(1);
    expect(ctx.scheduled.map((s) => s.duration)).toEqual([0.08, 2]);
    expect(ctx.scheduled[0].at).toBeCloseTo(0.5, 5); // ahora + 50 ms
    expect(ctx.scheduled[1].at).toBeCloseTo(0.58, 5); // justo a continuacion

    await push(pcm(2));
    expect(ctx.scheduled[2].at).toBeCloseTo(2.58, 5);
    expect(player.total()).toBeCloseTo(4.08, 5);
    expect(player.isFinal()).toBe(false);

    await close();
    const all = await player.generated;
    expect(all!.length).toBe((0.08 + 2 + 2) * 48000);
    expect(player.isFinal()).toBe(true);
  });

  it('un bloque que llega tarde sigue apenas llega, sin programarse en el pasado', async () => {
    const ctx = new FakeContext();
    const { stream, push, close } = controlled();
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0.1 });
    await push(pcm(0.5));
    expect(ctx.scheduled[0].at).toBeCloseTo(0.05, 5);
    ctx.currentTime = 3; // la GPU se atraso: ya se acabo lo anterior
    await push(pcm(1));
    expect(ctx.scheduled[1].at).toBeCloseTo(3.01, 5);
    await close();
    await player.generated;
  });

  it('un audio mas corto que el colchon suena al terminar el stream', async () => {
    const ctx = new FakeContext();
    const { stream, push, close } = controlled();
    const onStart = vi.fn();
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0.5, onStart });
    await push(pcm(0.2));
    expect(onStart).not.toHaveBeenCalled();
    await close();
    await player.generated;
    expect(onStart).toHaveBeenCalledTimes(1);
    expect(ctx.scheduled).toHaveLength(1);
  });

  it('un bloque que corta una muestra de 2 bytes no pierde ni corre el audio', async () => {
    const ctx = new FakeContext();
    const { stream, push, close } = controlled();
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0 });
    const whole = pcm(0.01, 1234);
    await push(whole.subarray(0, 101)); // corta en medio de la muestra 50
    await push(whole.subarray(101));
    await close();
    const out = await player.generated;
    expect(out).toEqual(whole);
    const samples = ctx.scheduled.flatMap((s) => [...s.samples]);
    expect(samples).toHaveLength(whole.length / 2);
    expect(new Set(samples.map((x) => Math.round(x * 32768)))).toEqual(new Set([1234]));
  });

  it('avisa el fin cuando termino de llegar y de sonar, y no antes', async () => {
    const ctx = new FakeContext();
    const { stream, push, close } = controlled();
    const onEnd = vi.fn();
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0, onEnd });
    await push(pcm(1));
    ctx.finishAll(); // lo programado ya sono, pero el motor sigue generando
    expect(onEnd).not.toHaveBeenCalled();
    await push(pcm(1));
    await close();
    await player.generated;
    expect(onEnd).not.toHaveBeenCalled(); // quedan bloques sonando
    ctx.finishAll();
    expect(onEnd).toHaveBeenCalledTimes(1);
  });

  it('elapsed sigue al reloj del audio y no pasa del total', async () => {
    const ctx = new FakeContext();
    const { stream, push, close } = controlled();
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0 });
    expect(player.elapsed()).toBe(0);
    await push(pcm(2));
    ctx.currentTime = 1.05; // 1 s despues de empezar (empezo en 0,05)
    expect(player.elapsed()).toBeCloseTo(1, 5);
    ctx.currentTime = 99;
    expect(player.elapsed()).toBeCloseTo(2, 5);
    await close();
    await player.generated;
  });

  it('stop corta lo que suena y la descarga; generated queda en null y no hay onEnd', async () => {
    const ctx = new FakeContext();
    const { stream, push } = controlled();
    const onEnd = vi.fn();
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0, onEnd });
    await push(pcm(1));
    player.stop();
    expect(ctx.scheduled[0].stop).toHaveBeenCalled();
    expect(await player.generated).toBeNull();
    ctx.finishAll();
    expect(onEnd).not.toHaveBeenCalled();
  });

  it('si el stream falla, generated rechaza y lo que sonaba se corta', async () => {
    const ctx = new FakeContext();
    let controller!: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({ start: (c) => (controller = c) });
    const player = new PcmStreamPlayback(asCtx(ctx), stream, { prebufferSeconds: 0 });
    controller.enqueue(pcm(1));
    await new Promise((r) => setTimeout(r, 0));
    controller.error(new TypeError('network error'));
    await expect(player.generated).rejects.toThrow('network error');
    expect(ctx.scheduled[0].stop).toHaveBeenCalled();
  });
});
