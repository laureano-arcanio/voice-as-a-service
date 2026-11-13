import type { ClientTool } from '@/api/types';
import type { ExtraVariable } from '@/components/variables';

/**
 * Las variables que asignan las demás herramientas (`assign` de su definición): llegan al espacio de la
 * conversación y esta herramienta las puede nombrar. La propia no cuenta: sus `assign` son su salida.
 */
export function assignedByOthers(tools: ClientTool[], slug: string): ExtraVariable[] {
  const out: ExtraVariable[] = [];
  const seen = new Set<string>();
  for (const tool of tools) {
    if (tool.slug === slug) continue;
    const assign = (tool.definition as { assign?: unknown } | null)?.assign;
    if (!Array.isArray(assign)) continue;
    for (const item of assign) {
      const name = (item as { var?: unknown } | null)?.var;
      if (typeof name !== 'string' || !name.trim() || seen.has(name.trim())) continue;
      seen.add(name.trim());
      out.push({ name: name.trim(), description: `La asigna ${tool.slug}` });
    }
  }
  return out;
}
