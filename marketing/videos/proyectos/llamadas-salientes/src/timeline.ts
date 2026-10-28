import dur from "../../../public/proyectos/llamadas-salientes/vo/duraciones.json";
import { armarEscenas, duracionTotal, Voz } from "../../../src/comun/montaje";

export const DUR: Record<string, number> = { ...dur };

// Escenas (s). La intro se funde 0,6 s con la siguiente.
export const INTRO_FADE = 0.6;
const LENS = {
  intro: 11.0,
  numero: 10.4,
  equipo: 13.0,
  contactos: 10.4,
  panel: 16.2,
  app: 16.4,
  cierre: 12.4,
};
export type SceneId = keyof typeof LENS;
export const SCENES = armarEscenas<SceneId>(LENS, "intro", INTRO_FADE);
export const TOTAL = duracionTotal(SCENES);

// Cuándo arranca cada voz dentro de su escena (s)
export const AT = {
  l1: 0.6, l2: 0.3, l3: 0.3, l4: 0.3, l5: 0.3, l6: 11.3, l7: 0.3, l8: 11.5, l9: 0.4, l10: 4.6, l11: 9.0,
} as const;

export const VOICES: Voz[] = [
  { id: "l1", scene: "intro", at: AT.l1 },
  { id: "l2", scene: "numero", at: AT.l2 },
  { id: "l3", scene: "equipo", at: AT.l3 },
  { id: "l4", scene: "contactos", at: AT.l4 },
  { id: "l5", scene: "panel", at: AT.l5 },
  { id: "l6", scene: "panel", at: AT.l6 },
  { id: "l7", scene: "app", at: AT.l7 },
  { id: "l8", scene: "app", at: AT.l8 },
  { id: "l9", scene: "cierre", at: AT.l9 },
  { id: "l10", scene: "cierre", at: AT.l10 },
  { id: "l11", scene: "cierre", at: AT.l11 },
];

export const ESCENA_DE: Record<string, SceneId> = {
  l1: "intro", l2: "numero", l3: "equipo", l4: "contactos", l5: "panel", l6: "panel", l7: "app", l8: "app",
  l9: "cierre", l10: "cierre", l11: "cierre",
};

// Subtítulos: lo que dice la locución, con la grafía normal, en tramos cortos (se reparten por largo de texto)
export const SUBS: Record<string, string[]> = {
  l1: ["En este video te mostramos cómo hacer llamadas salientes con tu equipo,", "desde el panel y desde la aplicación de teléfono.", "Son cuatro pasos: el número, el equipo, los contactos y el teléfono."],
  l2: ["Primero, el número. El administrador lo asigna a tu cliente desde Números,", "y enseguida aparece en tu panel, en Cuenta, Números.", "Con ese número ya podés llamar."],
  l3: ["Segundo, el equipo. En Agenda, Equipo, agregás a cada persona", "con su nombre, su teléfono y su usuario del panel.", "Después, en el número, elegís que lo atienda el equipo", "y sumás a esas personas, para que también reciban las entrantes."],
  l4: ["Tercero, los contactos. En Agenda, Contactos, tocás Nuevo contacto", "y cargás el teléfono y el nombre.", "Si tenés muchos, los importás desde un archivo."],
  l5: ["Cuarto, a llamar. En Canales, Teléfono del equipo,", "elegís un contacto y tocás Llamar.", "Hablás desde el navegador, mejor con auriculares,", "y tu contacto ve el número de tu empresa."],
  l6: ["Las llamadas del equipo se graban y se transcriben siempre.", "Las encontrás en Conversaciones."],
  l7: ["Y si preferís, usá la aplicación Teléfono.", "Se abre desde el panel, con Abrir aplicación Teléfono,", "y está pensada para el celular.", "Elegís un contacto, tocás Llamar, y la llamada sigue en pantalla completa."],
  l8: ["Mientras hablás, podés silenciar el micrófono,", "usar el teclado o ver los subtítulos."],
  l9: ["Eso es todo: el número, el equipo, los contactos y el teléfono."],
  l10: ["Tené en cuenta que hace falta un plan pago", "y haber aceptado las condiciones nuevas."],
  l11: ["La guía completa está en la documentación."],
};
