import { ApiError, errorMessage } from '@/api/errors';
import { QUOTA_TITLES } from '@/lib/labels';

export interface CallErrorInfo {
  title: string;
  message: string;
  /** yellow: limite o falta algo (se resuelve esperando o pidiendo); red: error. */
  color: 'yellow' | 'red';
}

/** Titulo y mensaje para un error de POST /calls, segun el `code` de la API. */
export function callErrorInfo(error: unknown, isAdmin: boolean): CallErrorInfo {
  const code = error instanceof ApiError ? error.code : undefined;
  const status = error instanceof ApiError ? error.status : 0;
  if (code === 'no_caller_id')
    return {
      title: 'Sin número para salientes',
      message: isAdmin
        ? 'Asigná un número al cliente para hacer salientes.'
        : 'Tu cuenta no tiene un número propio y las salientes salen con uno. Pedinos un número; mientras tanto, probá el agente con el modo prueba.',
      color: 'yellow',
    };
  if (code === 'client_inactive')
    return {
      title: QUOTA_TITLES.client_inactive,
      message: isAdmin
        ? 'El cliente está inactivo: no hace ni recibe llamadas.'
        : 'Tu cuenta está inactiva: podés ver el historial, pero no hacer llamadas.',
      color: 'yellow',
    };
  if (status === 429)
    return {
      title: QUOTA_TITLES[code ?? ''] ?? 'Límite del plan',
      message: errorMessage(error),
      color: 'yellow',
    };
  return {
    title: status === 502 ? 'No se pudo iniciar la llamada' : 'Error',
    message: errorMessage(error),
    color: 'red',
  };
}
