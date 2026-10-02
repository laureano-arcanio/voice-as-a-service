import type { Label } from '@/lib/labels';

export const WA_STATUS: Record<string, Label> = {
  connected: { label: 'Conectado', color: 'green' },
  pending: { label: 'Pendiente', color: 'yellow' },
  disconnected: { label: 'Desconectado', color: 'red' },
};

export const WA_STATUS_HELP: Record<string, string> = {
  connected: 'Recibe y responde mensajes.',
  pending: 'Falta suscribir o registrar el número en Meta: usá "Reintentar registro".',
  disconnected: 'Meta rechazó el token o se quitó el acceso. Volvé a conectar con "Conectar WhatsApp".',
};

/** quality_rating de Meta. */
export const WA_QUALITY: Record<string, Label> = {
  GREEN: { label: 'Alta', color: 'green' },
  YELLOW: { label: 'Media', color: 'yellow' },
  RED: { label: 'Baja', color: 'red' },
  NA: { label: 'Sin datos', color: 'gray' },
  UNKNOWN: { label: 'Sin datos', color: 'gray' },
};

export const WA_SOURCE: Record<string, string> = {
  manual: 'Alta manual',
  embedded_signup: 'Conectado por el cliente',
  coexistence: 'Coexistencia (app de WhatsApp Business)',
};

export const TEMPLATE_STATUS: Record<string, Label> = {
  APPROVED: { label: 'Aprobada', color: 'green' },
  PENDING: { label: 'En revisión', color: 'yellow' },
  IN_APPEAL: { label: 'En apelación', color: 'yellow' },
  REJECTED: { label: 'Rechazada', color: 'red' },
  PAUSED: { label: 'Pausada', color: 'yellow' },
  DISABLED: { label: 'Deshabilitada', color: 'gray' },
};

export const TEMPLATE_CATEGORY: Record<string, string> = {
  UTILITY: 'Utilidad',
  MARKETING: 'Marketing',
  AUTHENTICATION: 'Autenticación',
};

/** WhatsApp Manager: ahí el cliente carga su medio de pago (Meta le cobra los mensajes). */
export const WA_MANAGER_URL = 'https://business.facebook.com/wa/manage/home/';
