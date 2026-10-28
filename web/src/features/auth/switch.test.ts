import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { jsonResponse } from '@/test/render';
import { bootPanelSession, bootPhoneSession, leave } from './switch';

function mockFetch(me: number, redeem = 200) {
  const seen: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(new URL(String(input), 'http://localhost'));
      const path = new URL(req.url).pathname;
      seen.push(`${req.method} ${path}`);
      if (path === '/api/v1/auth/switch/redeem') return jsonResponse({}, redeem);
      if (path === '/api/v1/auth/me') return jsonResponse({}, me);
      return jsonResponse({}, 404);
    }),
  );
  return seen;
}

describe('pase de sesión entre el panel y el teléfono', () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.replaceState(null, '', '/');
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('con #sesion= lo cambia por la sesión y lo saca de la URL', async () => {
    const seen = mockFetch(401);
    window.history.replaceState(null, '', '/telefono#sesion=abc.def-ghi_jkl');
    await bootPanelSession();
    expect(seen).toEqual(['POST /api/v1/auth/switch/redeem']);
    expect(window.location.hash).toBe('');
  });

  it('el teléfono sin sesión prueba una vez con la del panel', async () => {
    const replace = vi.spyOn(leave, 'replace').mockImplementation(() => undefined);
    mockFetch(401);
    expect(await bootPhoneSession()).toBe(false);
    expect(replace).toHaveBeenCalledWith('/api/v1/auth/switch/start?target=phone');
    // Vuelve sin sesión del panel: pide la clave y no rebota otra vez.
    window.history.replaceState(null, '', '/#sin_sesion');
    expect(await bootPhoneSession()).toBe(true);
    expect(await bootPhoneSession()).toBe(true);
    expect(replace).toHaveBeenCalledTimes(1);
  });

  it('con sesión, o fuera de su host (/movil), no rebota', async () => {
    const replace = vi.spyOn(leave, 'replace').mockImplementation(() => undefined);
    mockFetch(200);
    expect(await bootPhoneSession()).toBe(true);
    mockFetch(401);
    window.history.replaceState(null, '', '/movil');
    expect(await bootPhoneSession()).toBe(true);
    expect(replace).not.toHaveBeenCalled();
  });
});
