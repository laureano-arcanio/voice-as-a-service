import { previewCsv } from '@/features/contacts/csv';

/** A quienes va la campaña: etiquetas de la agenda, contactos elegidos y/o un CSV. */
export interface Recipients {
  tags: string[];
  contactIds: string[];
  csv: string;
}

export const EMPTY_RECIPIENTS: Recipients = { tags: [], contactIds: [], csv: '' };

/** Cuantos contactos se suman seguro (los de las etiquetas se saben en el servidor). */
export function recipientsCount(r: Recipients): { rows: number; ids: number; tags: number } {
  return { rows: previewCsv(r.csv)?.rows.length ?? 0, ids: r.contactIds.length, tags: r.tags.length };
}

export function recipientsEmpty(r: Recipients): boolean {
  const n = recipientsCount(r);
  return n.rows + n.ids + n.tags === 0;
}

/** "2 etiquetas, 3 contactos y 40 filas del CSV". */
export function recipientsSummary(r: Recipients): string {
  const n = recipientsCount(r);
  const parts = [
    n.tags && `${n.tags} ${n.tags === 1 ? 'etiqueta' : 'etiquetas'}`,
    n.ids && `${n.ids} ${n.ids === 1 ? 'contacto elegido' : 'contactos elegidos'}`,
    n.rows && `${n.rows} ${n.rows === 1 ? 'fila' : 'filas'} del CSV`,
  ].filter(Boolean) as string[];
  if (parts.length === 0) return 'Todavía no elegiste a nadie.';
  return parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(', ')} y ${parts[parts.length - 1]}`;
}
