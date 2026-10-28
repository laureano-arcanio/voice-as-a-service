import type { SiteDetailKind } from './types';

// Nombres de GA (en inglés) a los de la guía; lo que no está, tal cual.
export const CHANNELS: Record<string, string> = {
  Direct: 'Directo',
  Email: 'Email',
  'Organic Search': 'Búsqueda orgánica',
  'Paid Search': 'Búsqueda paga',
  'AI Assistant': 'Asistentes de IA',
  'Organic Social': 'Redes',
  'Paid Social': 'Redes pagas',
  'Organic Video': 'Video',
  Referral: 'Otros sitios',
  Display: 'Display',
  Unassigned: 'Sin asignar',
};
export const DEVICES: Record<string, string> = {
  desktop: 'Computadora',
  mobile: 'Celular',
  tablet: 'Tablet',
};

export const KINDS: Record<SiteDetailKind, string> = {
  channel: 'Canal',
  source: 'Fuente / medio',
  page: 'Página',
  city: 'Ciudad',
  device: 'Dispositivo',
};

export const int = (n: number) => n.toLocaleString('es-AR');
export const dayLabel = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;

export function duration(sec: number): string {
  const s = Math.round(sec);
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`;
}

export function itemLabel(kind: SiteDetailKind, value: string): string {
  if (kind === 'channel') return CHANNELS[value] ?? value;
  if (kind === 'device') return DEVICES[value] ?? value;
  if (kind === 'city' && value === '(not set)') return 'Sin dato';
  return value;
}
