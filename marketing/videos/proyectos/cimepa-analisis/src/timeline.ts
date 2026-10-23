import dur from "../../../public/proyectos/cimepa-analisis/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s), en el orden del PDF cimepa-propuesta v1 (hojas 1, 3 y 4), con el formato de goldman-analisis v3 y
// baicenter-analisis v1. La intro se funde con la siguiente (INTRO_FADE s).
export const INTRO_FADE = 0.6;
const LENS = { intro: 6.9, pedido: 14.0, entra: 10.6, empleado: 7.6, ia: 6.5, registro: 8.2, agente: 8.1, cierre: 3.3 };
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// v2: paula narra y pablo dice los cuatro pedidos (c2a a c2d). Respiro entre líneas: GAP s entre los archivos, más el
// silencio propio de cada toma (~0,3 s) ≈ 0,65–0,7 s
const GAP = 0.35;
const c2 = 0.55;
const c2a = c2 + dur.c2 + GAP;
const c2b = c2a + dur.c2a + GAP;
const c2c = c2b + dur.c2b + GAP;
const c2d = c2c + dur.c2c + GAP;

// Momento en que arranca cada voz, relativo a su escena (s). c1 espera 2 s con la portada en pantalla.
export const AT = { c1: 2.0, c2, c2a, c2b, c2c, c2d, c3: 0.25, c4: 0.15, c5: 0.25, c6: 0.25, c7: 0.25, c8: 0.4 };

export const VOICES: Voz[] = [
  { id: "c1", scene: "intro", at: AT.c1 },
  { id: "c2", scene: "pedido", at: AT.c2 },
  { id: "c2a", scene: "pedido", at: AT.c2a },
  { id: "c2b", scene: "pedido", at: AT.c2b },
  { id: "c2c", scene: "pedido", at: AT.c2c },
  { id: "c2d", scene: "pedido", at: AT.c2d },
  { id: "c3", scene: "entra", at: AT.c3 },
  { id: "c4", scene: "empleado", at: AT.c4 },
  { id: "c5", scene: "ia", at: AT.c5 },
  { id: "c6", scene: "registro", at: AT.c6 },
  { id: "c7", scene: "agente", at: AT.c7 },
  { id: "c8", scene: "cierre", at: AT.c8 },
];
export const DUR = dur;
