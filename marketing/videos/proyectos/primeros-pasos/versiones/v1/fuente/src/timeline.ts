import dur from "../../../public/proyectos/primeros-pasos/vo/duraciones.json";
import guion from "../guion.json";
import { armarEscenas, duracionTotal, type Voz } from "../../../src/comun/montaje";

// Escenas (s). Los largos salen de la locución (duraciones.json) más el tiempo de lo que pasa en pantalla
// (tipeo, toques, la llamada). Una sola voz: paula.
export const INTRO_FADE = 0.6;
const r1 = (s: number) => Math.round(s * 10) / 10;

// Momento en que arranca cada voz, relativo a su escena (s)
export const AT = { p1: 0.8, p2: 0.3, p3: 0.3, p4: 0.6, p5: 0.3, p6: 0.3, p7: 0.3, p8: 0.3, p9: 0.3, p10: 0.3, p11: 0.4 };

// Tipeo con zoom: cuándo empieza y cuántos caracteres por segundo
export const TIPEO = {
  nombre: { desde: 0.75, cps: 15 },
  apertura: { desde: 0.95, cps: 30 },
  conocimiento: { desde: 1.0, cps: 30 },
};

const LENS = {
  intro: r1(AT.p1 + dur.p1 + 1.0),
  agentes: r1(AT.p2 + dur.p2 + 1.2),
  nuevo: r1(AT.p3 + dur.p3 + 1.3),
  voz: r1(AT.p4 + dur.p4 + 1.6),
  apertura: r1(Math.max(AT.p5 + dur.p5 + 1.0, 5.2)),
  conocimiento: r1(AT.p6 + dur.p6 + 1.1),
  guardar: r1(AT.p7 + dur.p7 + 1.7),
  probar: r1(AT.p8 + dur.p8 + 1.9),
  llamada: r1(AT.p9 + dur.p9 + 3.4),
  conversaciones: r1(AT.p10 + dur.p10 + 1.6),
  cierre: r1(AT.p11 + dur.p11 + 2.2),
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);
export const LEN = LENS;

const ESCENA: Record<keyof typeof AT, SceneId> = {
  p1: "intro", p2: "agentes", p3: "nuevo", p4: "voz", p5: "apertura", p6: "conocimiento", p7: "guardar",
  p8: "probar", p9: "llamada", p10: "conversaciones", p11: "cierre",
};
export const VOICES: Voz[] = (Object.keys(AT) as (keyof typeof AT)[]).map((id) => ({ id, scene: ESCENA[id], at: AT[id] }));
export const DUR = dur;

/** Cuándo se dice un fragmento de una línea, relativo a la escena (s), por proporción de caracteres. */
export const en = (id: keyof typeof AT, fragmento: string): number => {
  const texto = guion.lineas.find((l) => l.id === id)?.texto ?? "";
  const i = Math.max(0, texto.indexOf(fragmento));
  return AT[id] + (dur as Record<string, number>)[id] * (i / Math.max(1, texto.length));
};
