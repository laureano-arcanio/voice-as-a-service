import type { Campaign, CampaignChannel, CampaignContact } from '@/api/types';
import type { Label } from '@/lib/labels';

export const CHANNEL: Record<CampaignChannel, string> = {
  whatsapp: 'WhatsApp',
  voice: 'Llamadas',
};

export const CAMPAIGN_STATUS: Record<string, Label> = {
  draft: { label: 'Borrador', color: 'gray' },
  scheduled: { label: 'Programada', color: 'blue' },
  running: { label: 'En curso', color: 'blue' },
  paused: { label: 'Pausada', color: 'yellow' },
  done: { label: 'Terminada', color: 'green' },
  cancelled: { label: 'Cancelada', color: 'gray' },
};

/** Estado de un contacto dentro de la campaña. */
export const CONTACT_STATUS: Record<string, Label> = {
  pending: { label: 'Pendiente', color: 'gray' },
  in_progress: { label: 'En curso', color: 'blue' },
  retry: { label: 'Por reintentar', color: 'yellow' },
  done: { label: 'Terminado', color: 'green' },
  failed: { label: 'Falló', color: 'red' },
  skipped: { label: 'Salteado', color: 'gray' },
};

/** Resultado de un contacto: el de WhatsApp (el mas avanzado) o el de la llamada. */
export const CONTACT_RESULT: Record<string, Label> = {
  sent: { label: 'Enviado', color: 'gray' },
  delivered: { label: 'Entregado', color: 'green' },
  read: { label: 'Leído', color: 'green' },
  replied: { label: 'Respondió', color: 'blue' },
  answered: { label: 'Atendió', color: 'green' },
  no_answer: { label: 'No atendió', color: 'yellow' },
  busy: { label: 'Ocupado', color: 'yellow' },
  voicemail: { label: 'Contestador', color: 'yellow' },
  invalid: { label: 'Número inválido', color: 'red' },
  rejected: { label: 'Rechazó', color: 'gray' },
  failed: { label: 'Falló', color: 'red' },
};

/** Resultados que se pueden reintentar (los que `retry_on` acepta). */
export const RETRY_RESULTS = ['no_answer', 'busy', 'voicemail', 'failed'] as const;
export const RETRY_DEFAULT = [...RETRY_RESULTS];

export const PURPOSE: Record<string, string> = {
  comercial: 'Comercial',
  cobranza: 'Cobranza',
  turnos: 'Turnos',
  aviso: 'Aviso',
};

export const FOLLOWUP_STATUS: Record<string, string> = {
  pending: 'Pendientes',
  sent: 'Enviados',
  replied: 'Respondieron',
  failed: 'Fallaron',
  skipped: 'Salteados',
};

export const WEEKDAYS = [
  { value: 0, label: 'Lun' },
  { value: 1, label: 'Mar' },
  { value: 2, label: 'Mié' },
  { value: 3, label: 'Jue' },
  { value: 4, label: 'Vie' },
  { value: 5, label: 'Sáb' },
  { value: 6, label: 'Dom' },
];

/** Etiqueta del estado de la campaña: en WhatsApp "enviando" en vez de "en curso". */
export function statusLabel(c: Pick<Campaign, 'status' | 'channel'>): Label {
  const l = CAMPAIGN_STATUS[c.status] ?? { label: c.status, color: 'gray' };
  return c.status === 'running' && c.channel === 'whatsapp' ? { ...l, label: 'Enviando' } : l;
}

/** Que se muestra de un contacto: su resultado, o su estado si todavia no tiene. */
export function contactLabel(c: Pick<CampaignContact, 'status' | 'result'>): Label {
  if (c.result && CONTACT_RESULT[c.result]) return CONTACT_RESULT[c.result];
  return CONTACT_STATUS[c.status] ?? { label: c.status, color: 'gray' };
}

/** "Lun a vie", "Todos los días", "Lun, mié y vie". */
export function formatWeekdays(days: number[] | null | undefined): string {
  if (!days || days.length === 0 || days.length === 7) return 'Todos los días';
  const sorted = [...days].sort((a, b) => a - b);
  const names = sorted.map((d, i) => {
    const name = WEEKDAYS[d]?.label ?? String(d);
    return i === 0 ? name : name.toLowerCase();
  });
  const run = sorted.every((d, i) => i === 0 || d === sorted[i - 1] + 1);
  if (run && sorted.length > 2) return `${names[0]} a ${names[names.length - 1]}`;
  return names.length > 1 ? `${names.slice(0, -1).join(', ')} y ${names[names.length - 1]}` : names[0];
}

/** "9 a 20 h" */
export function formatWindow(start: number, end: number): string {
  return start === 0 && end === 24 ? 'Todo el día' : `${start} a ${end} h`;
}

/** "unos 45 min", "1 h 35 min". */
export function formatEta(minutes: number): string {
  if (minutes < 60) return `${Math.max(1, Math.round(minutes))} min`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m ? `${h} h ${m} min` : `${h} h`;
}

/** Porcentaje entero de a sobre b, o null si b es 0. */
export function pct(a: number, b: number): number | null {
  return b > 0 ? Math.round((a / b) * 100) : null;
}

/** El texto de la plantilla con los valores de un contacto (como lo ve el contacto). */
export function renderTemplate(body: string, params: string[]): string {
  return body.replace(/\{\{\s*(\d+)\s*\}\}/g, (m, n: string) => params[Number(n) - 1] ?? m);
}

/** Ayuda del formato de contactos, segun cuantas variables tiene la plantilla. */
export function csvHelp(vars: number): string {
  const cols = [
    'telefono',
    'nombre',
    ...Array.from({ length: Math.max(0, vars - 1) }, (_, i) => `dato${i + 2}`),
  ];
  return (
    `Una fila por contacto, con encabezado: ${cols.join(',')}. ` +
    (vars
      ? `Las columnas que no son el teléfono completan {{1}}${vars > 1 ? `..{{${vars}}}` : ''} en orden. `
      : '') +
    'Teléfonos de Argentina con código de área (351 555-1234) o con +54 9.'
  );
}

// Errores de Meta frecuentes en una plantilla, en palabras del negocio (el codigo lo ve el admin).
const META_ERRORS: Record<number, string> = {
  131026: 'El número no tiene WhatsApp o no se le pudo entregar',
  131047: 'Pasaron más de 24 h desde el último mensaje del contacto',
  131049: 'Meta no lo entregó para no saturar al contacto con mensajes de marketing',
  131050: 'El contacto dejó de recibir mensajes de marketing',
  131056: 'Demasiados mensajes seguidos al mismo número',
  130472: 'Meta no lo entregó (prueba de Meta con usuarios)',
  100: 'Meta rechazó el mensaje (número o datos inválidos)',
};

/** Texto del error de un contacto: el de Meta traducido si se conoce el codigo. */
export function recipientError(error: Record<string, unknown> | null | undefined): string {
  if (!error) return '';
  const code = typeof error.code === 'number' ? error.code : Number(error.code);
  return META_ERRORS[code] ?? String(error.message ?? '');
}
