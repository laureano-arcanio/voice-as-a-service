import dur from "../../../public/proyectos/axiomait-analisis/vo/duraciones.json";
import guion from "../guion.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s), en el orden del PDF axiomait-propuesta v1 (hojas 1 a 6), con el formato de cimepa-analisis v2.
// Los largos salen de la locución (duraciones.json): la voz arranca en AT y la escena sigue POST s después.
export const INTRO_FADE = 0.6;
const r1 = (s: number) => Math.round(s * 10) / 10;

// Respiro entre las líneas de lucas: GAP s entre archivos, más el silencio propio de cada toma (~0,3 s) ≈ 0,7 s
const GAP = 0.38;
const b1 = 0.7; // con el título de la escena ya en pantalla
const b2 = b1 + dur.b1 + GAP;
const b3 = b2 + dur.b2 + GAP;
const b4 = b3 + dur.b3 + GAP;
const a7 = 0.35 + dur.a6 + 0.35;
const a8 = a7 + dur.a7 + 0.45;

// Momento en que arranca cada voz, relativo a su escena (s). a1 espera 2 s con la portada en pantalla.
export const AT = { a1: 2.0, a2: 0.35, b1, b2, b3, b4, a4: 0.3, a5: 0.3, a6: 0.35, a7, a8, a9: 0.3, a10: 0.4 };

const LENS = {
  intro: r1(AT.a1 + dur.a1 + 0.9),
  bien: r1(AT.a2 + dur.a2 + 0.9),
  lineas: r1(b4 + dur.b4 + 0.9),
  producto: r1(AT.a4 + dur.a4 + 0.9),
  llamador: r1(AT.a5 + dur.a5 + 1.0),
  voces: r1(a8 + dur.a8 + 0.9),
  marcha: r1(AT.a9 + dur.a9 + 0.9),
  cierre: r1(AT.a10 + dur.a10 + 1.6),
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

export const VOICES: Voz[] = (Object.keys(AT) as (keyof typeof AT)[]).map((id) => ({
  id,
  scene: { a1: "intro", a2: "bien", b1: "lineas", b2: "lineas", b3: "lineas", b4: "lineas", a4: "producto",
    a5: "llamador", a6: "voces", a7: "voces", a8: "voces", a9: "marcha", a10: "cierre" }[id],
  at: AT[id],
}));
export const DUR = dur;

/**
 * Cuándo se dice un fragmento de una línea, relativo a la escena (s): el inicio de la voz más la proporción de
 * caracteres antes del fragmento (paula habla a ritmo parejo; las pausas de puntuación corren algo la cuenta).
 */
export const en = (id: keyof typeof AT, fragmento: string): number => {
  const texto = guion.lineas.find((l) => l.id === id)?.texto ?? "";
  const i = Math.max(0, texto.indexOf(fragmento));
  return AT[id] + (dur as Record<string, number>)[id] * (i / Math.max(1, texto.length));
};
