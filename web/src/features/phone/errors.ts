import { ApiError, errorMessage } from '@/api/errors';
import { QUOTA_TITLES } from '@/lib/labels';
import type { CallProblem } from './context';

export const SUPPORT_REASON = 'Entrando como el cliente no se puede llamar ni atender.';

/** El micrófono no se pudo abrir: no hay, o el navegador no lo deja usar. */
export function micProblem(e: unknown): CallProblem {
  const name = e instanceof DOMException ? e.name : '';
  if (name === 'NotFoundError' || name === 'OverconstrainedError')
    return {
      title: 'No encontramos un micrófono',
      message: 'Conectá uno y volvé a intentar.',
      code: 'no_mic',
    };
  if (name === 'NotReadableError')
    return {
      title: 'El micrófono está en uso',
      message: 'Otra aplicación lo está usando. Cerrala y volvé a intentar.',
      code: 'mic_busy',
    };
  return {
    title: 'El micrófono está bloqueado',
    message:
      'El navegador no deja usarlo en esta página. Hacé clic en el candado de la barra de direcciones, Micrófono → Permitir, y volvé a intentar.',
    code: 'mic_denied',
  };
}

export const NO_BROWSER: CallProblem = {
  title: 'Este navegador no puede llamar',
  message: 'Abrí el panel en Chrome, Safari, Edge o Firefox.',
  code: 'no_webrtc',
};

const code = (e: unknown) => (e instanceof ApiError ? e.code : undefined);

/** El cliente no aceptó las condiciones que cubren las llamadas directas (403 terms_pending). */
function termsProblem(e: unknown): CallProblem {
  return { title: 'Falta aceptar las condiciones nuevas', message: errorMessage(e), code: 'terms_pending' };
}

/** Error al empezar una llamada (POST /direct-calls), salvo `opted_out`, que se confirma. */
export function startProblem(e: unknown): CallProblem {
  const c = code(e);
  switch (c) {
    case 'blocked_number':
      return {
        title: 'El número está bloqueado',
        message: 'Desbloquealo en Contactos, Números bloqueados, para llamarlo.',
        code: c,
      };
    case 'no_phone_number':
      return {
        title: 'No tenés un número para llamar',
        message: 'Hace falta un número asignado a tu cuenta.',
        code: c,
      };
    case 'direct_calls_not_in_plan':
      return { title: 'Tu plan no incluye llamadas directas', message: 'Podés mejorarlo en Plan.', code: c };
    case 'no_channel':
      return { title: 'Todas las líneas están ocupadas', message: 'Probá en unos minutos.', code: c };
    case 'support_read_only':
      return { title: 'No se puede llamar', message: SUPPORT_REASON, code: c };
    case 'terms_pending':
      return termsProblem(e);
    default:
      if (c && QUOTA_TITLES[c]) return { title: QUOTA_TITLES[c], message: errorMessage(e), code: c };
      return { title: 'No se pudo llamar', message: errorMessage(e), code: c };
  }
}

/** Error al volver a entrar o al abrir una llamada creada por API o MCP (POST /direct-calls/{id}/join). */
export function joinProblem(e: unknown): CallProblem {
  const c = code(e);
  if (c === 'not_your_call')
    return {
      title: 'La llamada es de otro usuario',
      message: 'Solo puede entrar quien la va a hablar: abrí el link con su usuario.',
      code: c,
    };
  if (c === 'call_not_active')
    return { title: 'La llamada terminó', message: 'La conversación queda en Conversaciones.', code: c };
  if (e instanceof ApiError && e.status === 404)
    return {
      title: 'No encontramos la llamada',
      message: 'Revisá el link o buscala en Conversaciones.',
      code: 'not_found',
    };
  if (c === 'support_read_only') return { title: 'No se puede entrar', message: SUPPORT_REASON, code: c };
  if (c === 'terms_pending') return termsProblem(e);
  return { title: 'No pudimos entrar a la llamada', message: errorMessage(e), code: c };
}

/** Atender: si otro la atendió primero, o dejó de sonar. */
export function answerProblem(e: unknown): CallProblem {
  const c = code(e);
  if (c === 'already_answered' || c === 'not_ringing' || (e instanceof ApiError && e.status === 404))
    return {
      title: 'La atendió otra persona',
      message: 'La llamada ya no te está sonando.',
      code: c ?? 'not_ringing',
    };
  if (c === 'support_read_only') return { title: 'No se puede atender', message: SUPPORT_REASON, code: c };
  if (c === 'terms_pending') return termsProblem(e);
  return { title: 'No se pudo atender', message: errorMessage(e), code: c };
}

/** Y si no se pudo conectar a la room (red, LiveKit). */
export function connectProblem(e: unknown): CallProblem {
  return { title: 'No pudimos conectar la llamada', message: errorMessage(e), code: 'connect_failed' };
}
