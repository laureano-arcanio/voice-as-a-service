// SDK de Facebook y mensajes de Embedded Signup v4 (docs/WHATSAPP_PLAN.md 3.3).
// El SDK se carga recien al abrir el alta: no va en index.html (CSP: connect.facebook.net).

interface FbLoginResponse {
  status?: string;
  authResponse?: { code?: string } | null;
}

interface FbLoginOptions {
  config_id: string;
  response_type: 'code';
  override_default_response_type: boolean;
  extras: Record<string, unknown>;
}

export interface FacebookSdk {
  init(opts: { appId: string; autoLogAppEvents: boolean; xfbml: boolean; version: string }): void;
  login(cb: (response: FbLoginResponse) => void, opts: FbLoginOptions): void;
}

declare global {
  interface Window {
    FB?: FacebookSdk;
    fbAsyncInit?: () => void;
  }
}

/** El origen exacto de facebook.com o un subdominio. El ejemplo de Meta usa
 * endsWith('facebook.com'), que acepta evilfacebook.com. */
export function isFacebookOrigin(origin: string): boolean {
  try {
    const url = new URL(origin);
    if (url.protocol !== 'https:') return false;
    return url.hostname === 'facebook.com' || url.hostname.endsWith('.facebook.com');
  } catch {
    return false;
  }
}

/** Eventos de alta que la API acepta. */
export type SignupEvent = 'FINISH' | 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING' | 'FINISH_ONLY_WABA';

export type SignupMessage =
  | {
      kind: 'finish';
      event: SignupEvent;
      waba_id: string;
      phone_number_id: string;
      business_id: string | null;
    }
  | { kind: 'cancel'; step: string | null }
  | { kind: 'error'; message: string; code: string | null; sessionId: string | null }
  | { kind: 'unsupported'; event: string };

const FINISH_EVENTS: SignupEvent[] = [
  'FINISH',
  'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING',
  'FINISH_ONLY_WABA',
];
const DIGITS = /^\d{1,32}$/;

function str(v: unknown): string | null {
  if (typeof v === 'string' && v) return v;
  if (typeof v === 'number' && Number.isFinite(v)) return String(v);
  return null;
}

/** Interpreta un `message` del popup. null si no es de Embedded Signup (el SDK manda otros). */
export function parseSignupMessage(raw: unknown): SignupMessage | null {
  let obj: unknown = raw;
  if (typeof raw === 'string') {
    try {
      obj = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (!obj || typeof obj !== 'object') return null;
  const msg = obj as { type?: unknown; event?: unknown; data?: unknown };
  if (msg.type !== 'WA_EMBEDDED_SIGNUP') return null;
  const data = (msg.data && typeof msg.data === 'object' ? msg.data : {}) as Record<string, unknown>;
  const event = str(msg.event) ?? '';

  const errorMessage = str(data.error_message);
  if (errorMessage) {
    return {
      kind: 'error',
      message: errorMessage,
      code: str(data.error_code),
      sessionId: str(data.session_id),
    };
  }
  if (event === 'CANCEL') return { kind: 'cancel', step: str(data.current_step) };
  if ((FINISH_EVENTS as string[]).includes(event)) {
    const waba = str(data.waba_id);
    const pnid = str(data.phone_number_id) ?? '';
    const business = str(data.business_id);
    if (!waba || !DIGITS.test(waba)) {
      return {
        kind: 'error',
        message: 'Meta no devolvió la cuenta de WhatsApp Business.',
        code: null,
        sessionId: null,
      };
    }
    return {
      kind: 'finish',
      event: event as SignupEvent,
      waba_id: waba,
      phone_number_id: DIGITS.test(pnid) ? pnid : '',
      business_id: business && DIGITS.test(business) ? business : null,
    };
  }
  return { kind: 'unsupported', event };
}

const SDK_ID = 'facebook-jssdk';
let sdkPromise: Promise<FacebookSdk> | null = null;
let initializedFor: string | null = null;

/** Carga el SDK una vez y lo inicializa con la app (y la version de Graph) de la API. */
export function loadFacebookSdk(appId: string, version: string, locale: string): Promise<FacebookSdk> {
  const safeLocale = /^[a-z]{2}_[A-Z]{2}$/.test(locale) ? locale : 'en_US';
  const init = (fb: FacebookSdk) => {
    const key = `${appId}:${version}`;
    if (initializedFor !== key) {
      fb.init({ appId, autoLogAppEvents: true, xfbml: true, version });
      initializedFor = key;
    }
    return fb;
  };
  if (window.FB) return Promise.resolve(init(window.FB));
  if (!sdkPromise) {
    sdkPromise = new Promise<FacebookSdk>((resolve, reject) => {
      window.fbAsyncInit = () => {
        if (window.FB) resolve(window.FB);
        else reject(new Error('El SDK de Facebook cargó sin FB'));
      };
      if (document.getElementById(SDK_ID)) return;
      const script = document.createElement('script');
      script.id = SDK_ID;
      script.src = `https://connect.facebook.net/${safeLocale}/sdk.js`;
      script.async = true;
      script.defer = true;
      script.crossOrigin = 'anonymous';
      script.onerror = () => {
        sdkPromise = null;
        script.remove();
        reject(new Error('No se pudo cargar el SDK de Facebook (¿bloqueador de anuncios o sin conexión?).'));
      };
      document.body.appendChild(script);
    });
  }
  return sdkPromise.then(init);
}
