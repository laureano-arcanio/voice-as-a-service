import dur from "../../../public/proyectos/yoizen/vo/duraciones.json";

export type VoId = keyof typeof dur;

// Escenas (segundos). La intro se funde con la escena siguiente: esta arranca INTRO_FADE s antes.
export const INTRO_FADE = 0.6;
const LENS = { intro: 6.0, arquitectura: 11.0, agentes: 10.4, llamadas: 13.0, inferencia: 11.0, datos: 9.4, cierre: 9.4 };
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
  { id: "y1", scene: "intro", at: 0.4 },
  { id: "y2", scene: "arquitectura", at: 0.3 },
  { id: "y3", scene: "agentes", at: 0.3 },
  { id: "y4", scene: "llamadas", at: 0.3 },
  { id: "y5", scene: "inferencia", at: 0.3 },
  { id: "y6", scene: "datos", at: 0.3 },
  { id: "y7", scene: "cierre", at: 0.3 },
];

export const FPS = 30;
export const f = (s: number) => Math.round(s * FPS);
export const TOTAL = SCENES.cierre.from + SCENES.cierre.len;
export const VOICE_SPANS = VOICES.map((v) => {
  const start = f(SCENES[v.scene].from + v.at);
  return [start, start + f(dur[v.id])] as const;
});
