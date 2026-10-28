import { previewCsv } from '@/features/contacts/csv';

/** A quienes va la campaña: contactos elegidos de la agenda y/o un CSV. */
export interface Recipients {
  contactIds: string[];
  csv: string;
}

export const EMPTY_RECIPIENTS: Recipients = { contactIds: [], csv: '' };

/** Cuantos contactos se suman. */
export function recipientsCount(r: Recipients): { rows: number; ids: number } {
  return { rows: previewCsv(r.csv)?.rows.length ?? 0, ids: r.contactIds.length };
}

export function recipientsEmpty(r: Recipients): boolean {
  const n = recipientsCount(r);
  return n.rows + n.ids === 0;
}

/** "3 contactos elegidos y 40 filas del CSV". */
export function recipientsSummary(r: Recipients): string {
  const n = recipientsCount(r);
  const parts = [
    n.ids && `${n.ids} ${n.ids === 1 ? 'contacto elegido' : 'contactos elegidos'}`,
    n.rows && `${n.rows} ${n.rows === 1 ? 'fila' : 'filas'} del CSV`,
  ].filter(Boolean) as string[];
  if (parts.length === 0) return 'Todavía no elegiste a nadie.';
  return parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(', ')} y ${parts[parts.length - 1]}`;
}
