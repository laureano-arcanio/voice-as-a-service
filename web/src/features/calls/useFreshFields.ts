import { useEffect, useState } from 'react';

interface NamedValue {
  name: string;
  value?: unknown;
}

const HIGHLIGHT_MS = 4000;

/**
 * Datos que pasaron de vacio a obtenido desde el render anterior (para resaltarlos
 * unos segundos). La primera carga no resalta nada.
 */
export function useFreshFields(fields: NamedValue[]): Set<string> {
  const snapshot = JSON.stringify(fields.map((f) => [f.name, f.value ?? null]));
  const [prev, setPrev] = useState<{ snapshot: string; values: Map<string, unknown> } | null>(null);
  const [fresh, setFresh] = useState<Set<string>>(() => new Set());

  // Estado derivado del render anterior (patron recomendado por React, sin efecto).
  if (prev?.snapshot !== snapshot) {
    const values = new Map(fields.map((f) => [f.name, f.value ?? null]));
    if (prev) {
      const added = fields
        .filter((f) => f.value != null && prev.values.get(f.name) == null)
        .map((f) => f.name);
      if (added.length) setFresh(new Set([...fresh, ...added]));
    }
    setPrev({ snapshot, values });
  }

  useEffect(() => {
    if (!fresh.size) return;
    const t = setTimeout(() => setFresh(new Set()), HIGHLIGHT_MS);
    return () => clearTimeout(t);
  }, [fresh]);

  return fresh;
}
