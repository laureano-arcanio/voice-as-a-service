import type { ClientTool } from '@/api/types';
import type { Draft } from './draft';

/** Secretos que piden las herramientas del cliente elegidas en el formulario: nombre -> slugs. */
export function neededSecrets(draft: Draft, tools: ClientTool[] | undefined): Map<string, string[]> {
  const out = new Map<string, string[]>();
  if (draft.external) return out;
  for (const g of draft.clientTools) {
    for (const name of tools?.find((t) => t.slug === g.tool)?.secrets ?? [])
      out.set(name, [...(out.get(name) ?? []), g.tool]);
  }
  return out;
}
