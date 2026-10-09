// Etiquetas y colores de estados. Colores: solo blue, green, yellow, red y gray
// (docs/DESIGN_GUIDELINE_APP.md, seccion 3); una categoria sin estado va en gray.

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
  rechazada: { label: 'Rechazada', color: 'yellow' },
};

export const CALL_MODE: Record<string, Label> = {
  saliente: { label: 'Saliente', color: 'gray' },
  entrante: { label: 'Entrante', color: 'gray' },
  prueba: { label: 'Prueba', color: 'gray' },
  loadtest: { label: 'Loadtest', color: 'gray' },
  api: { label: 'API (texto)', color: 'gray' },
  whatsapp: { label: 'WhatsApp', color: 'gray' },
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
  client_inactive: 'Cuenta en solo lectura',
  // Tope global de la plataforma (MAX_CONCURRENT_CALLS_GLOBAL): no es del plan del cliente.
  platform_busy: 'Plataforma al máximo de llamadas',
};
