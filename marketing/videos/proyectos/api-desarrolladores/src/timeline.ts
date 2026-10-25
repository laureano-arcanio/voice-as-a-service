import dur from "../../../public/proyectos/api-desarrolladores/vo/duraciones.json";
import barras from "../../../public/proyectos/api-desarrolladores/vo/demo-barras.json";
import { armarEscenas, duracionTotal, Voz } from "../../../src/comun/montaje";

// Duraciones de la locución + la muestra real del TTS (vo/demo.wav: la respuesta de POST /audio/speech, voz sofia)
export const DUR: Record<string, number> = { ...dur, demo: barras.segundos };

// Escenas (s). La intro se funde 0,6 s con la siguiente.
export const INTRO_FADE = 0.6;
const LENS = {
  intro: 11.6,
  capacidades: 14.0,
  auth: 14.6,
  llm: 10.4,
  tts: 10.6,
  agente: 9.2,
  llamada: 10.4,
  resultado: 10.4,
  webhook: 8.0,
  cierre: 10.0,
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas<SceneId>(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Cuándo arranca cada voz dentro de su escena (s)
export const AT = {
  a1: 0.6, a2: 0.3, a3: 0.3, a4: 9.5, a5: 0.3, a6: 0.3, demo: 6.4, a7: 0.3, a8: 0.3, a9: 0.3, a10: 0.3, a11: 0.4,
} as const;

export const VOICES: Voz[] = [
  { id: "a1", scene: "intro", at: AT.a1 },
  { id: "a2", scene: "capacidades", at: AT.a2 },
  { id: "a3", scene: "auth", at: AT.a3 },
  { id: "a4", scene: "auth", at: AT.a4 },
  { id: "a5", scene: "llm", at: AT.a5 },
  { id: "a6", scene: "tts", at: AT.a6 },
  { id: "demo", scene: "tts", at: AT.demo },
  { id: "a7", scene: "agente", at: AT.a7 },
  { id: "a8", scene: "llamada", at: AT.a8 },
  { id: "a9", scene: "resultado", at: AT.a9 },
  { id: "a10", scene: "webhook", at: AT.a10 },
  { id: "a11", scene: "cierre", at: AT.a11 },
];

// Subtítulos: lo que dice la locución, con la grafía normal, en tramos cortos (se reparten por largo de texto)
export const SUBS: Record<string, string[]> = {
  a1: ["Con las APIs de Atentina sumás agentes de IA,", "llamadas, campañas y voz a cualquier aplicación.", "Y la API de inferencia es compatible con el SDK de OpenAI."],
  a2: ["Son dos. La de plataforma hace lo mismo que el panel:", "agentes, llamadas, contactos, campañas, derivaciones y reportes.", "La de inferencia: modelo de lenguaje, transcripción", "y síntesis con voces argentinas, también en streaming."],
  a3: ["Para empezar, en el panel: API > Nueva API key.", "Elegí qué puede hacer: llamadas, LLM, transcripción o síntesis.", "La key se muestra una sola vez."],
  a4: ["Cada pedido lleva la key en el encabezado Authorization."],
  a5: ["Con el SDK de OpenAI cambiás solo base_url y api_key.", "El modelo lo fija la plataforma.", "Esta es la respuesta real."],
  a6: ["Para pasarla a voz, mandás el texto a la síntesis", "con una de las 41 voces. Así suena:"],
  demo: ["«Sí, atendemos los sábados de 9 a 13 horas.» (audio real, voz sofia)"],
  a7: ["Ahora, la API de plataforma, con la key calls.", "Consultás un agente: su versión, su voz", "y los datos que toma en cada conversación."],
  a8: ["Para lanzar una llamada, mandás el agente y el teléfono.", "Sin teléfono, es una llamada de prueba desde el navegador.", "La respuesta trae el conversation_id."],
  a9: ["Con ese id consultás el estado y el resultado:", "cuánto duró, cómo terminó y los datos que tomó el agente,", "listos para guardar en tu sistema."],
  a10: ["En las campañas no hace falta consultar:", "el resultado de cada contacto te llega por webhook, firmado."],
  a11: ["Una key y pocas líneas: agentes, telefonía y voz en tu aplicación.", "Documentación: atentina.com.ar/desarrolladores"],
};
