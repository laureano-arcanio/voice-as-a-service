import dur from "../../../public/proyectos/primeros-pasos/vo/duraciones.json";

export const FPS = 30;
export type VoId = keyof typeof dur;

// Escenas en segundos absolutos, en orden. La intro se funde 0,6 s sobre la siguiente.
export const INTRO_FADE = 0.6;
const LENS = {
  intro: 5.0,
  agentes: 5.4,
  nombre: 7.9,
  definicion: 8.0,
  guardar: 5.4,
  probar: 6.0,
  enlace: 7.0,
  llamada: 8.6,
  cierre: 7.0,
};
export type SceneId = keyof typeof LENS;

export const SCENES = (() => {
  let at = 0;
  const out = {} as Record<SceneId, { from: number; len: number }>;
  for (const id of Object.keys(LENS) as SceneId[]) {
    out[id] = { from: at, len: LENS[id] };
    at += LENS[id] - (id === "intro" ? INTRO_FADE : 0);
  }
  return out;
})();

export const VOICES: { id: VoId; scene: SceneId; at: number }[] = [
  { id: "t1", scene: "intro", at: 0.25 },
  { id: "t2", scene: "agentes", at: 0.45 },
  { id: "t3", scene: "nombre", at: 0.35 },
  { id: "t4", scene: "definicion", at: 0.35 },
  { id: "t5", scene: "guardar", at: 0.4 },
  { id: "t6", scene: "probar", at: 0.35 },
  { id: "t7", scene: "enlace", at: 0.35 },
  { id: "t8", scene: "llamada", at: 0.35 },
  { id: "t9", scene: "cierre", at: 0.5 },
];

export const TOTAL = SCENES.cierre.from + SCENES.cierre.len;
export const f = (s: number) => Math.round(s * FPS);
