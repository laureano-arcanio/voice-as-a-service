import { ApiError } from '@/api/errors';

const TITLES: Record<string, string> = {
  phone_numbers_limit: 'Límite de números del tier',
  number_assigned: 'El número ya es de otro cliente',
  number_unassigned: 'El número está libre: asignalo a un cliente primero',
  already_unlimited: 'El límite ya es ilimitado',
};

/** Titulo de la notificacion para los 409/422 de numeros (el detail va de mensaje). */
export function numberErrorTitle(e: unknown): string | undefined {
  return e instanceof ApiError && e.code ? TITLES[e.code] : undefined;
}

/** Campo del formulario "Atiende" al que corresponde un error del PATCH (el resto, a una notificación). */
export type AnsweringField =
  'answer_mode' | 'member_ids' | 'agent_id' | 'ring_seconds' | 'schedule' | 'team_fallback_message';

export function answeringErrorField(e: unknown): AnsweringField | undefined {
  if (!(e instanceof ApiError)) return undefined;
  switch (e.code) {
    case 'members_required':
    case 'invalid_members':
      return 'member_ids';
    case 'agent_required':
      return 'agent_id';
    case 'direct_calls_not_in_plan':
    case 'terms_pending':
      return 'answer_mode';
  }
  if (e.status !== 422) return undefined;
  const m = e.message;
  // Los 422 de pydantic traen el campo adelante ("ring_seconds: ..."); los de la API, solo el texto.
  if (/^ring_seconds\b|timbre/i.test(m)) return 'ring_seconds';
  if (/^team_fallback_message\b|mensaje/i.test(m)) return 'team_fallback_message';
  if (/^schedule\b|horario|franja|zona horaria|días|fecha/i.test(m)) return 'schedule';
  return undefined;
}
