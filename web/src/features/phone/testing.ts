// Ayudas de los tests del teléfono: un livekit-client falso (rooms y micrófono) y la API mockeada.
import { vi } from 'vitest';
import type { PlanFeatures } from '@/api/types';
import { jsonResponse } from '@/test/render';

type Handler = (...args: unknown[]) => void;

export class FakeRoom {
  static all: FakeRoom[] = [];
  handlers = new Map<string, Handler>();
  canPlaybackAudio = true;
  localParticipant = {
    identity: 'user-u-client',
    publishTrack: vi.fn(async () => undefined),
    publishDtmf: vi.fn(async () => undefined),
  };
  connect = vi.fn(async () => undefined);
  disconnect = vi.fn(async () => undefined);
  startAudio = vi.fn(async () => undefined);

  constructor() {
    FakeRoom.all.push(this);
  }

  on(event: string, fn: Handler) {
    this.handlers.set(event, fn);
    return this;
  }

  removeAllListeners() {
    this.handlers.clear();
  }

  emit(event: string, ...args: unknown[]) {
    this.handlers.get(event)?.(...args);
  }

  /** Un mensaje del worker en un tema de datos. */
  data(topic: string, body: unknown) {
    this.emit('dataReceived', new TextEncoder().encode(JSON.stringify(body)), undefined, undefined, topic);
  }

  static last(): FakeRoom {
    const r = FakeRoom.all.at(-1);
    if (!r) throw new Error('sin room');
    return r;
  }
}

export const fakeMic = {
  isMuted: false,
  mute: vi.fn(async () => undefined),
  unmute: vi.fn(async () => undefined),
  stop: vi.fn(),
};

/** Módulo falso de livekit-client: `vi.mock('livekit-client', () => fakeLivekit())`. */
export function fakeLivekit() {
  return {
    Room: FakeRoom,
    RoomEvent: {
      TrackSubscribed: 'trackSubscribed',
      TrackUnsubscribed: 'trackUnsubscribed',
      AudioPlaybackStatusChanged: 'audioPlaybackChanged',
      DataReceived: 'dataReceived',
      Disconnected: 'disconnected',
    },
    Track: { Kind: { Audio: 'audio' } },
    createLocalAudioTrack: vi.fn(async () => fakeMic),
  };
}

/** El navegador de los tests (jsdom) no trae getUserMedia. */
export function stubMediaDevices() {
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia: vi.fn() },
    configurable: true,
  });
}

export interface Seen {
  method: string;
  path: string;
  search: string;
  body?: unknown;
}

export const PLAN_OK: PlanFeatures = {
  client_id: 'c-1',
  tier_name: 'Sucursal',
  free: false,
  features: { direct_calls: { enabled: true, reason: null } },
};

export const PLAN_FREE: PlanFeatures = {
  client_id: 'c-1',
  tier_name: 'Free',
  free: true,
  features: {
    direct_calls: { enabled: false, reason: 'Está en los planes Mostrador, Sucursal y Red.' },
  },
};

/** fetch mockeado por "MÉTODO /ruta"; lo que no está, 404. Devuelve los pedidos vistos. */
export function mockApi(routes: Record<string, (body: unknown) => Response>) {
  const seen: Seen[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const body =
        req.method === 'GET'
          ? undefined
          : await req
              .clone()
              .json()
              .catch(() => undefined);
      seen.push({ method: req.method, path: url.pathname, search: url.search, body });
      const route = routes[`${req.method} ${url.pathname}`];
      return route ? route(body) : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return seen;
}
