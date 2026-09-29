import { ApiError } from '@/api/errors';

const TITLES: Record<string, string> = {
  phone_numbers_limit: 'Límite de números del tier',
  number_assigned: 'El número ya es de otro cliente',
  number_unassigned: 'El número está libre: asignalo a un cliente primero',
};

/** Titulo de la notificacion para los 409/422 de numeros (el detail va de mensaje). */
export function numberErrorTitle(e: unknown): string | undefined {
  return e instanceof ApiError && e.code ? TITLES[e.code] : undefined;
}
