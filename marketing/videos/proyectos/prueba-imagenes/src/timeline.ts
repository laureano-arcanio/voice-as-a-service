import { armarEscenas, duracionTotal } from "../../../src/comun/montaje";

// Prueba del pipeline de imágenes: sin locución (guion.json con lineas vacías), duraciones fijas por escena.
export const INTRO_FADE = 0.6;

const LENS = {
  intro: 3.0,
  cafe: 5.4,
  equipo: 5.4,
  marca: 5.0,
  cierre: 3.6,
};

export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas<SceneId>(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);
