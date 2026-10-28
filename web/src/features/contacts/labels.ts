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
