import type { Label } from '@/lib/labels';

export const CAMPAIGN_STATUS: Record<string, Label> = {
  draft: { label: 'Borrador', color: 'gray' },
  running: { label: 'Enviando', color: 'blue' },
  paused: { label: 'Pausada', color: 'yellow' },
  done: { label: 'Terminada', color: 'green' },
  cancelled: { label: 'Cancelada', color: 'gray' },
};

export const RECIPIENT_STATUS: Record<string, Label> = {
  pending: { label: 'Pendiente', color: 'gray' },
  sent: { label: 'Enviado', color: 'gray' },
  delivered: { label: 'Entregado', color: 'green' },
  read: { label: 'Leído', color: 'green' },
  replied: { label: 'Respondió', color: 'blue' },
  failed: { label: 'Falló', color: 'red' },
  skipped: { label: 'Salteado', color: 'gray' },
};

export const OPTOUT_SOURCE: Record<string, string> = {
  keyword: 'La pidió por WhatsApp',
  manual: 'Cargada a mano',
};

/** "9 a 20 h" */
export function formatWindow(start: number, end: number): string {
  return start === 0 && end === 24 ? 'Todo el día' : `${start} a ${end} h`;
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
