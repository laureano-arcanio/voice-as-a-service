import dur from "../../../public/proyectos/sqlamoblamientos-analisis/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s), en el orden del PDF sqlamoblamientos-propuesta v1 y con el formato de goldman-analisis v3 y
// baicenter-analisis v1. La intro se funde con la siguiente (INTRO_FADE s).
export const INTRO_FADE = 0.6;
const LENS = { intro: 7.6, bien: 7.1, cita: 5.6, mejorar: 16.75, clientes: 8.0, propuesta: 15.5, panel: 5.8, cierre: 3.6 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Respiro entre las tarjetas de "Dónde podríamos mejorar": GAP s entre los archivos, más el silencio propio del final
// de cada toma (~0,15–0,2 s): ~0,65 s
const GAP = 0.45;
const a4a = 0.3;
const a4b = a4a + dur.a4a + GAP;
const a4c = a4b + dur.a4b + GAP;
const a4d = a4c + dur.a4c + GAP;

// Momento en que arranca cada voz, relativo a su escena (s). a1 espera 2 s con la portada en pantalla.
// a6c (v3): el pase a una persona, en la misma escena que a6a, 0,4 s después
export const AT = { a1: 2.0, a2: 0.3, a3: 0.3, a4a, a4b, a4c, a4d, a5: 0.3, a6a: 0.3, a6c: 0.3 + dur.a6a + 0.4, a6b: 0.3, a7: 0.5 };

export const VOICES: Voz[] = [
  { id: "a1", scene: "intro", at: AT.a1 },
  { id: "a2", scene: "bien", at: AT.a2 },
  { id: "a3", scene: "cita", at: AT.a3 },
  { id: "a4a", scene: "mejorar", at: AT.a4a },
  { id: "a4b", scene: "mejorar", at: AT.a4b },
  { id: "a4c", scene: "mejorar", at: AT.a4c },
  { id: "a4d", scene: "mejorar", at: AT.a4d },
  { id: "a5", scene: "clientes", at: AT.a5 },
  { id: "a6a", scene: "propuesta", at: AT.a6a },
  { id: "a6c", scene: "propuesta", at: AT.a6c },
  { id: "a6b", scene: "panel", at: AT.a6b },
  { id: "a7", scene: "cierre", at: AT.a7 },
];
export const DUR = dur;
