import { UserFacingError } from "./errors";

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

const SCRIPT_URL = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
let loading: Promise<Turnstile> | null = null;
let widgetId: string | null = null;
let pending: { resolve: (token: string) => void; reject: (error: Error) => void } | null = null;

function load(): Promise<Turnstile> {
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => (window.turnstile ? resolve(window.turnstile) : reject(new UserFacingError("No se pudo cargar la verificación. Recargá la página.")));
    script.onerror = () => {
      loading = null;
      reject(new UserFacingError("No se pudo cargar la verificación. Revisá tu conexión."));
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
  else current.reject(new UserFacingError(error ?? "No pudimos verificar que seas una persona."));
}

export async function turnstileToken(): Promise<string> {
  const turnstile = await load();
  const container = document.getElementById("turnstile");
  if (!container) throw new UserFacingError("No se pudo cargar la verificación. Recargá la página.");
  const token = new Promise<string>((resolve, reject) => {
    pending = { resolve, reject };
  });
  if (widgetId === null) {
    widgetId = turnstile.render(container, {
      sitekey: import.meta.env.PUBLIC_TURNSTILE_SITE_KEY,
      execution: "execute",
      appearance: "interaction-only",
      action: "demo",
      language: "es",
      callback: (value: string) => settle(value),
      "error-callback": () => settle(null),
      "expired-callback": () => settle(null, "La verificación venció. Volvé a intentar."),
    });
  } else {
    turnstile.reset(widgetId);
  }
  turnstile.execute(widgetId);
  return token;
}
