// Lógica pura de `{{variable}}`: cuándo abrir la lista, filtrarla e insertar. La usan el editor del prompt
// (CodeMirror) y los campos cortos (Combobox), así los dos se comportan igual.

/** Misma regex que el backend (`app/conversation/variables.py`). */
const USED = /\{\{\s*([a-z][a-z0-9_]*(?:\.[A-Za-z0-9_]+)?)\s*\}\}/g;
const QUERY = /^[A-Za-z0-9_.]*$/;
const MAX_OPTIONS = 50;

export interface OpenMatch {
  /** Posición del `{{`. */
  from: number;
  /** Lo escrito después de `{{`. */
  query: string;
}

/** `{{` sin cerrar antes del cursor: `{{ a`, `{{a}}` o un salto de línea lo cierran. */
export function openAt(text: string, cursor: number): OpenMatch | null {
  const head = text.slice(0, cursor);
  const from = head.lastIndexOf('{{');
  if (from < 0) return null;
  const query = head.slice(from + 2);
  return QUERY.test(query) ? { from, query } : null;
}

const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Por prefijo y después por subcadena, sin acentos ni mayúsculas; hasta 50. Conserva el orden de entrada. */
export function filter<T extends { name: string }>(options: T[], query: string): T[] {
  const q = fold(query);
  if (!q) return options.slice(0, MAX_OPTIONS);
  const starts: T[] = [];
  const contains: T[] = [];
  for (const o of options) {
    const n = fold(o.name);
    if (n.startsWith(q)) starts.push(o);
    else if (n.includes(q)) contains.push(o);
  }
  return [...starts, ...contains].slice(0, MAX_OPTIONS);
}

export interface Insertion {
  text: string;
  /** Cursor después de lo insertado. */
  cursor: number;
  /** Rango de `text` original que se reemplazó, y con qué (para aplicar el cambio mínimo). */
  from: number;
  to: number;
  inserted: string;
}

/**
 * Reemplaza `text[from:cursor]` (el `{{` y lo tipeado) por `{{name}}` y se come un `}}` que ya estuviera
 * justo después del cursor. Con `partial` (un nombre con hueco, `fields.`) deja `{{fields.` abierto.
 */
export function insert(text: string, from: number, cursor: number, name: string, partial = false): Insertion {
  const inserted = partial ? `{{${name}` : `{{${name}}}`;
  const to = !partial && text.startsWith('}}', cursor) ? cursor + 2 : cursor;
  return {
    text: text.slice(0, from) + inserted + text.slice(to),
    cursor: from + inserted.length,
    from,
    to,
    inserted,
  };
}

/** Nombres usados en el texto, únicos y en orden de aparición. */
export function usedVariables(text: string): string[] {
  const seen = new Set<string>();
  for (const m of text.matchAll(USED)) seen.add(m[1]);
  return [...seen];
}

/** Cada `{{x}}` con su posición (para marcarla en el editor). */
export function variableRanges(text: string): { from: number; to: number; name: string }[] {
  return [...text.matchAll(USED)].map((m) => ({ from: m.index, to: m.index + m[0].length, name: m[1] }));
}
