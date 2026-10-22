import dur from "../../../public/proyectos/zennonbi-analisis/vo/duraciones.json";
import guion from "../guion.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s), en el orden del PDF zennonbi-propuesta v1 (hojas 1 a 5), con el formato de axiomait-analisis v1.
// Los largos salen de la locución (duraciones.json): la voz arranca en AT y la escena sigue ~0,9 s después.
export const INTRO_FADE = 0.6;
const r1 = (s: number) => Math.round(s * 10) / 10;

// Respiro entre las líneas de lucas: GAP s entre archivos, más el silencio propio de cada toma (~0,3 s) ≈ 0,7 s
const GAP = 0.38;
const b1 = 0.7; // con el título de la escena ya en pantalla
const b2 = b1 + dur.b1 + GAP;
const b3 = b2 + dur.b2 + GAP;
const b4 = b3 + dur.b3 + GAP;
const a3 = 0.35 + dur.a2 + 0.7; // la cita entra en la pausa, antes de a3
const a5 = 0.3 + dur.a4 + 0.5;
const a7 = 0.35 + dur.a6 + 0.45;

// Momento en que arranca cada voz, relativo a su escena (s). a1 espera 2 s con la portada en pantalla.
export const AT = { a1: 2.0, a2: 0.35, a3, b1, b2, b3, b4, a4: 0.3, a5, a6: 0.35, a7, a8: 0.3, a9: 0.4 };

const LENS = {
  intro: r1(AT.a1 + dur.a1 + 0.9),
  bien: r1(a3 + dur.a3 + 0.9),
  lineas: r1(b4 + dur.b4 + 0.9),
  integracion: r1(a5 + dur.a5 + 1.0),
  alianza: r1(a7 + dur.a7 + 1.0),
  marcha: r1(AT.a8 + dur.a8 + 0.9),
  cierre: r1(AT.a9 + dur.a9 + 1.6),
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

const ESCENA: Record<keyof typeof AT, SceneId> = {
  a1: "intro", a2: "bien", a3: "bien", b1: "lineas", b2: "lineas", b3: "lineas", b4: "lineas",
  a4: "integracion", a5: "integracion", a6: "alianza", a7: "alianza", a8: "marcha", a9: "cierre",
};
export const VOICES: Voz[] = (Object.keys(AT) as (keyof typeof AT)[]).map((id) => ({ id, scene: ESCENA[id], at: AT[id] }));
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
