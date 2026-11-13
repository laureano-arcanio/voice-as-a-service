import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { components } from '@/api/schema';

export type VariableCatalog = components['schemas']['VariableCatalogOut'];
/** Dónde se escribe la variable: decide cuáles del sistema se ofrecen (`applies_to` del catálogo). */
export type VariableContext = 'prompt' | 'first_message' | 'analysis' | 'handoff' | 'tool';
/** Variable declarada en la definición (`variables`), en el orden de la lista. */
export interface DeclaredVariable {
  name: string;
  description?: string | null;
}
/** Variable que otra fuente asigna (el `assign` de una herramienta o del pre-call, un dato del análisis). */
export type ExtraVariable = string | DeclaredVariable;
export type VariableKind = 'system' | 'declared' | 'extra';

export interface VariableOption {
  name: string;
  kind: VariableKind;
  description: string;
  example: string;
  /** El nombre lleva un hueco (`fields.<campo>`): se inserta solo el prefijo, sin cerrar `}}`. */
  partial: boolean;
  /** Lo que se escribe tras `{{` (el nombre, o el prefijo si `partial`). */
  insertName: string;
}

export interface VariableSources {
  catalog?: VariableCatalog | null;
  declared?: DeclaredVariable[];
  extra?: ExtraVariable[];
  field: VariableContext;
}

export const KIND_LABEL: Record<VariableKind, string> = {
  system: 'sistema',
  declared: 'declarada',
  extra: 'asignada',
};

export const UNKNOWN_HINT =
  'Sin fuente declarada: puede venir del pre-call o de una herramienta. Si nadie la asigna, queda vacía.';

export const catalogKey = ['variables', 'catalog'] as const;

/** Catálogo de variables del sistema (igual para todos los clientes: se guarda una hora). */
export function useVariableCatalog(enabled = true) {
  return useQuery({
    queryKey: catalogKey,
    queryFn: () => unwrap(api.GET('/api/v1/variables/catalog')),
    staleTime: 60 * 60 * 1000,
    enabled,
  });
}

const PLACEHOLDER = /<[^>]*>$/;
const prefixOf = (name: string) => name.slice(0, name.search(PLACEHOLDER));

function normalizeExtra(item: ExtraVariable): DeclaredVariable {
  return typeof item === 'string' ? { name: item } : item;
}

/**
 * Lo que ofrece un campo: declaradas, después las de `extra` y al final las del sistema que aplican al
 * campo. Sin repetidos (gana la del sistema).
 */
export function variableOptions({
  catalog,
  declared = [],
  extra = [],
  field,
}: VariableSources): VariableOption[] {
  const system = (catalog?.system ?? []).filter((v) => v.applies_to.includes(field));
  const taken = new Set(system.map((v) => v.name));
  const out: VariableOption[] = [];
  const add = (items: DeclaredVariable[], kind: 'declared' | 'extra') => {
    for (const v of items) {
      const name = v.name?.trim();
      if (!name || taken.has(name)) continue;
      taken.add(name);
      out.push({
        name,
        kind,
        description: v.description ?? '',
        example: '',
        partial: false,
        insertName: name,
      });
    }
  };
  add(declared, 'declared');
  add(extra.map(normalizeExtra), 'extra');
  for (const v of system) {
    const partial = PLACEHOLDER.test(v.name);
    out.push({
      name: v.name,
      kind: 'system',
      description: v.description,
      example: v.example,
      partial,
      insertName: partial ? prefixOf(v.name) : v.name,
    });
  }
  return out;
}

export interface Resolved {
  kind: 'system' | 'declared' | 'unknown';
  description: string;
  /** Es una del sistema que este campo no admite (p. ej. `{{secrets.X}}` en el prompt). */
  misplaced: boolean;
}

/** Qué es `{{name}}` en este campo, para el color y el aviso. */
export function resolveVariable(name: string, sources: VariableSources): Resolved {
  const { catalog, declared = [], extra = [], field } = sources;
  const sys = (catalog?.system ?? []).find((v) =>
    PLACEHOLDER.test(v.name)
      ? name.startsWith(prefixOf(v.name)) && name.length > prefixOf(v.name).length
      : v.name === name,
  );
  if (sys) {
    if (sys.applies_to.includes(field))
      return { kind: 'system', description: sys.description, misplaced: false };
    return { kind: 'unknown', description: 'No se puede usar en este campo.', misplaced: true };
  }
  const own = [...declared, ...extra.map(normalizeExtra)].find((v) => v.name === name);
  if (own) return { kind: 'declared', description: own.description ?? '', misplaced: false };
  return { kind: 'unknown', description: UNKNOWN_HINT, misplaced: false };
}

/** `system | declared | unknown` de `{{name}}` (las `extra` cuentan como declaradas: tienen fuente). */
export function classify(name: string, sources: VariableSources): Resolved['kind'] {
  return resolveVariable(name, sources).kind;
}
