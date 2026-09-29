import type { PhoneNumber } from '@/api/types';

// Carga masiva: el texto pegado (uno por linea o separados por coma/punto y coma) a
// numeros, con la misma normalizacion que el server (app/services/calls.py normalize_e164).

export const MAX_BULK = 1000;

const E164 = /^\+\d{8,15}$/;

/** Tokens no vacios del textarea, en orden. Espacios y guiones dentro de un numero se respetan. */
export function splitNumbers(text: string): string[] {
  return text
    .split(/[\n\r,;]+/)
    .map((t) => t.trim())
    .filter(Boolean);
}

/** Saca espacios, parentesis, guiones y puntos; null si no queda un E.164 valido. */
export function normalizeE164(raw: string): string | null {
  const n = raw.replace(/[\s()\-.]/g, '');
  return E164.test(n) ? n : null;
}

export interface BulkPreview {
  /** Lo que se manda al server, tal cual (el server normaliza y reporta). */
  tokens: string[];
  valid: number;
  invalid: string[];
  duplicated: string[];
  tooMany: boolean;
}

/** Vista previa antes de cargar: cuantos son validos, invalidos y repetidos en el texto. */
export function previewNumbers(text: string): BulkPreview {
  const tokens = splitNumbers(text);
  const seen = new Set<string>();
  const invalid: string[] = [];
  const duplicated: string[] = [];
  let valid = 0;
  for (const t of tokens) {
    const n = normalizeE164(t);
    if (!n) invalid.push(t);
    else if (seen.has(n)) duplicated.push(t);
    else {
      seen.add(n);
      valid++;
    }
  }
  return { tokens, valid, invalid, duplicated, tooMany: tokens.length > MAX_BULK };
}

/** Filtra por numero ignorando espacios y signos. */
export function matchesNumber(n: Pick<PhoneNumber, 'e164' | 'label'>, q: string): boolean {
  const digits = q.replace(/\D/g, '');
  if (digits) return n.e164.includes(digits);
  const t = q.trim().toLowerCase();
  return !t || n.label.toLowerCase().includes(t);
}

/** "1 número" / "3 números". */
export function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}
