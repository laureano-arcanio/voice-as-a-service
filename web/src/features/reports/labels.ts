import type { Channel } from './types';

export const CHANNEL_LABEL: Record<Channel, string> = {
  voice: 'Teléfono',
  whatsapp: 'WhatsApp',
  web: 'Web',
};

/** Como terminan las llamadas (GET /reports/calls, `ended`). */
export const ENDED_REASON: Record<string, string> = {
  customer_hangup: 'Cortó el cliente',
  agent_end: 'Terminó el agente',
  off_topic: 'Fuera de tema',
  hangup_by_user: 'Cortada desde el panel',
  blocked_number: 'Número bloqueado',
  rejected: 'Rechazada',
  failed: 'Falló',
  other: 'Otro',
};

/** Motivos de no contacto de las campañas. */
export const NO_CONTACT_REASON: Record<string, string> = {
  busy: 'Ocupado',
  no_answer: 'No atiende',
  voicemail: 'Contestador',
  invalid: 'Número inválido',
  failed: 'Falló',
  other: 'Otro',
  ocupado: 'Ocupado',
  no_atiende: 'No atiende',
  contestador: 'Contestador',
  invalido: 'Número inválido',
  fallido: 'Falló',
  otro: 'Otro',
};

/** Rechazos por limite del plan (operacion del admin). */
export const REJECT_REASON: Record<string, string> = {
  concurrency_limit: 'Tope de llamadas simultáneas',
  inbound_minutes: 'Sin minutos entrantes',
  outbound_minutes: 'Sin minutos salientes',
  client_inactive: 'Cliente inactivo',
  number_suspended: 'Número suspendido',
  blocked_number: 'Número bloqueado',
};

export const ALERT_KIND: Record<string, { label: string; color: string }> = {
  near_quota: { label: 'Cerca del cupo', color: 'yellow' },
  inactive: { label: 'Inactivo', color: 'gray' },
};

export const label = (map: Record<string, string>, key: string | null | undefined) =>
  key ? (map[key] ?? key) : '–';
