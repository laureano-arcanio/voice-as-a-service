/**
 * "Ver como cliente" (docs/ADMIN_SOPORTE_PLAN.md): el cliente en el que entró un admin, por pestaña.
 * Mientras está, cada pedido a la API lleva el header X-Atentina-Client y el backend lo atiende como un
 * usuario de ese cliente (`me.role === 'client'`, `me.support`).
 */

export const SUPPORT_KEY = 'support:client';
export const SUPPORT_HEADER = 'X-Atentina-Client';

export function supportClientId(): string | null {
  try {
    return window.sessionStorage.getItem(SUPPORT_KEY);
  } catch {
    return null;
  }
}

export function setSupportClientId(id: string | null) {
  try {
    if (id) window.sessionStorage.setItem(SUPPORT_KEY, id);
    else window.sessionStorage.removeItem(SUPPORT_KEY);
  } catch {
    // modo privado: sin sessionStorage no se puede entrar como cliente
  }
}

/** URL que abre el panel de un cliente en otra pestaña: `noopener` no copia el sessionStorage, así que el cliente
 * (y el borrador de la marca, para la vista previa) viajan en el fragmento, que no llega al servidor. */
export function supportUrl(clientId: string, branding?: unknown): string {
  const params = new URLSearchParams({ ver: clientId });
  if (branding) params.set('marca', JSON.stringify(branding));
  return `/#${params.toString()}`;
}

/** Al arrancar: adopta el cliente y el borrador de `supportUrl` y limpia el fragmento. */
export function adoptSupportFromUrl(previewKey: string) {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const clientId = params.get('ver');
  if (!clientId) return;
  setSupportClientId(clientId);
  try {
    const marca = params.get('marca');
    if (marca) window.sessionStorage.setItem(previewKey, marca);
  } catch {
    // sin sessionStorage: sin vista previa
  }
  window.history.replaceState(null, '', window.location.pathname + window.location.search);
}
