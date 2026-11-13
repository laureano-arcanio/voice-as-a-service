import { useCallback, useMemo, useState } from 'react';
import type { Definition } from '@/api/types';
import { isSystemVariable, useVariableCatalog, usedVariables } from '@/components/variables';

// Valores de prueba de un agente (los "Test Inputs"/"dynamic_variable_placeholders" de Retell y ElevenLabs):
// una fila por variable declarada o usada, prellenada con su default, y las que se agreguen a mano. Viajan
// como `variables` en POST /conversations y POST /calls (sin teléfono). Se recuerdan por agente en
// sessionStorage. La tabla es `TestVariables.tsx`; T10 reutiliza los dos.

/** Una variable que el agente puede ver: la declarada (con su default) o la usada sin declarar. */
export interface TestVariable {
  name: string;
  default: string;
  description: string;
}

/** Una fila de la tabla: el nombre y el valor que se manda. Un nombre vacío no viaja. */
export interface TestValueRow {
  name: string;
  value: string;
}

const obj = (x: unknown): Record<string, unknown> =>
  x && typeof x === 'object' && !Array.isArray(x) ? (x as Record<string, unknown>) : {};
const str = (x: unknown): string => (typeof x === 'string' ? x : x == null ? '' : String(x));

/** Las variables de la definición, en orden: declaradas primero y después las usadas sin declarar. */
export function testVariableNames(
  definition: Definition,
  catalog: Parameters<typeof isSystemVariable>[1],
): TestVariable[] {
  const declared = (Array.isArray(definition.variables) ? definition.variables : []).map((raw) => {
    const v = obj(raw);
    return { name: str(v.name), default: str(v.default), description: str(v.description) };
  });
  const analysis = obj(definition.analysis);
  const text = [str(definition.prompt), str(definition.first_message), str(analysis.instructions)].join('\n');
  const out = declared.filter((v) => v.name);
  for (const name of usedVariables(text)) {
    if (isSystemVariable(name, catalog) || out.some((v) => v.name === name)) continue;
    out.push({ name, default: '', description: '' });
  }
  return out;
}

/** La fila de `name` en lo guardado, si está. */
const stored = (rows: TestValueRow[], name: string) => rows.find((r) => r.name === name);

/**
 * Las filas de la tabla: las de la definición (con el valor guardado o el default) y después las que se
 * agregaron a mano. `always` son las que tienen que estar aunque el agente no las use (T10: `motivo`).
 */
export function testRows(
  names: TestVariable[],
  saved: TestValueRow[],
  always: { name: string; description?: string }[] = [],
): TestValueRow[] {
  const all = [...names];
  for (const a of always)
    if (!all.some((v) => v.name === a.name))
      all.push({ name: a.name, default: '', description: a.description ?? '' });
  const rows = all.map((v) => ({ name: v.name, value: stored(saved, v.name)?.value ?? v.default }));
  for (const r of saved) {
    // Las que se agregaron a mano (también una fila vacía recién agregada).
    if (!all.some((v) => v.name === r.name)) rows.push({ name: r.name, value: r.value });
  }
  return rows;
}

/** Lo que viaja como `variables`: las filas con nombre. */
export function testVariables(rows: TestValueRow[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const r of rows) if (r.name.trim()) out[r.name.trim()] = r.value;
  return out;
}

const storageKey = (key: string) => `test-variables:${key}`;

function read(key: string): TestValueRow[] {
  try {
    const raw = window.sessionStorage.getItem(storageKey(key));
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    return Array.isArray(parsed)
      ? parsed.map((r) => ({ name: str(obj(r).name), value: str(obj(r).value) }))
      : [];
  } catch {
    return [];
  }
}

function write(key: string, rows: TestValueRow[]) {
  try {
    window.sessionStorage.setItem(storageKey(key), JSON.stringify(rows));
  } catch {
    // sin sessionStorage (modo privado): el valor vale para esta pantalla.
  }
}

/** Valores de prueba de un agente, recordados en sessionStorage. `key` es el agente (o la campaña). */
export function useTestVariables(
  key: string,
  definition: Definition,
  always: { name: string; description?: string }[] = [],
) {
  const catalog = useVariableCatalog().data;
  const names = useMemo(() => testVariableNames(definition, catalog), [definition, catalog]);
  const alwaysKey = JSON.stringify(always);
  // Lo editado, por clave: cambiar de agente no necesita un efecto (se lee lo suyo).
  const [edited, setEdited] = useState<Record<string, TestValueRow[]>>({});
  const saved = edited[key] ?? read(key);
  const rows = useMemo(
    () => testRows(names, saved, always),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `always` llega como array nuevo
    [names, saved, alwaysKey],
  );
  const setRows = useCallback(
    (next: TestValueRow[]) => {
      setEdited((prev) => ({ ...prev, [key]: next }));
      write(key, next);
    },
    [key],
  );
  const variables = useMemo(() => testVariables(rows), [rows]);
  return { names, rows, variables, setRows };
}
