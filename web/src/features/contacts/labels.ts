import type { Contact, OptoutChannel } from '@/api/types';
import type { Label } from '@/lib/labels';

export const CONTACT_SOURCE: Record<Contact['source'], string> = {
  manual: 'A mano',
  csv: 'CSV',
  api: 'API',
  campaign: 'Campaña',
  inbound: 'Entrante',
};

export const OPTOUT_CHANNEL: Record<OptoutChannel, string> = {
  whatsapp: 'WhatsApp',
  voice: 'Llamadas',
  all: 'Todos los canales',
};

export const OPTOUT_SOURCE: Record<string, string> = {
  keyword: 'Lo pidió por WhatsApp',
  outcome: 'Lo pidió en una llamada',
  manual: 'Cargada a mano',
};

export const ARCHIVED: Label = { label: 'Archivado', color: 'gray' };

/** Atributos de un contacto como texto: `deuda: 15000`. */
export function attributesText(attributes: Record<string, unknown>): string {
  return Object.entries(attributes)
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .join(' · ');
}

/** Valor de un campo de atributo (texto) a lo que guarda la API: numeros como numeros. */
export function parseAttribute(text: string): string | number {
  const t = text.trim();
  return /^-?\d+(\.\d+)?$/.test(t) && t.length < 16 ? Number(t) : t;
}
