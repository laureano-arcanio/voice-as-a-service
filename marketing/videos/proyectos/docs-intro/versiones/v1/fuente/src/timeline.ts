import dur from "../../../public/proyectos/docs-intro/vo/duraciones.json";
import { armarEscenas, duracionTotal, Voz } from "../../../src/comun/montaje";

export const DUR: Record<string, number> = dur;

// Escenas (s). La intro se funde 0,6 s con la siguiente.
export const INTRO_FADE = 0.6;
const LENS = {
  intro: 7.2,
  formas: 7.4,
  mcp: 11.4,
  api: 10.4,
  cierre: 9.0,
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas<SceneId>(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Cuándo arranca cada voz dentro de su escena (s)
export const AT = { d1: 0.6, d2: 0.4, d3: 0.3, d4: 0.3, d5: 0.4 } as const;
export type VoId = keyof typeof AT;

export const ESCENA_DE: Record<VoId, SceneId> = { d1: "intro", d2: "formas", d3: "mcp", d4: "api", d5: "cierre" };

export const VOICES: Voz[] = (Object.keys(AT) as VoId[]).map((id) => ({ id, scene: ESCENA_DE[id], at: AT[id] }));

// Subtítulos: la locución con la grafía normal, en tramos de una línea (se reparten por largo de texto)
export const SUBS: Record<VoId, string[]> = {
  d1: ["Atentina se usa de tres formas:", "desde el panel, desde tu agente de IA o desde tu sistema."],
  d2: ["Las tres hacen lo mismo, con tu cuenta y dentro de tu plan."],
  d3: ["Por MCP conectás tu agente de IA", "y le pedís en español lo que necesitás:", "armar y probar agentes, revisar las llamadas", "o lanzar una campaña. Sin programar."],
  d4: ["Por API, tu sistema maneja agentes, llamadas y campañas,", "y usa los motores de lenguaje, transcripción y voz,", "compatibles con OpenAI."],
  d5: ["Elegí la forma que te sirva.", "La documentación de cada una está en atentina.com.ar/desarrolladores"],
};

/** Momento (s, dentro de la escena) en que arranca el tramo n de la voz, repartido por largo como los subtítulos. */
export const sub = (id: VoId, n: number) => {
  const partes = SUBS[id];
  const total = partes.reduce((s, p) => s + p.length, 0);
  const antes = partes.slice(0, n).reduce((s, p) => s + p.length, 0);
  return AT[id] + (DUR[id] * antes) / total;
};
