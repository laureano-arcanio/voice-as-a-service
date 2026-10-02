// Reglas de una plantilla de texto, las mismas que valida la API (app/whatsapp/signup.py).

const PLACEHOLDER = /\{\{\s*(\d+)\s*\}\}/g;
export const TEMPLATE_NAME = /^[a-z0-9_]{1,512}$/;

/** Numeros de las variables {{n}} del cuerpo, sin repetir y ordenados. */
export function placeholderNumbers(body: string): number[] {
  const nums = new Set<number>();
  for (const m of body.matchAll(PLACEHOLDER)) nums.add(Number(m[1]));
  return [...nums].sort((a, b) => a - b);
}

/** Error de las variables del cuerpo, o null si son {{1}}..{{n}} seguidas. */
export function placeholderError(body: string): string | null {
  const nums = placeholderNumbers(body);
  if (nums.some((n, i) => n !== i + 1)) return 'Las variables tienen que ser {{1}}, {{2}}... seguidas';
  return null;
}

/** Nombre valido para Meta a partir de lo que escribe el usuario. */
export function normalizeTemplateName(raw: string): string {
  return raw
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .slice(0, 512);
}

/** Texto del cuerpo de una plantilla de Meta (componente BODY). */
export function templateBody(components: Record<string, unknown>[]): string {
  const body = components.find((c) => String(c.type).toUpperCase() === 'BODY');
  return typeof body?.text === 'string' ? body.text : '';
}
