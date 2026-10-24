import dur from "../../../public/proyectos/derivaciones/vo/duraciones.json";
import { armarEscenas, duracionTotal } from "../../../src/comun/montaje";

export type VoId = keyof typeof dur;

// Escenas en segundos, en orden. La intro se funde 0,6 s sobre la siguiente. Cada escena dura su locución
// (vo/duraciones.json) más un respiro; si se regenera la voz, revisar que ninguna se pise.
export const INTRO_FADE = 0.6;
const LENS = {
  intro: 6.6,
  ciclo: 8.4,
  areas: 7.4,
  espera: 6.9,
  fallback: 5.9,
  equipo: 6.4,
  area: 6.5,
  horario: 7.0,
  agente: 8.0,
  guardar: 6.0,
  resultado: 5.6,
  cierre: 5.6,
};
export type SceneId = keyof typeof LENS;

export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);

export const VOICES: { id: VoId; scene: SceneId; at: number }[] = [
  { id: "d1", scene: "intro", at: 0.4 },
  { id: "d2", scene: "ciclo", at: 0.4 },
  { id: "d3", scene: "areas", at: 0.4 },
  { id: "d4", scene: "espera", at: 0.4 },
  { id: "d5", scene: "fallback", at: 0.45 },
  { id: "d6", scene: "equipo", at: 0.45 },
  { id: "d7", scene: "area", at: 0.4 },
  { id: "d8", scene: "horario", at: 0.4 },
  { id: "d9", scene: "agente", at: 0.4 },
  { id: "d10", scene: "guardar", at: 0.4 },
  { id: "d11", scene: "resultado", at: 0.4 },
  { id: "d12", scene: "cierre", at: 0.7 },
];

export const TOTAL = duracionTotal(SCENES);
