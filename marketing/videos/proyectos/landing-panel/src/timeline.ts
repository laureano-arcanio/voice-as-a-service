// Video de la landing (columna de ~540 px, al lado de la lista de funciones): el panel para configurar un agente.
// Vertical 4:5 (1080 x 1350). Desde la v5, sin texto: arranca en el panel y recorre cinco momentos.
// Sin locución, en loop: un fundido corto desde y hacia blanco. Tiempos en segundos.

export const W = 1080;
export const H = 1350;

// Cada momento entra con un fundido de CRUCE s sobre el anterior (el nuevo se dibuja encima).
export const CRUCE = 0.35;
// Fundido desde blanco al empezar y hacia blanco al terminar (9 cuadros): el loop empalma.
export const BLANCO = 0.3;

export const T = {
  m1: 0, // el agente y la voz
  m2: 4.8, // la herramienta y Tu sistema
  m3: 9.2, // el área Ventas: orden, rotativa y horario
  m4: 13.6, // Hablarle ahora
  m5: 17.8, // Reportes
  fin: 22.0,
};

export const MOMENTOS = [
  { id: "m1", de: T.m1, a: T.m2 },
  { id: "m2", de: T.m2, a: T.m3 },
  { id: "m3", de: T.m3, a: T.m4 },
  { id: "m4", de: T.m4, a: T.m5 },
  { id: "m5", de: T.m5, a: T.fin },
] as const;
