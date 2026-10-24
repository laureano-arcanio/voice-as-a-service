import dur from "../../../public/proyectos/tutorial-agente-free-mobile/vo/duraciones.json";
import { armarEscenas, duracionTotal } from "../../../src/comun/montaje";

export type VoId = keyof typeof dur;

// Escenas en segundos, en orden. La intro se funde 0,6 s sobre la siguiente. Cada escena dura su locución
// (vo/duraciones.json) más un respiro; si se regenera la voz, revisar que ninguna se pise.
export const INTRO_FADE = 0.6;
const LENS = {
  intro: 5.5,
  agentes: 5.3,
  nombre: 5.9,
  definicion: 7.1,
  probar: 7.5,
  link: 6.2,
  quien: 6.3,
  conversaciones: 6.4,
  planes: 8.7,
  cierre: 4.2,
};
export type SceneId = keyof typeof LENS;

export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);

export const VOICES: { id: VoId; scene: SceneId; at: number }[] = [
  { id: "f1", scene: "intro", at: 0.4 },
  { id: "f2", scene: "agentes", at: 0.4 },
  { id: "f3", scene: "nombre", at: 0.4 },
  { id: "f4", scene: "definicion", at: 0.4 },
  { id: "f5", scene: "probar", at: 0.4 },
  { id: "f6", scene: "link", at: 0.4 },
  { id: "f7", scene: "quien", at: 0.4 },
  { id: "f8", scene: "conversaciones", at: 0.4 },
  { id: "f9", scene: "planes", at: 0.4 },
  { id: "f10", scene: "cierre", at: 0.7 },
];

export const TOTAL = duracionTotal(SCENES);
