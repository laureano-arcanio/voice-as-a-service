import type { HandoffArea } from '@/api/types';
import type { Label } from '@/lib/labels';

/** Los mensajes de un area (docs/DERIVACIONES_PLAN.md, 4.7), en el orden en que pasan. */
export const MESSAGE_FIELDS: { key: string; label: string; help: string }[] = [
  { key: 'transfer', label: 'Antes de transferir', help: 'Lo dice el agente al cliente antes de pasarlo.' },
  {
    key: 'whisper',
    label: 'Aviso a la persona del equipo',
    help: 'Lo escucha quien atiende, antes de que se conecte la llamada.',
  },
  {
    key: 'no_answer',
    label: 'Si nadie atiende',
    help: 'También si atiende un contestador, o si no hay línea o minutos libres.',
  },
  { key: 'busy', label: 'Si están ocupados', help: 'Cuando la persona rechaza la llamada o da ocupado.' },
  {
    key: 'after_hours',
    label: 'Fuera de horario',
    help: 'Cuando el cliente pide el área fuera de su horario.',
  },
  {
    key: 'resume',
    label: 'Cuando el agente vuelve',
    help: 'Si la persona del equipo corta y el agente retoma la llamada.',
  },
  {
    key: 'goodbye',
    label: 'Despedida',
    help: 'Si la persona del equipo corta y el agente se despide y corta.',
  },
];

export const STRATEGY_OPTIONS = [
  { value: 'sequential', label: 'En orden' },
  { value: 'round_robin', label: 'Rotativa' },
];

export const STRATEGY_HELP: Record<string, string> = {
  sequential: 'Siempre empieza por la primera persona de la lista y sigue en orden.',
  round_robin: 'Empieza por la siguiente a la última que recibió una derivación, para repartirlas.',
};

/** Estado de un area: inactiva, atiende ahora o fuera de horario. */
export function areaStatus(area: Pick<HandoffArea, 'active' | 'open_now'>): Label {
  if (!area.active) return { label: 'Inactiva', color: 'gray' };
  return area.open_now
    ? { label: 'Atiende ahora', color: 'green' }
    : { label: 'Fuera de horario', color: 'gray' };
}

/** Tecla de vuelta a la IA: 1 a 4 digitos o #, sin * (la toma la central de Anura) y distinta de 1. */
export function returnDigitsError(v: string): string | null {
  if (!/^[0-9#]{1,4}$/.test(v)) return 'De 1 a 4 dígitos o #, sin *.';
  if (v === '1') return 'El 1 es para atender la derivación: elegí otra tecla.';
  return null;
}
