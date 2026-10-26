// Condiciones y política de privacidad con versión (docs/TERMINOS_PLAN.md). Los textos son copia de
// app/legal/texts/ (`make legal-sync`): no se editan acá.
import type { AstroComponentFactory } from "astro/runtime/server/index.js";
import index from "./legal/index.json";

export type LegalSlug = keyof typeof index;

const modules = import.meta.glob<{ Content: AstroComponentFactory }>("./legal/*/*.md", { eager: true });

export const legal = index;

/** El texto de una versión, como componente. */
export function legalContent(slug: LegalSlug, version: string): AstroComponentFactory {
  const mod = modules[`./legal/${slug}/${version}.md`];
  if (!mod) throw new Error(`No existe ${slug}/${version}.md: make legal-sync`);
  return mod.Content;
}

/** "25 de octubre de 2026" desde la versión (AAAA-MM-DD). */
export function versionDate(version: string): string {
  return new Date(`${version}T12:00:00Z`).toLocaleDateString("es-AR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}
