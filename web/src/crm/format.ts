// Formatos y etiquetas del CRM. La API del CRM da las horas en UTC sin zona: se les agrega la Z.
import type { Label } from '@/lib/labels';
import type { ActivityKind, Campaign, ContactKind, MessageKind, MessageStatus, Stage } from './types';

const EMPTY = '–';

/** "2026-10-21T13:00:00" (UTC sin zona) -> Date. Con zona, se respeta. */
export function parseUtc(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const withZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(withZone);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Fecha y hora local: 21/10/2026 10:00. */
export function fmtDateTime(iso: string | null | undefined): string {
  const d = parseUtc(iso);
  if (!d) return EMPTY;
  return `${d.toLocaleDateString('es-AR')} ${d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })}`;
}

/** Fecha sola ("2026-10-21", sin zona: no se corre de dia) o la fecha local de un datetime. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return EMPTY;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (m) return `${Number(m[3])}/${Number(m[2])}/${m[1]}`;
  const d = parseUtc(iso);
  return d ? d.toLocaleDateString('es-AR') : EMPTY;
}

/** Hace cuanto, corto: "hoy", "ayer", "hace 5 d". */
export function fmtAgo(iso: string | null | undefined, now = new Date()): string {
  const d = parseUtc(iso);
  if (!d) return EMPTY;
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((startOf(now) - startOf(d)) / 86_400_000);
  if (days <= 0) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} d`;
}

/** Date -> "2026-10-21" en hora local (para DateInput). */
export function toIsoDay(d: Date | string | null): string | null {
  if (!d) return null;
  if (typeof d === 'string') return d.slice(0, 10);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** Hoy en hora local, "2026-10-21". */
export function todayIso(): string {
  return toIsoDay(new Date())!;
}

export const STAGES: Record<Stage, Label> = {
  nuevo: { label: 'Nuevo', color: 'gray' },
  contactado: { label: 'Contactado', color: 'blue' },
  seguimiento: { label: 'Seguimiento', color: 'blue' },
  respondio: { label: 'Respondió', color: 'green' },
  charla_agendada: { label: 'Charla agendada', color: 'green' },
  charla_hecha: { label: 'Charla hecha', color: 'green' },
  propuesta: { label: 'Propuesta', color: 'green' },
  piloto: { label: 'Piloto', color: 'green' },
  cliente: { label: 'Cliente', color: 'green' },
  sin_respuesta: { label: 'Sin respuesta', color: 'gray' },
  no_interesa: { label: 'No interesa', color: 'yellow' },
  descartado: { label: 'Descartado', color: 'red' },
};

export const STAGE_OPTIONS = (Object.keys(STAGES) as Stage[]).map((v) => ({
  value: v,
  label: STAGES[v].label,
}));

export const MESSAGE_STATUS: Record<MessageStatus, Label> = {
  draft: { label: 'Borrador', color: 'gray' },
  queued: { label: 'En cola', color: 'blue' },
  sent: { label: 'Enviado', color: 'green' },
  delivered: { label: 'Entregado', color: 'green' },
  bounced: { label: 'Rebotó', color: 'red' },
  complained: { label: 'Queja', color: 'red' },
  failed: { label: 'Falló', color: 'red' },
  canceled: { label: 'Cancelado', color: 'gray' },
  received: { label: 'Recibido', color: 'green' },
};

export const MESSAGE_STATUS_OPTIONS = (Object.keys(MESSAGE_STATUS) as MessageStatus[]).map((v) => ({
  value: v,
  label: MESSAGE_STATUS[v].label,
}));

export const MESSAGE_KIND: Record<MessageKind, string> = {
  first: 'Primer mail',
  follow_up: 'Seguimiento',
  other: 'Otro',
};

/** "Primer mail", "Seguimiento 2", "Respuesta". */
export function messageLabel(m: { kind: MessageKind; step?: number | null; direction?: string }): string {
  if (m.direction === 'in') return 'Respuesta';
  if (m.kind === 'follow_up' && m.step) return `Seguimiento ${m.step}`;
  return MESSAGE_KIND[m.kind];
}

export const MESSAGE_KIND_OPTIONS = (Object.keys(MESSAGE_KIND) as MessageKind[]).map((v) => ({
  value: v,
  label: MESSAGE_KIND[v],
}));

export const ACTIVITY_KIND: Record<ActivityKind, string> = {
  note: 'Nota',
  call: 'Llamada',
  meeting: 'Charla',
  linkedin: 'LinkedIn',
  task: 'Tarea',
  stage_change: 'Etapa',
};

export const CONTACT_KIND: Record<ContactKind, string> = {
  email: 'Email',
  phone: 'Teléfono',
  whatsapp: 'WhatsApp',
  linkedin: 'LinkedIn',
  form: 'Formulario',
};

export const CONTACT_LABEL: Record<string, string> = {
  persona: 'persona',
  area: 'área',
  atencion: 'atención',
};

export const LEAD_KIND_OPTIONS = [
  { value: 'cliente', label: 'Cliente' },
  { value: 'canal', label: 'Canal' },
];

/** Variables de las plantillas (crm/services/templates.py). */
export const TEMPLATE_VARS: { name: string; help: string }[] = [
  { name: 'saludo', help: '"Hola, Pablo:" si el ★ es una persona con nombre; si no, "Hola:"' },
  { name: 'nombre', help: 'Nombre de pila de la persona, o vacío' },
  { name: 'empresa', help: 'Nombre del lead' },
  { name: 'link', help: 'El sitio con las UTM de la campaña y del lead' },
];

export const CAMPAIGN_STATUS: Record<Campaign['status'], Label> = {
  draft: { label: 'Borrador', color: 'gray' },
  active: { label: 'Activa', color: 'blue' },
  done: { label: 'Terminada', color: 'green' },
};

export const CAMPAIGN_STATUS_OPTIONS = (Object.keys(CAMPAIGN_STATUS) as Campaign['status'][]).map((v) => ({
  value: v,
  label: CAMPAIGN_STATUS[v].label,
}));
