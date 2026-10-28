// Una sola sesión para el panel y el teléfono del equipo (app/services/session_switch.py): cada host tiene su
// cookie, y para pasar de uno al otro el de origen da un pase de un solo uso que viaja en el fragmento
// (`#sesion=`). El destino lo cambia por su cookie antes de montar la app.
import { useMutation } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';

/** Salir de la página (aparte, para espiarlo en los tests: jsdom no navega). */
export const leave = {
  assign: (url: string) => window.location.assign(url),
  replace: (url: string) => window.location.replace(url),
};

const TOKEN_HASH = /^#sesion=([\w.-]+)$/;
const NO_SESSION_HASH = '#sin_sesion';
const SSO_KEY = 'atentina.phone.sso';

function clearHash() {
  window.history.replaceState(null, '', window.location.pathname + window.location.search);
}

/** El pase de la URL (y lo saca de la barra de direcciones), o null. */
export function takeSwitchToken(): string | null {
  const m = TOKEN_HASH.exec(window.location.hash);
  if (!m) return null;
  clearHash();
  return m[1]!;
}

/** Cambia el pase por la sesión de este host. Si venció o ya se usó, sigue sin sesión (pide la clave). */
export async function redeemSwitch(token: string): Promise<boolean> {
  const { response } = await api.POST('/api/v1/auth/switch/redeem', { body: { token } });
  return response.ok;
}

function ssoTried(on?: boolean): boolean {
  try {
    if (on === true) window.sessionStorage.setItem(SSO_KEY, '1');
    else if (on === false) window.sessionStorage.removeItem(SSO_KEY);
    return window.sessionStorage.getItem(SSO_KEY) === '1';
  } catch {
    return true; // sin almacenamiento no se intenta: evita un rebote sin fin
  }
}

/** Antes de montar el panel: si llega con un pase, abre la sesión. */
export async function bootPanelSession(): Promise<void> {
  const token = takeSwitchToken();
  if (token) await redeemSwitch(token).catch(() => false);
}

/**
 * Antes de montar el teléfono: con un pase abre la sesión; sin sesión (en su host), prueba una vez por pestaña con
 * la del panel (GET /auth/switch/start, que vuelve con el pase o con #sin_sesion). Devuelve false si se va.
 */
export async function bootPhoneSession(): Promise<boolean> {
  const token = takeSwitchToken();
  if (token) {
    if (await redeemSwitch(token).catch(() => false)) ssoTried(false);
    return true;
  }
  if (window.location.hash === NO_SESSION_HASH) {
    clearHash();
    ssoTried(true);
    return true;
  }
  if (window.location.pathname !== '/' || ssoTried()) return true;
  const me = await fetch('/api/v1/auth/me', { credentials: 'same-origin' }).catch(() => null);
  if (me?.ok) ssoTried(false);
  if (me?.status !== 401) return true;
  ssoTried(true);
  leave.replace('/api/v1/auth/switch/start?target=phone');
  return false;
}

/** Ir a la app del teléfono o volver al Teléfono del equipo del panel, con la misma sesión. */
export function useSwitchTo() {
  return useMutation({
    mutationFn: (target: 'phone' | 'panel') => unwrap(api.POST('/api/v1/auth/switch', { body: { target } })),
    onSuccess: ({ url }) => leave.assign(url),
  });
}
