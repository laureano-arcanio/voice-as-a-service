import type { HandoffArea } from '@/api/types';
import type { Label } from '@/lib/labels';

/**
 * Cuando aplica un mensaje: `call` en toda area de llamada; `rotation` si el area rota por WhatsApp de texto
 * (plantilla de rotacion); `notice` en un area que solo avisa por WhatsApp.
 */
export type MessageGroup = 'call' | 'rotation' | 'notice';

export interface MessageField {
  key: string;
  label: string;
  help: string;
  /** Donde se muestra: por defecto, en las de llamada. `notice` tambien lo usan las de aviso. */
  group?: MessageGroup | 'call+notice';
}

/** Los mensajes de un area (docs/features/EQUIPO_TELEFONIA.md), en el orden en que pasan. */
export const MESSAGE_FIELDS: MessageField[] = [
  { key: 'transfer', label: 'Antes de transferir', help: 'Lo dice el agente al cliente antes de pasarlo.' },
  {
    key: 'whisper',
    label: 'Aviso a la persona del equipo',
    help: 'Lo escucha quien atiende, antes de que se conecte la llamada.',
  },
  {
    key: 'no_answer',
    label: 'Mensaje si nadie atiende',
    help: 'También si atiende un contestador, o si no hay línea o minutos libres. En un área de aviso, si no se pudo avisar a nadie.',
    group: 'call+notice',
  },
  { key: 'busy', label: 'Si están ocupados', help: 'Cuando la persona rechaza la llamada o da ocupado.' },
  {
    key: 'after_hours',
    label: 'Fuera de horario',
    help: 'Cuando el cliente pide el área fuera de su horario.',
    group: 'call+notice',
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
  {
    key: 'notified',
    label: 'Después de avisar',
    help: 'Lo dice el agente a la persona cuando el aviso por WhatsApp salió.',
    group: 'notice',
  },
  {
    key: 'accepted',
    label: 'Cuando alguien acepta (a la persona)',
    help: 'Se lo escribe el agente a la persona cuando alguien del equipo toca Aceptar.',
    group: 'rotation',
  },
  {
    key: 'relay_failed',
    label: 'Si no llegó su mensaje (a la persona)',
    help: 'Cuando lo que escribe la persona no le pudo llegar a quien aceptó.',
    group: 'rotation',
  },
  {
    key: 'operator_ack',
    label: 'Al aceptar (a la persona del equipo)',
    help: 'Recibe la persona del equipo apenas toca Aceptar, antes de los datos del contacto.',
    group: 'rotation',
  },
  {
    key: 'operator_contact',
    label: 'Datos del contacto (a la persona del equipo)',
    help: 'Los datos que recibe la persona del equipo para responder desde su WhatsApp.',
    group: 'rotation',
  },
  {
    key: 'post_call_failed',
    label: 'Si falló el registro (a la persona del equipo)',
    help: 'Cuando la acción posterior a la conversación no se pudo confirmar.',
    group: 'rotation',
  },
  {
    key: 'tap_wait',
    label: 'Si toca Aceptar y aún se confirma',
    help: 'Respuesta a la persona del equipo mientras se confirma el registro.',
    group: 'rotation',
  },
  {
    key: 'tap_taken',
    label: 'Si ya la tomó otra persona',
    help: 'Respuesta a quien toca Aceptar cuando otra persona la tomó antes.',
    group: 'rotation',
  },
  {
    key: 'tap_closed',
    label: 'Si la solicitud ya se cerró',
    help: 'Respuesta a quien toca Aceptar sobre una solicitud cerrada.',
    group: 'rotation',
  },
];

/** Los mensajes que se muestran segun como entrega el area y si rota por WhatsApp de texto. */
export function messageFieldsFor(delivery: string, rotation: boolean): MessageField[] {
  return MESSAGE_FIELDS.filter((f) => {
    const group = f.group ?? 'call';
    if (delivery === 'whatsapp') return group === 'notice' || group === 'call+notice';
    if (group === 'notice') return false;
    return group === 'rotation' ? rotation : true;
  });
}

/** Lo que dicen la ayuda y el error de un mensaje que todavía no lleva datos de la persona (`pre_accept_*` de la API). */
export function preAcceptNote(variables: string[]): string {
  return `Todavía no lleva los datos de la persona: solo admite ${variables.map((v) => `{{${v}}}`).join(', ')}`;
}

/** Error de un mensaje de antes de aceptar con una variable que no admite; null si está bien. */
export function preAcceptError(text: string, variables: string[]): string | null {
  const used = [...text.matchAll(/\{\{\s*(\w+)\s*\}\}/g)].map((m) => m[1]!);
  return used.some((v) => !variables.includes(v)) ? `${preAcceptNote(variables)}.` : null;
}

/** Timbre por persona: entre 5 y 60 segundos. */
export function ringSecondsError(v: number | string): string | null {
  return typeof v === 'number' && v >= 5 && v <= 60 ? null : 'Entre 5 y 60 segundos';
}

export const DELIVERY_OPTIONS = [
  { value: 'call', label: 'Se llama' },
  { value: 'whatsapp', label: 'Solo aviso por WhatsApp' },
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
