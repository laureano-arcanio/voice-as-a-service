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
  cancelada: { label: 'Cancelada', color: 'gray' },
};

/** La saliente que nadie atendió o estaba ocupada: `fallida` con ended_reason no_answer o busy. */
export const CALL_UNANSWERED: Label = { label: 'No atendida', color: 'yellow' };

export function isUnanswered(c: { status?: string | null; ended_reason?: string | null }): boolean {
  return c.status === 'fallida' && (c.ended_reason === 'no_answer' || c.ended_reason === 'busy');
}

/**
 * Quién cortó una llamada finalizada, por `ended_reason` (lo deja el worker de voz, nunca el LLM): el cliente que
 * llamó o atendió, el equipo (una persona en la llamada o el botón Cortar llamada del panel), el agente (terminó
 * la conversación, fuera de tema o contestador) o el sistema (tope de minutos o de duración, el worker se cayó).
 * Sin motivo o con uno que no se conoce (llamadas viejas): null, queda "Finalizada" a secas.
 */
const ENDED_BY: Record<string, string> = {
  customer_hangup: 'el cliente',
  person_hangup: 'el equipo',
  hangup_by_user: 'el equipo',
  completed: 'el agente',
  off_topic: 'el agente',
  voicemail: 'el agente',
  external_error: 'el agente',
  external_agent_not_in_plan: 'el agente',
  max_duration: 'el sistema',
  quota_exhausted: 'el sistema',
  worker_stopped: 'el sistema',
  'parent process shutdown': 'el sistema',
  'room disconnected': 'el sistema',
  'job crashed': 'el sistema',
};

/** "Finalizada por el cliente / el equipo / el agente / el sistema"; "Finalizada" si no se sabe quién cortó. */
export function finishedLabel(endedReason: string | null | undefined): string {
  const by = endedReason ? ENDED_BY[endedReason] : undefined;
  return by ? `${CALL_STATUS.finalizada.label} por ${by}` : CALL_STATUS.finalizada.label;
}

export const CALL_MODE: Record<string, Label> = {
  saliente: { label: 'Saliente', color: 'gray' },
  entrante: { label: 'Entrante', color: 'gray' },
  directa: { label: 'Directa', color: 'gray' },
  prueba: { label: 'Prueba', color: 'gray' },
  web: { label: 'Link web', color: 'gray' },
  loadtest: { label: 'Loadtest', color: 'gray' },
  api: { label: 'API (texto)', color: 'gray' },
  whatsapp: { label: 'WhatsApp', color: 'gray' },
};

/** Quién atiende las entrantes (CallSummary.answered_by): el agente o el equipo (llamadas directas). */
export const ANSWERED_BY: Record<string, string> = {
  agent: 'Agente',
  team: 'Equipo',
};

/** Una entrante que atendió el equipo, sin agente (docs/features/EQUIPO_TELEFONIA.md). */
export function isTeamInbound(c: { mode?: string | null; answered_by?: string | null }): boolean {
  return c.mode === 'entrante' && c.answered_by === 'team';
}

/** Llamada de una persona del equipo, sin agente: una directa o una entrante que atendió el equipo. */
export function isPersonCall(c: { mode?: string | null; answered_by?: string | null }): boolean {
  return c.mode === 'directa' || isTeamInbound(c);
}

/**
 * Quién habló, en las llamadas sin agente: "Llamó: Ana" (directa) o "Atendió: Ana" (entrante del equipo); una
 * entrante del equipo que terminó sin que nadie atienda, "Atendió: nadie". Null si no es una llamada de persona,
 * o si la entrante todavía está sonando.
 */
export function callPerson(c: {
  mode?: string | null;
  answered_by?: string | null;
  user_name?: string | null;
  status?: string | null;
}): { verb: 'Llamó' | 'Atendió'; name: string } | null {
  if (c.mode === 'directa') return { verb: 'Llamó', name: c.user_name || 'alguien del equipo' };
  if (!isTeamInbound(c)) return null;
  if (c.user_name) return { verb: 'Atendió', name: c.user_name };
  return c.status && !isLiveStatus(c.status) ? { verb: 'Atendió', name: 'nadie' } : null;
}

export const WORKFLOW_STATUS: Record<string, Label> = {
  active: { label: 'Incompleto', color: 'yellow' },
  completed: { label: 'Completo', color: 'green' },
};

/** Tipo de una herramienta del cliente (docs/features/HERRAMIENTAS.md). */
export const CLIENT_TOOL_TYPE: Record<string, string> = {
  http: 'API',
  code: 'Código',
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
  number_suspended: 'Número suspendido',
};

/** Estado del plan pago (suscripcion). */
export const SUBSCRIPTION_STATUS: Record<string, Label> = {
  pending: { label: 'Esperando el pago', color: 'yellow' },
  active: { label: 'Activo', color: 'green' },
  past_due: { label: 'Vencido', color: 'red' },
  canceled: { label: 'Terminado', color: 'gray' },
};

export const PAYMENT_METHOD: Record<string, string> = {
  transfer: 'Transferencia',
  mercadopago: 'Mercado Pago',
};

export const TAX_CONDITION: Record<string, string> = {
  ri: 'Responsable inscripto',
  monotributo: 'Monotributo',
  exento: 'Exento',
  cf: 'Consumidor final',
};

// Pedidos a la API de inferencia (/api-requests).
export const API_REQUEST_STATUS: Record<string, Label> = {
  ok: { label: 'Completado', color: 'green' },
  cut: { label: 'Cortado', color: 'yellow' },
  error: { label: 'Error', color: 'red' },
  rejected: { label: 'Rechazado por el plan', color: 'yellow' },
};

export const API_KIND: Record<string, Label> = {
  llm: { label: 'LLM', color: 'gray' },
  stt: { label: 'Transcripción', color: 'gray' },
  tts: { label: 'Síntesis de voz', color: 'gray' },
};

// De dónde viene el pedido: la API de inferencia o una prueba de voz (no se descuenta del plan).
export const API_SOURCE: Record<string, Label> = {
  api: { label: 'API', color: 'gray' },
  voice_test_panel: { label: 'Prueba de voz · panel', color: 'blue' },
  voice_test_api: { label: 'Prueba de voz · API/MCP', color: 'blue' },
  voice_test_landing: { label: 'Prueba de voz · landing', color: 'blue' },
};

// Sistema (/admin/system): gravedad de una alerta y motivos de recorte del reloj de una GPU.
export const ALERT_SEVERITY: Record<string, Label> = {
  critical: { label: 'Crítica', color: 'red' },
  warning: { label: 'Aviso', color: 'yellow' },
};

export const GPU_THROTTLE: Record<string, Label> = {
  sw_power_cap: { label: 'Tope de potencia', color: 'gray' },
  sync_boost: { label: 'Sincronizada', color: 'gray' },
  hw_slowdown: { label: 'Recorte por hardware', color: 'red' },
  sw_thermal: { label: 'Recorte térmico', color: 'red' },
  hw_thermal: { label: 'Recorte térmico (hardware)', color: 'red' },
  hw_power_brake: { label: 'Freno de potencia', color: 'red' },
};
