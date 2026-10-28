import type { MantineColorsTuple } from '@mantine/core';

/** Color de la marca blanca (docs/ARQUITECTURA.md): contraste WCAG y la escala de 10 tonos que pisa a `blue`.
 * La misma matemática que app/services/branding.py (un test de cada lado verifica la misma tabla). */

export const INK = '#0b1220';
export const WHITE = '#ffffff';
export const MIN_CONTRAST = 4.5;

function rgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function toHex(c: [number, number, number]): string {
  return `#${c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`;
}

function linear(channel: number): number {
  const v = channel / 255;
  return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

export function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map(linear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Relación de contraste WCAG 2.1 (1 a 21). */
export function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Texto sobre un fondo: blanco si contrasta 4,5:1, si no la tinta de la app. */
export function textOn(background: string): string {
  return contrast(WHITE, background) >= MIN_CONTRAST ? WHITE : INK;
}

export function isHex(value: string): boolean {
  return /^#[0-9a-f]{6}$/i.test(value);
}

function mix(c: [number, number, number], target: [number, number, number], k: number): [number, number, number] {
  return [c[0] + (target[0] - c[0]) * k, c[1] + (target[1] - c[1]) * k, c[2] + (target[2] - c[2]) * k];
}

// Mezclas ajustadas sobre el azul de Atentina (#2456e6 -> #eaf0ff ... #0e287a; scratch/marca-blanca/fit_scale.py):
// tonos 0-5 hacia blanco, 7-9 hacia negro. Error máximo contra la escala del tema: 10 puntos por canal (tono 4).
const TINTS = [0.914, 0.852, 0.77, 0.688, 0.598, 0.27];
const SHADES = [0.221, 0.353, 0.488];

/** Escala de 10 tonos de Mantine con el color en el tono 6 (primaryShade). */
export function scale(hex: string): MantineColorsTuple {
  const c = rgb(hex);
  const white: [number, number, number] = [255, 255, 255];
  const black: [number, number, number] = [0, 0, 0];
  return [
    ...TINTS.map((t) => toHex(mix(c, white, t))),
    hex.toLowerCase(),
    ...SHADES.map((s) => toHex(mix(c, black, s))),
  ] as unknown as MantineColorsTuple;
}
