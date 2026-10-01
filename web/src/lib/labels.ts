// Etiquetas y colores de estados (como static/common.js del dashboard viejo).

export interface Label {
  label: string;
  color: string;
}

export const CALL_STATUS: Record<string, Label> = {
  pendiente: { label: 'Pendiente', color: 'gray' },
  sonando: { label: 'Sonando', color: 'blue' },
  en_curso: { label: 'En curso', color: 'blue' },
  finalizada: { label: 'Finalizada', color: 'green' },
  fallida: { label: 'Fallida', color: 'red' },
  rechazada: { label: 'Rechazada', color: 'orange' },
};

export const CALL_MODE: Record<string, Label> = {
  saliente: { label: 'Saliente', color: 'navy' },
  entrante: { label: 'Entrante', color: 'navy' },
  prueba: { label: 'Prueba', color: 'amber' },
  loadtest: { label: 'Loadtest', color: 'amber' },
  api: { label: 'API (texto)', color: 'gray' },
  whatsapp: { label: 'WhatsApp', color: 'green' },
};

export const WORKFLOW_STATUS: Record<string, Label> = {
  active: { label: 'Incompleto', color: 'yellow' },
  completed: { label: 'Completo', color: 'green' },
};

export const ENGINE: Record<string, string> = {
  classic: 'Clásico',
  structured: 'Estructurado',
};

export const LIVE_STATUSES = ['pendiente', 'sonando', 'en_curso'];

export function isLiveStatus(status: string | null | undefined): boolean {
  return !!status && LIVE_STATUSES.includes(status);
}

/** Motivos del 429 de POST /calls. */
export const QUOTA_TITLES: Record<string, string> = {
  concurrency_limit: 'Tope de llamadas simultáneas',
  inbound_minutes: 'Sin minutos entrantes este mes',
  outbound_minutes: 'Sin minutos salientes este mes',
  client_inactive: 'Cliente inactivo',
};
