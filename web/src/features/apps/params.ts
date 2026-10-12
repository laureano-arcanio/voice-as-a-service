/** "fecha=2026-10-12 & otro=1" -> {fecha: "2026-10-12", otro: "1"}. Vacio: {}. null si no se entiende. */
export function parseParams(text: string): Record<string, string> | null {
  const out: Record<string, string> = {};
  for (const part of text.split(/[&,\n]/)) {
    const p = part.trim();
    if (!p) continue;
    const i = p.indexOf('=');
    if (i <= 0) return null;
    const key = p.slice(0, i).trim();
    const value = p.slice(i + 1).trim();
    if (!/^[a-z_][a-z0-9_]*$/i.test(key) || !value) return null;
    out[key] = value;
  }
  return out;
}
