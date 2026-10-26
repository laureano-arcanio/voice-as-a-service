import dur from "../../../public/proyectos/yoizen-tu-propio-agente/vo/duraciones.json";
import { armarEscenas, duracionTotal, Voz } from "../../../src/comun/montaje";

export const DUR: Record<string, number> = dur;

/** Las 12 diapositivas de documentos/proyectos/yoizen-tu-propio-agente v1, una escena cada una. */
export const IDS = ["s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08", "s09", "s10", "s11", "s12"] as const;
export type SceneId = (typeof IDS)[number];

// Cada escena dura lo que su locución, más una entrada y una cola (s). Las duraciones salen de vo/duraciones.json.
export const LEAD = 0.5;
const TAIL = 0.8;
const LENS = Object.fromEntries(IDS.map((id) => [id, Math.round((LEAD + DUR[id] + TAIL) * 10) / 10])) as Record<SceneId, number>;
export const SCENES = armarEscenas<SceneId>(LENS);
export const TOTAL = duracionTotal(SCENES);

export const VOICES: Voz[] = IDS.map((id) => ({ id, scene: id, at: LEAD }));

// Subtítulos: la locución con la grafía normal, en tramos de una línea (se reparten por largo de texto)
export const SUBS: Record<SceneId, string[]> = {
  s01: ["Tu propio agente. Una sola función:", "los bots que ustedes ya tienen deciden qué decir,", "y Atentina pone la voz y el teléfono."],
  s02: ["Su omnicanal ya atiende WhatsApp y web chat,", "y su orquestador decide qué responder.", "Falta la voz: llamadas entrantes y salientes,", "con esos mismos bots."],
  s03: ["Atentina pone el número, las llamadas,", "la transcripción, la voz y los minutos.", "Ustedes ponen el prompt, las herramientas,", "la memoria y qué responder."],
  s04: ["La persona habla. Atentina transcribe,", "le manda la conversación a su endpoint", "en el formato de OpenAI,", "y dice cada pedazo de la respuesta apenas llega."],
  s05: ["Sin estado de su lado:", "el historial que mandamos es el que vale.", "Los datos de la llamada van en headers,", "y varios bots pueden compartir un endpoint."],
  s06: ["La respuesta vuelve en pedazos:", "el primero ya suena en el teléfono mientras llega el segundo.", "Streaming obligatorio:", "una respuesta entera cuenta como error."],
  s07: ["Dos herramientas que ejecuta Atentina.", "Con una, su bot corta la llamada y elige el resultado.", "Con la otra, la pasa a una persona de su equipo."],
  s08: ["Un endpoint mínimo son veinte líneas: agrega su prompt,", "le pasa la conversación a su modelo", "y devuelve la respuesta tal cual.", "El resto ya lo tienen."],
  s09: ["Tres pasos en el panel: la conexión,", "con la dirección de su endpoint y su key;", "probar el endpoint;", "y prender que conteste su propio agente.", "También por API y MCP."],
  s10: ["Lo que más pesa es el tiempo hasta el primer texto.", "Más de un segundo se siente lento,", "y su modelo y su infraestructura se notan.", "Texto primero, herramientas después."],
  s11: ["Si su endpoint falla, la llamada no se queda muda:", "el agente dice el mensaje configurado.", "Con varios errores seguidos,", "corta o pasa la llamada a su equipo."],
  s12: ["Próximos pasos: un endpoint con uno de sus bots", "y un caso real.", "Lo conectamos, hacemos llamadas de prueba", "y vamos a un piloto, en el plan Red.", "El resto lo ponemos nosotros."],
};
