// Video de la landing (columna de ~540 px, al lado de la lista de funciones): el panel para configurar un agente.
// Vertical 4:5 (1080 x 1350) desde la v2.
// Sin locución, en loop: empieza y termina en blanco. Tiempos en segundos.

export const W = 1920;
export const H = 1080;

// Cada momento entra con un fundido de CRUCE s sobre el anterior (el nuevo se dibuja encima).
export const CRUCE = 0.35;

export const T = {
  logoIn: 0.25, // intro: logo y frase sobre blanco
  fraseIn: 0.5,
  m1: 1.9, // Creás tu agente y elegís la voz
  m2: 5.7, // Lo conectás a tu sistema
  m3: 8.8, // Derivás a tu equipo
  m4: 11.9, // Lo probás en el momento
  m5: 15.0, // Ves los resultados
  cierre: 18.0, // logo y frase sobre blanco
  cierreOut: 19.5, // se va todo
  fin: 20.0, // blanco: empalma con el principio
};

export const MOMENTOS = [
  { id: "m1", de: T.m1, a: T.m2 },
  { id: "m2", de: T.m2, a: T.m3 },
  { id: "m3", de: T.m3, a: T.m4 },
  { id: "m4", de: T.m4, a: T.m5 },
  { id: "m5", de: T.m5, a: T.cierre },
] as const;
