// Turnstile invisible (interaction-only): un token por llamada. Como landing/src/scripts/turnstile.ts,
// con la site key que manda el server en los datos de la pagina.

interface Turnstile {
  render(container: HTMLElement, options: Record<string, unknown>): string;
  execute(widgetId: string): void;
  reset(widgetId: string): void;
}

declare global {
  interface Window {
    turnstile?: Turnstile;
  }
}

export class CaptchaError extends Error {}

const SCRIPT_URL = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
let loading: Promise<Turnstile> | null = null;
let widgetId: string | null = null;
let pending: { resolve: (token: string) => void; reject: (error: Error) => void } | null = null;

export function loadTurnstile(): Promise<Turnstile> {
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () =>
      window.turnstile ? resolve(window.turnstile) : reject(new CaptchaError('No se pudo cargar la verificación.'));
    script.onerror = () => {
      loading = null;
      reject(new CaptchaError('No se pudo cargar la verificación. Revisá tu conexión.'));
    };
    document.head.appendChild(script);
  });
  return loading;
}

function settle(token: string | null, error?: string) {
  const current = pending;
  pending = null;
  if (!current) return;
  if (token) current.resolve(token);
  else current.reject(new CaptchaError(error ?? 'No pudimos verificar que seas una persona.'));
}

export async function turnstileToken(siteKey: string): Promise<string> {
  const turnstile = await loadTurnstile();
  const container = document.getElementById('turnstile');
  if (!container) throw new CaptchaError('No se pudo cargar la verificación. Recargá la página.');
  const token = new Promise<string>((resolve, reject) => {
    pending = { resolve, reject };
  });
  if (widgetId === null) {
    widgetId = turnstile.render(container, {
      sitekey: siteKey,
      execution: 'execute',
      appearance: 'interaction-only',
      action: 'call_link',
      language: 'es',
      callback: (value: string) => settle(value),
      'error-callback': () => settle(null),
      'expired-callback': () => settle(null, 'La verificación venció. Volvé a intentar.'),
    });
  } else {
    turnstile.reset(widgetId);
  }
  turnstile.execute(widgetId);
  return token;
}
