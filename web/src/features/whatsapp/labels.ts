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

/** Quién atiende el número (coexistencia): el agente o el dueño desde su app. */
export const WA_ATTENDANCE: Record<string, Label> = {
  agent: { label: 'Agente', color: 'blue' },
  owner: { label: 'Dueño', color: 'grape' },
};

/** Motivos de baja de Meta en status_reason (account_update PARTNER_REMOVED <motivo>). */
export const WA_INACTIVITY: Record<string, string> = {
  PRIMARY_INACTIVITY: 'el número dejó de abrirse en el teléfono por unos 14 días',
  COMPANION_INACTIVITY: 'la app de WhatsApp Business del teléfono dejó de estar activa',
};

export function waStatusReason(reason: string | null | undefined): string | null {
  if (!reason) return null;
  const why = Object.entries(WA_INACTIVITY).find(([code]) => reason.includes(code))?.[1];
  return why
    ? `Meta desconectó el número porque ${why}. Volvé a conectarlo con "Conectar WhatsApp".`
    : reason;
}

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
  own_app: 'App propia de Meta',
  coexistence: 'Coexistencia (app de WhatsApp Business)',
};

export const TEMPLATE_STATUS: Record<string, Label> = {
  APPROVED: { label: 'Aprobada', color: 'green' },
  PENDING: { label: 'En revisión', color: 'yellow' },
  IN_APPEAL: { label: 'En apelación', color: 'yellow' },
  REJECTED: { label: 'Rechazada', color: 'red' },
  PAUSED: { label: 'Pausada', color: 'yellow' },
  DISABLED: { label: 'Deshabilitada', color: 'gray' },
  // Borrada con envíos sin entregar: Meta la reintenta hasta 30 días.
  PENDING_DELETION: { label: 'Borrado pendiente', color: 'gray' },
};

export const TEMPLATE_CATEGORY: Record<string, string> = {
  UTILITY: 'Utilidad',
  MARKETING: 'Marketing',
  AUTHENTICATION: 'Autenticación',
};

/** WhatsApp Manager: ahí el cliente carga su medio de pago (Meta le cobra los mensajes). */
export const WA_MANAGER_URL = 'https://business.facebook.com/wa/manage/home/';
