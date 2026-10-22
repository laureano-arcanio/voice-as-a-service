import dur from "../../../public/proyectos/goldman-analisis/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s), en el orden del PDF goldman-propuesta v1. La intro se funde con la siguiente (INTRO_FADE s).
// v3: locución a 1x, lo observado con un respiro entre tarjetas y la propuesta en dos escenas (equipo y panel).
export const INTRO_FADE = 0.6;
const LENS = { intro: 5.5, bien: 9.8, cita: 5.5, observamos: 14.2, clientes: 7.8, propuesta: 10.9, panel: 6.6, cierre: 4.3 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Respiro entre las observaciones: GAP s entre los archivos, más ~0,3 s de silencio propio de cada toma (~0,7 s)
const GAP = 0.4;
const a4a = 0.3;
const a4b = a4a + dur.a4a + GAP;
const a4c = a4b + dur.a4b + GAP;
const a4d = a4c + dur.a4c + GAP;

// Momento en que arranca cada voz, relativo a su escena (s)
// a1 espera 2 s con la portada en pantalla (pedido del usuario, v2)
export const AT = { a1: 2.0, a2: 0.3, a3: 0.3, a4a, a4b, a4c, a4d, a5: 0.3, a6a: 0.3, a6b: 0.3, a7: 0.5 };

export const VOICES: Voz[] = [
  { id: "a1", scene: "intro", at: AT.a1 },
  { id: "a2", scene: "bien", at: AT.a2 },
  { id: "a3", scene: "cita", at: AT.a3 },
  { id: "a4a", scene: "observamos", at: AT.a4a },
  { id: "a4b", scene: "observamos", at: AT.a4b },
  { id: "a4c", scene: "observamos", at: AT.a4c },
  { id: "a4d", scene: "observamos", at: AT.a4d },
  { id: "a5", scene: "clientes", at: AT.a5 },
  { id: "a6a", scene: "propuesta", at: AT.a6a },
  { id: "a6b", scene: "panel", at: AT.a6b },
  { id: "a7", scene: "cierre", at: AT.a7 },
];
export const DUR = dur;
