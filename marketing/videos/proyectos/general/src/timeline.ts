import dur from "../../../public/proyectos/general/vo/duraciones.json";
import envs from "../../../public/proyectos/general/vo/envolventes.json";

export const FPS = 30;
export type VoId = keyof typeof dur;

// Escenas (segundos absolutos), en orden. La intro (la pantalla del cierre) se funde con la escena
// siguiente: esta arranca INTRO_FADE s antes de que la intro termine.
export const INTRO_FADE = 0.6;
const LENS = { intro: 6.8, problema: 5.2, atentina: 5.5, viaje: 7.8, api: 13.6, salientes: 9.0, panel: 6.4, cierre: 6.8 };
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

// Viaje de la voz, relativo a la escena "viaje" (s). Entre que la cliente termina de hablar y la
// respuesta pasan RESPUESTA s: la mediana real de las llamadas desde el 7-oct-2026 (call_logs.latency,
// total = fin de la frase + LLM + TTS, 35 turnos).
export const RESPUESTA = 0.9;
const C1 = 0.7;
const END_C1 = C1 + dur.c1;
export const VIAJE = {
  C1,
  END_C1,
  STT: END_C1 + 0.12, // sale el texto
  LLM: END_C1 + 0.26, // llega al agente
  CRM: END_C1 + 0.4, // busca a la cliente en el CRM
  CRM_BACK: END_C1 + 0.56, // vuelve con sus datos
  TTS: END_C1 + 0.78, // la respuesta llega a la síntesis
  A1: END_C1 + RESPUESTA,
  END_A1: END_C1 + RESPUESTA + dur.a1,
};

export const VOICES: { id: VoId; scene: SceneId; at: number }[] = [
  { id: "n5", scene: "intro", at: 0.2 },
  { id: "n1", scene: "problema", at: 0.4 },
  { id: "n2", scene: "atentina", at: 0.25 },
  { id: "c1", scene: "viaje", at: VIAJE.C1 },
  { id: "a1", scene: "viaje", at: VIAJE.A1 },
  { id: "n3", scene: "api", at: 0.2 },
  { id: "n3b", scene: "api", at: 6.1 },
  { id: "n6", scene: "salientes", at: 0.2 },
  { id: "n4", scene: "panel", at: 0.2 },
  { id: "n5", scene: "cierre", at: 0.2 },
];

export const TOTAL = SCENES.cierre.from + SCENES.cierre.len;
export const f = (s: number) => Math.round(s * FPS);
export const voDur = (id: VoId) => dur[id];

// Intervalos absolutos (frames) en que suena una voz: para bajar la música
export const VOICE_SPANS = VOICES.map((v) => {
  const start = f(SCENES[v.scene].from + v.at);
  return [start, start + f(dur[v.id])] as const;
});

/** Nivel de la voz (0..1) en un frame local de la escena, si la voz arrancó en `at` (s). */
export const level = (id: VoId, frame: number, at: number) => {
  const e = envs[id];
  const i = frame - f(at);
  return i >= 0 && i < e.length ? e[i] : 0;
};
