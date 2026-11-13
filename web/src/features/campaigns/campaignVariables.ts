// Mapeo de las columnas del CSV de una campaña de llamadas a las variables del agente. Las columnas sin rol
// (nombre, telefono, email y notas) llegan a la conversación como variables con su nombre normalizado
// (app/services/contacts.py, `_data_columns`, y app/conversation/variables.py, `key`); acá se elige de qué
// columna sale cada variable que declara el agente y se reescribe la fila de encabezados del CSV antes de
// crearla. Una columna que ya caía en una variable que no se usa se quita, para que valga su default.
import type { VariableCatalog } from '@/components/variables';
import type { VariableSpec } from '@/features/agents/definition';
import { csvDelimiter, formatRows, parseRows, previewCsv } from '@/features/contacts/csv';

/** Las columnas que no son una variable de usuario (los roles de la agenda y los params de WhatsApp). */
export const NOT_VARIABLE = new Set(['nombre', 'telefono', 'email', 'params']);

/** Los datos del contacto de la agenda que llegan a la conversación. */
export const CONTACT_KEYS = new Set(['nombre', 'telefono', 'email']);

// Lo mismo que trae `GET /variables/catalog`, para poder avisar antes de que llegue.
const RESERVED = ['channel', 'today', 'now'];
const RESERVED_PREFIXES = ['call.', 'agent.', 'secrets.', 'fields.'];
const NAME_PATTERN = '^[a-z][a-z0-9_]{0,63}$';
const MAX_VARIABLES = 30;

/** El nombre de la variable de una columna: sin acentos ni mayúsculas, con `_` (`Fecha Vence` → `fecha_vence`). */
export function variableKey(header: string): string {
  return header
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 64);
}

function nameProblem(name: string, catalog?: VariableCatalog | null): string | null {
  const reserved = catalog?.reserved ?? RESERVED;
  const prefixes = catalog?.reserved_prefixes ?? RESERVED_PREFIXES;
  if (reserved.includes(name) || prefixes.some((p) => name.startsWith(p))) return 'es del sistema';
  const pattern = new RegExp(catalog?.name_pattern ?? NAME_PATTERN);
  if (!pattern.test(name)) return 'nombre inválido';
  return null;
}

export interface CsvColumn {
  /** Posición en la fila de encabezados. */
  index: number;
  header: string;
  /** Nombre normalizado con que llega a la conversación. */
  name: string;
  /** Puede alimentar una variable. */
  data: boolean;
  /** Por qué el backend la ignora (solo en las columnas de datos). */
  problem?: string;
}

/** Las columnas del CSV y qué hace el backend con cada una. */
export function csvColumns(csv: string, catalog?: VariableCatalog | null): CsvColumn[] {
  const preview = previewCsv(csv);
  if (!preview) return [];
  const seen = new Set<string>();
  const columns = preview.columns.map((col, index): CsvColumn => {
    const header = col.header.trim();
    const name = variableKey(header);
    const base: CsvColumn = { index, header, name, data: false };
    if (col.role !== 'ignored') return base;
    if (!name) return { ...base, problem: 'sin nombre' };
    if (NOT_VARIABLE.has(name)) return { ...base, problem: 'nombre, teléfono, email y params no son variables' };
    const problem = nameProblem(name, catalog);
    if (problem) return { ...base, problem };
    if (seen.has(name)) return { ...base, problem: 'repetida: llega la primera' };
    seen.add(name);
    return { ...base, data: true };
  });
  const limit = catalog?.limits.max_variables ?? MAX_VARIABLES;
  const total = columns.filter((c) => c.data).length;
  if (total > limit)
    for (const c of columns) if (c.data) c.problem = `más de ${limit} columnas de datos: la API rechaza el CSV`;
  return columns;
}

/** La columna que ya trae cada variable: la primera con el mismo nombre normalizado. */
export function defaultMapping(
  variables: { name: string }[],
  columns: CsvColumn[],
): Record<string, number> {
  const taken = new Set<number>();
  const out: Record<string, number> = {};
  for (const v of variables) {
    const col = columns.find((c) => c.data && c.name === v.name && !taken.has(c.index));
    if (!col) continue;
    out[v.name] = col.index;
    taken.add(col.index);
  }
  return out;
}

/**
 * De dónde sale cada variable: lo elegido por la persona (`overrides`, con `null` = usar el default o
 * vacía) o lo que ya traía el CSV (`defaults`). Solo las que tienen columna.
 */
export function variableMapping(
  names: string[],
  defaults: Record<string, number>,
  overrides: Record<string, number | null> = {},
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const name of names) {
    const pick = name in overrides ? overrides[name] : defaults[name];
    if (pick != null) out[name] = pick;
  }
  return out;
}

/** Columnas que se quitan: una que ya caía en una variable sin columna elegida (así vale su default). */
export function removedColumns(
  columns: CsvColumn[],
  mapping: Record<string, number>,
  expected: string[],
): Set<number> {
  const targets = new Set(Object.values(mapping));
  const out = new Set<number>();
  for (const name of expected) {
    if (mapping[name] != null) continue;
    const col = columns.find((c) => c.data && c.name === name && !targets.has(c.index));
    if (col) out.add(col.index);
  }
  return out;
}

/** El CSV con la fila de encabezados reescrita: cada columna mapeada toma el nombre de su variable. */
export function applyMapping(
  csv: string,
  columns: CsvColumn[],
  mapping: Record<string, number>,
  expected: string[],
): string {
  const rows = parseRows(csv);
  if (!rows.length) return csv;
  const removed = removedColumns(columns, mapping, expected);
  const entries = Object.entries(mapping);
  if (!removed.size && !entries.length) return csv;
  const byIndex = new Map(entries.map(([name, index]) => [index, name]));
  const next = rows.map((row, n) =>
    (n === 0 ? row.map((h, i) => byIndex.get(i) ?? h) : row).filter((_, i) => !removed.has(i)),
  );
  return formatRows(next, csvDelimiter(csv));
}

export interface MappingAlerts {
  /** Variables sin default ni columna: llegan vacías. */
  empty: string[];
  /** Columnas de datos que no van a ninguna variable: llegan igual con su nombre normalizado. */
  columnsLeft: CsvColumn[];
  /** Columnas que el backend ignora. */
  ignored: CsvColumn[];
  /** Cantidad de columnas de datos si pasa el tope de la API. */
  overLimit: number | null;
  /** Variables declaradas que los contactos de la agenda no traen. */
  agendaMissing: string[];
}

/** Los avisos del mapeo: ninguno bloquea (el CSV se puede crear igual). */
export function mappingAlerts({
  variables,
  columns,
  mapping,
  contactIds,
  catalog,
}: {
  variables: VariableSpec[];
  columns: CsvColumn[];
  mapping: Record<string, number>;
  contactIds: string[];
  catalog?: VariableCatalog | null;
}): MappingAlerts {
  const expected = variables.map((v) => v.name);
  const removed = removedColumns(columns, mapping, expected);
  const used = new Set(Object.values(mapping));
  const limit = catalog?.limits.max_variables ?? MAX_VARIABLES;
  const total = columns.filter((c) => c.data).length;
  return {
    empty: variables.filter((v) => !v.default.trim() && mapping[v.name] == null).map((v) => v.name),
    columnsLeft: columns.filter((c) => c.data && !used.has(c.index) && !removed.has(c.index)),
    ignored: columns.filter((c) => c.problem),
    overLimit: total > limit ? total : null,
    agendaMissing: contactIds.length ? expected.filter((n) => !CONTACT_KEYS.has(n)) : [],
  };
}
