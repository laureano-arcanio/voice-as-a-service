import type { ToolGrantDraft } from './draft';

/** Cambia las herramientas de una app: null la saca. */
export function setGrant(tools: ToolGrantDraft[], app: string, next: string[] | null): ToolGrantDraft[] {
  const rest = tools.filter((g) => g.app !== app);
  if (next === null) return rest;
  const i = tools.findIndex((g) => g.app === app);
  const grant = { app, tools: next };
  if (i < 0) return [...tools, grant];
  return tools.map((g) => (g.app === app ? grant : g));
}
