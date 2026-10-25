import dur from "../../../public/proyectos/mcp-claude-code/vo/duraciones.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s). Los largos salen de la locución (duraciones.json): la voz arranca en AT y la escena sigue unos
// segundos más; las de la terminal, lo que necesita la demo (instalar dura más que su frase).
export const INTRO_FADE = 0.6;
const r1 = (s: number) => Math.round(s * 10) / 10;

export const AT = { m1: 1.0, m2: 0.4, m3: 0.5, m4: 0.4, m5: 0.4, m6: 0.4, m7: 0.4, m8: 0.4, m9: 0.5 };
export type VoId = keyof typeof AT;

const LENS = {
  intro: r1(AT.m1 + dur.m1 + 1.0),
  grupos: r1(AT.m2 + dur.m2 + 1.1),
  instalar: Math.max(7.4, r1(AT.m3 + dur.m3 + 1.0)),
  autenticar: r1(AT.m4 + dur.m4 + 1.4),
  cuenta: r1(AT.m5 + dur.m5 + 1.6),
  crear: r1(AT.m6 + dur.m6 + 1.6),
  probar: r1(AT.m7 + dur.m7 + 2.0),
  equipo: r1(AT.m8 + dur.m8 + 1.8),
  cierre: r1(AT.m9 + dur.m9 + 2.6),
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);
export const LEN = LENS;

const ESCENA: Record<VoId, SceneId> = {
  m1: "intro", m2: "grupos", m3: "instalar", m4: "autenticar", m5: "cuenta", m6: "crear", m7: "probar", m8: "equipo", m9: "cierre",
};
export const VOICES: Voz[] = (Object.keys(AT) as VoId[]).map((id) => ({ id, scene: ESCENA[id], at: AT[id] }));
export const DUR = dur as Record<VoId, number>;

/**
 * Subtítulos: la locución en pantalla, en tramos cortos (con cifras y "MCP" escritos como se leen). Cada tramo
 * dura lo proporcional a sus caracteres dentro de la línea (paula habla a ritmo parejo).
 */
export const SUBS: Record<VoId, string[]> = {
  m1: ["MCP es el protocolo que conecta un agente de IA con otras plataformas.", "Con el servidor de Atentina, administrás tu cuenta", "desde Claude Code, en lenguaje natural."],
  m2: ["Son 87 herramientas en 8 grupos:", "la cuenta y el plan, agentes, llamadas, links para llamar,", "WhatsApp, contactos, campañas, y el equipo con sus derivaciones."],
  m3: ["Se instala con un solo comando,", "que agrega el servidor con su dirección."],
  m4: ["Después, dentro de Claude Code, abrí el menú MCP,", "elegí Atentina y autenticá.", "Entrás con tu usuario del panel y permitís el acceso."],
  m5: ["Probemos. Le preguntamos qué incluye el plan:", "Claude mira la cuenta, las herramientas disponibles", "y el consumo del mes."],
  m6: ["Ahora, un agente de atención al cliente.", "Parte de la plantilla, completa la base de conocimiento,", "valida la definición y lo crea."],
  m7: ["Y lo prueba por texto, como si fuera un cliente.", "Recibe la respuesta del agente y los datos que tomó,", "sin llamar a nadie ni gastar minutos."],
  m8: ["Para derivar a una persona, suma a alguien al equipo", "y crea un área de ventas, con su horario.", "El agente transfiere ahí cuando hace falta."],
  m9: ["En resumen: con una sola integración, Claude Code consulta,", "crea, configura, prueba y administra Atentina,", "en lenguaje natural. La guía completa está en la documentación."],
};

/** Tramos de subtítulo de una línea: [desde, hasta, texto], relativos a la escena (s). */
export const tramos = (id: VoId): [number, number, string][] => {
  const parts = SUBS[id];
  const total = parts.reduce((a, p) => a + p.length, 0);
  let at = AT[id];
  return parts.map((p) => {
    const d = (DUR[id] * p.length) / total;
    const out: [number, number, string] = [at, at + d, p];
    at += d;
    return out;
  });
};

/** Cuándo empieza el tramo `n` de una línea, relativo a la escena (s). */
export const sub = (id: VoId, n: number) => tramos(id)[n][0];
