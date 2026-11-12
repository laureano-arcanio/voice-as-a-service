import dur from "../../../public/proyectos/experto-analisis/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s), en el orden del PDF experto-propuesta v1. La intro se funde con la siguiente (INTRO_FADE s).
export const INTRO_FADE = 0.6;
const LENS = { intro: 6.0, bien: 8.4, cita: 6.0, mejorar: 15.9, propuesta: 12.6, panel: 6.0, cierre: 4.0 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Respiro entre las frases de "Dónde podríamos mejorar": GAP s entre archivos, más el silencio propio de cada toma (~0,7 s)
const GAP = 0.4;
const a4a = 0.3;
const a4b = a4a + dur.a4a + GAP;
const a4c = a4b + dur.a4b + GAP;
const a4d = a4c + dur.a4c + GAP;

// Momento en que arranca cada voz, relativo a su escena (s). a1 espera 2 s con la portada en pantalla.
export const AT = { a1: 2.0, a2: 0.3, a3: 0.3, a4a, a4b, a4c, a4d, a5: 0.3, a6: 0.3, a7: 0.5 };

export const VOICES: Voz[] = [
  { id: "a1", scene: "intro", at: AT.a1 },
  { id: "a2", scene: "bien", at: AT.a2 },
  { id: "a3", scene: "cita", at: AT.a3 },
  { id: "a4a", scene: "mejorar", at: AT.a4a },
  { id: "a4b", scene: "mejorar", at: AT.a4b },
  { id: "a4c", scene: "mejorar", at: AT.a4c },
  { id: "a4d", scene: "mejorar", at: AT.a4d },
  { id: "a5", scene: "propuesta", at: AT.a5 },
  { id: "a6", scene: "panel", at: AT.a6 },
  { id: "a7", scene: "cierre", at: AT.a7 },
];
export const DUR = dur;
