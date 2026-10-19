// Vista previa del CSV de contactos en el navegador: las mismas reglas de columnas que la API
// (app/services/contacts.py, parse_csv). La API es la que carga y valida; esto solo muestra que va a entender.

export type ColumnRole = 'phone' | 'name' | 'email' | 'external_id' | 'tags' | 'attribute' | 'ignored';

export const ROLE_LABEL: Record<ColumnRole, string> = {
  phone: 'Teléfono',
  name: 'Nombre',
  email: 'Email',
  external_id: 'ID externo',
  tags: 'Etiquetas',
  attribute: 'Dato',
  ignored: 'Se ignora',
};

const ROLES: [Exclude<ColumnRole, 'attribute' | 'ignored'>, string[]][] = [
  ['phone', ['telefono', 'phone', 'numero', 'celular', 'whatsapp', 'wa_id', 'movil']],
  ['name', ['nombre', 'name']],
  ['email', ['email', 'mail', 'correo']],
  ['external_id', ['external_id', 'id_externo', 'idexterno', 'id']],
  ['tags', ['tags', 'etiquetas', 'tag', 'etiqueta']],
];

const strip = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '');
const headerKey = (h: string) =>
  strip(h)
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, '');
/** El nombre del atributo, como lo arma la API desde el encabezado. */
export const attributeKey = (h: string) =>
  strip(h)
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 64);

function delimiter(text: string): string {
  const first = text.split(/\r?\n/, 1)[0] ?? '';
  const count = (d: string) => first.split(d).length - 1;
  const best = [',', ';', '\t'].reduce((a, b) => (count(b) > count(a) ? b : a), ',');
  return count(best) > 0 ? best : ',';
}

/** Filas de un CSV (con comillas). Sin librerias: alcanza para mostrar la vista previa. */
export function parseRows(text: string): string[][] {
  const src = text.replace(/^\uFEFF/, '');
  if (!src.trim()) return [];
  const sep = delimiter(src);
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (quoted) {
      if (ch === '"' && src[i + 1] === '"') {
        cell += '"';
        i++;
      } else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === sep) {
      row.push(cell);
      cell = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && src[i + 1] === '\n') i++;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
    } else cell += ch;
  }
  row.push(cell);
  rows.push(row);
  return rows.filter((r) => r.some((c) => c.trim()));
}

export interface CsvPreview {
  /** Cada columna del encabezado y lo que la API va a hacer con ella. */
  columns: { header: string; role: ColumnRole }[];
  /** Filas de datos (sin el encabezado), todas. */
  rows: string[][];
  /** Por que no se puede cargar (sin columna de telefono), o null. */
  error: string | null;
}

export function previewCsv(text: string): CsvPreview | null {
  const all = parseRows(text);
  if (all.length === 0) return null;
  const [header, ...rows] = all;
  const used = new Set<string>();
  const columns = header.map((h) => {
    const key = headerKey(h);
    const found = ROLES.find(([role, names]) => !used.has(role) && names.includes(key));
    if (found) {
      used.add(found[0]);
      return { header: h, role: found[0] as ColumnRole };
    }
    return { header: h, role: (attributeKey(h) ? 'attribute' : 'ignored') as ColumnRole };
  });
  return {
    columns,
    rows,
    error: used.has('phone')
      ? null
      : 'Falta la columna del teléfono: poné un encabezado "telefono" (o celular, phone, whatsapp).',
  };
}
