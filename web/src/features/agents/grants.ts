import type { ClientTool } from '@/api/types';
import type { Draft } from './draft';

/** Secretos que piden las herramientas del cliente elegidas en el formulario (también las de workflows): nombre -> slugs. */
export function neededSecrets(draft: Draft, tools: ClientTool[] | undefined): Map<string, string[]> {
  const out = new Map<string, string[]>();
  if (draft.external) return out;
  // Las de pre-call y post-call las corre la plataforma y piden sus secretos igual.
  const slugs = [
    ...draft.clientTools.map((g) => g.tool),
    ...[draft.workflows.preCall?.tool, draft.workflows.postCall?.tool].filter((s): s is string => !!s),
  ];
  for (const slug of slugs) {
    for (const name of tools?.find((t) => t.slug === slug)?.secrets ?? [])
      out.set(name, [...(out.get(name) ?? []), slug]);
  }
  return out;
}
