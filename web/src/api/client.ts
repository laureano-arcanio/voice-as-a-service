import createClient, { type Middleware } from 'openapi-fetch';
import type { paths } from './schema';

// Mismo origen: la cookie de sesion (httpOnly, path /api) viaja sola. El front no ve tokens.
// baseUrl absoluto del mismo origen (en el navegador da igual; en los tests, Request lo necesita).
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? '',
  credentials: 'same-origin',
  // fetch resuelto en cada pedido (no al cargar el modulo): permite mockearlo en los tests.
  fetch: (request) => globalThis.fetch(request),
});

type Handler = () => void;
let onUnauthorized: Handler | null = null;

/** Lo registra la app: un 401 fuera del login cierra la sesion y lleva a /login. */
export function setUnauthorizedHandler(handler: Handler | null) {
  onUnauthorized = handler;
}

const PUBLIC = ['/api/v1/auth/login', '/api/v1/auth/me', '/api/v1/auth/logout'];

const unauthorized: Middleware = {
  onResponse({ request, response }) {
    if (
      response.status === 401 &&
      !PUBLIC.some((p) => new URL(request.url, location.origin).pathname === p)
    ) {
      onUnauthorized?.();
    }
    return response;
  },
};

api.use(unauthorized);
