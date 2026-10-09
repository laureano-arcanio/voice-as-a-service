/**
 * Reproduce audio PCM crudo (16 bits, mono, little-endian, 24 kHz: lo que devuelve el TTS con format=pcm) a medida que
 * llega, con Web Audio: cada bloque se programa a continuacion del anterior. Un `<audio>` no reproduce PCM en
 * streaming. El motor entrega un bloque chico (~80 ms) y despues bloques de ~2 s cada ~0,4 s: se espera un colchon
 * (`prebufferSeconds`) antes de empezar para que no haya un corte entre el primero y el segundo.
 */
export const PCM_SAMPLE_RATE = 24_000;
const START_DELAY = 0.05; // s entre el primer bloque programado y el "ahora"
const MIN_LEAD = 0.01; // un bloque que llega tarde se programa apenas despues de "ahora"

export interface PcmPlaybackOptions {
  /** Segundos de audio a juntar antes de empezar (o hasta que termine el stream). */
  prebufferSeconds?: number;
  /** Empezo a sonar. */
  onStart?: () => void;
  /** Termino de sonar todo el audio (no se llama al cortar con `stop`). */
  onEnd?: () => void;
}

export function int16ToFloat32(bytes: Uint8Array): Float32Array {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const out = new Float32Array(bytes.byteLength >> 1);
  for (let i = 0; i < out.length; i++) out[i] = view.getInt16(i * 2, true) / 32768;
  return out;
}

function concat(parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}

/** WAV (mono, 16 bits, 24 kHz) con ese PCM: para volver a escucharlo sin regenerarlo. */
export function wavFromPcm(pcm: Uint8Array): Uint8Array<ArrayBuffer> {
  const out = new Uint8Array(44 + pcm.length);
  const v = new DataView(out.buffer);
  const tag = (at: number, s: string) => [...s].forEach((c, i) => out.set([c.charCodeAt(0)], at + i));
  tag(0, 'RIFF');
  v.setUint32(4, 36 + pcm.length, true);
  tag(8, 'WAVEfmt ');
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);
  v.setUint16(22, 1, true);
  v.setUint32(24, PCM_SAMPLE_RATE, true);
  v.setUint32(28, PCM_SAMPLE_RATE * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  tag(36, 'data');
  v.setUint32(40, pcm.length, true);
  out.set(pcm, 44);
  return out;
}

export class PcmStreamPlayback {
  /** Todo el PCM, cuando termino de llegar; null si se corto antes con `stop`. Rechaza si el stream fallo. */
  readonly generated: Promise<Uint8Array | null>;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private sources = new Set<AudioBufferSourceNode>();
  private nextTime = 0;
  private startTime = 0;
  private received = 0; // muestras recibidas
  private started = false;
  private final = false;
  private stopped = false;
  private ended = false;

  constructor(
    private readonly ctx: AudioContext,
    stream: ReadableStream<Uint8Array>,
    private readonly opts: PcmPlaybackOptions = {},
  ) {
    this.generated = this.run(stream);
  }

  /** Segundos que ya sonaron. */
  elapsed(): number {
    return this.started ? Math.min(Math.max(this.ctx.currentTime - this.startTime, 0), this.total()) : 0;
  }

  /** Segundos de audio recibidos hasta ahora (la duracion total cuando `isFinal`). */
  total(): number {
    return this.received / PCM_SAMPLE_RATE;
  }

  /** Ya llego todo el audio. */
  isFinal(): boolean {
    return this.final;
  }

  /** Corta el audio y la descarga. */
  stop(): void {
    this.stopped = true;
    for (const s of this.sources) {
      s.onended = null;
      try {
        s.stop();
      } catch {
        /* ya habia terminado */
      }
    }
    this.sources.clear();
    void this.reader?.cancel().catch(() => undefined);
  }

  private async run(stream: ReadableStream<Uint8Array>): Promise<Uint8Array | null> {
    const prebuffer = this.opts.prebufferSeconds ?? 0.5;
    const reader = (this.reader = stream.getReader());
    const parts: Uint8Array[] = [];
    let carry: number | null = null; // un bloque puede cortar una muestra de 2 bytes
    let pending: Float32Array[] = [];
    let pendingSeconds = 0;
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done || this.stopped) break;
        let bytes = value;
        if (carry !== null) {
          const joined = new Uint8Array(bytes.length + 1);
          joined[0] = carry;
          joined.set(bytes, 1);
          bytes = joined;
          carry = null;
        }
        if (bytes.length % 2) {
          carry = bytes[bytes.length - 1];
          bytes = bytes.subarray(0, bytes.length - 1);
        }
        if (!bytes.length) continue;
        parts.push(bytes);
        const samples = int16ToFloat32(bytes);
        this.received += samples.length;
        if (this.started) {
          this.schedule(samples);
          continue;
        }
        pending.push(samples);
        pendingSeconds += samples.length / PCM_SAMPLE_RATE;
        if (pendingSeconds >= prebuffer) {
          this.begin(pending);
          pending = [];
        }
      }
      if (this.stopped) return null;
      if (!this.started && pending.length) this.begin(pending); // el audio entero era mas corto que el colchon
      this.final = true;
      this.maybeEnd();
      return concat(parts);
    } catch (e) {
      this.stop();
      if (this.stopped && e instanceof DOMException && e.name === 'AbortError') return null;
      throw e;
    } finally {
      this.reader = null;
      reader.releaseLock();
    }
  }

  private begin(blocks: Float32Array[]): void {
    this.started = true;
    this.startTime = this.nextTime = this.ctx.currentTime + START_DELAY;
    blocks.forEach((b) => this.schedule(b));
    this.opts.onStart?.();
  }

  private schedule(samples: Float32Array): void {
    const buffer = this.ctx.createBuffer(1, samples.length, PCM_SAMPLE_RATE);
    buffer.getChannelData(0).set(samples);
    const source = this.ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.ctx.destination);
    // Si el bloque llega despues de que se acabo lo anterior (GPU cargada), hay un corte: sigue apenas llega.
    const at = Math.max(this.nextTime, this.ctx.currentTime + MIN_LEAD);
    source.onended = () => {
      this.sources.delete(source);
      this.maybeEnd();
    };
    this.sources.add(source);
    source.start(at);
    this.nextTime = at + buffer.duration;
  }

  private maybeEnd(): void {
    if (this.final && this.started && this.sources.size === 0 && !this.ended && !this.stopped) {
      this.ended = true;
      this.opts.onEnd?.();
    }
  }
}
