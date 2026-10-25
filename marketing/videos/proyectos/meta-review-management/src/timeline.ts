// Video para el App Review de Meta (whatsapp_business_management): capturas reales del panel, sin locución,
// con subtítulos en inglés. Tiempos en segundos; coordenadas de cámara y cursor en px de cada captura.

export const W = 1920;
export const H = 1080;
export const DIR = "proyectos/meta-review-management";
export const CRUCE = 0.4; // fundido entre tomas

export type Cam = { t: number; x: number; y: number; s: number };
/** Punto del cursor: en px de la captura, o en px de pantalla con `pantalla` (para la ventana de Meta). */
export type Pt = { t: number; x: number; y: number; pantalla?: boolean };

export type Toma = {
  id: string;
  len: number;
  img?: string; // captura de fondo (public/<DIR>/capturas/)
  size?: [number, number];
  bg?: string; // color de la página fuera de la captura
  cam?: Cam[];
  cursor?: Pt[];
  clicks?: number[];
  popup?: { at: number; x: number; y: number; s: number }; // ventana de Meta (m06) encima, en px de pantalla
};

const PANEL: [number, number] = [1784, 1913];
const PAGINA = "#f6f8fb";
const VELO = "#8d9098"; // el fondo oscurecido detrás de un modal

export const TOMAS: Toma[] = [
  { id: "intro", len: 5.0 },
  {
    id: "login", len: 6.6, img: "c00-login.png", size: [1452, 1384], bg: PAGINA,
    cam: [{ t: 0, x: 726, y: 700, s: 1.3 }, { t: 1.2, x: 726, y: 700, s: 1.3 }, { t: 3.6, x: 726, y: 715, s: 1.85 }],
    cursor: [{ t: 0.6, x: 1010, y: 1010 }, { t: 2.2, x: 690, y: 682 }, { t: 3.4, x: 690, y: 682 }, { t: 4.8, x: 736, y: 812 }],
    clicks: [2.4, 5.4],
  },
  {
    // Página WhatsApp: el botón "Conectar WhatsApp" arriba a la derecha
    id: "whatsapp", len: 5.0, img: "m01-whatsapp.png", size: PANEL, bg: PAGINA,
    cam: [{ t: 0, x: 892, y: 502, s: 1.08 }, { t: 1.0, x: 892, y: 502, s: 1.08 }, { t: 3.0, x: 1240, y: 360, s: 1.3 }],
    cursor: [{ t: 0.2, x: 760, y: 560 }, { t: 3.2, x: 1640, y: 112 }],
    clicks: [3.9],
  },
  {
    // Modal "Conectar WhatsApp": cliente y agente elegidos
    id: "conectar", len: 6.4, img: "m04-conectar.png", size: PANEL, bg: VELO,
    cam: [{ t: 0, x: 892, y: 930, s: 1.4 }, { t: 1.5, x: 892, y: 975, s: 1.6 }],
    cursor: [{ t: 0, x: 1640, y: 112 }, { t: 1.6, x: 980, y: 966 }, { t: 2.6, x: 980, y: 966 }, { t: 3.4, x: 980, y: 1043 }, { t: 4.2, x: 980, y: 1043 }, { t: 5.2, x: 1095, y: 1133 }],
    clicks: [5.8],
  },
  {
    // El modal espera y se abre la ventana de Meta (Embedded Signup)
    id: "meta", len: 10.6, img: "m05-esperando-meta.png", size: PANEL, bg: VELO,
    cam: [{ t: 0, x: 892, y: 975, s: 1.6 }, { t: 1.2, x: 892, y: 975, s: 1.6 }, { t: 2.6, x: 760, y: 1000, s: 1.2 }],
    popup: { at: 1.4, x: 1090, y: 58, s: 1.2 },
    cursor: [
      { t: 0, x: 1095, y: 1133 }, { t: 1.6, x: 1095, y: 1133 },
      { t: 4.4, x: 1090 + 396 * 1.2, y: 58 + 352 * 1.2, pantalla: true }, { t: 8.6, x: 1090 + 396 * 1.2, y: 58 + 352 * 1.2, pantalla: true },
    ],
    clicks: [9.4],
  },
  {
    // Después del alta: el número conectado, con estado, calidad y token
    id: "numeros", len: 14.0, img: "m01-whatsapp.png", size: PANEL, bg: PAGINA,
    cam: [
      { t: 0, x: 892, y: 502, s: 1.08 }, { t: 1.2, x: 892, y: 502, s: 1.08 }, { t: 3.0, x: 1050, y: 300, s: 1.55 },
      { t: 5.2, x: 1050, y: 300, s: 1.55 }, { t: 6.8, x: 980, y: 320, s: 1.4 }, { t: 10.2, x: 980, y: 320, s: 1.4 },
      { t: 12.0, x: 1150, y: 930, s: 1.4 },
    ],
    cursor: [
      { t: 0.5, x: 900, y: 640 }, { t: 3.2, x: 470, y: 336 }, { t: 4.6, x: 470, y: 336 }, { t: 6.4, x: 1062, y: 346 },
      { t: 7.8, x: 1062, y: 346 }, { t: 8.8, x: 1288, y: 356 }, { t: 9.8, x: 1420, y: 356 }, { t: 12.6, x: 1360, y: 888 },
    ],
    clicks: [13.2],
  },
  {
    // Plantillas del número +54 9 351 700-2592, con su estado
    id: "plantillas", len: 9.6, img: "m02-plantillas.png", size: PANEL, bg: PAGINA,
    cam: [{ t: 0, x: 1150, y: 930, s: 1.4 }, { t: 1.0, x: 1150, y: 930, s: 1.4 }, { t: 2.6, x: 950, y: 960, s: 1.5 }, { t: 6.0, x: 950, y: 960, s: 1.5 }, { t: 7.4, x: 1180, y: 940, s: 1.45 }],
    cursor: [{ t: 0, x: 1360, y: 888 }, { t: 2.8, x: 360, y: 1022 }, { t: 3.8, x: 360, y: 1022 }, { t: 4.8, x: 848, y: 1022 }, { t: 6.2, x: 848, y: 1022 }, { t: 8.0, x: 1636, y: 889 }],
    clicks: [8.7],
  },
  {
    // Modal "Nueva plantilla": nombre, categoría, cuerpo con variables y ejemplos
    id: "plantilla", len: 12.4, img: "m03-nueva-plantilla.png", size: PANEL, bg: VELO,
    cam: [{ t: 0, x: 892, y: 790, s: 1.45 }, { t: 5.6, x: 892, y: 790, s: 1.45 }, { t: 8.0, x: 892, y: 1190, s: 1.45 }],
    cursor: [
      { t: 0, x: 1636, y: 889 }, { t: 1.4, x: 760, y: 616 }, { t: 2.4, x: 760, y: 616 }, { t: 3.4, x: 960, y: 693 },
      { t: 4.2, x: 960, y: 693 }, { t: 5.2, x: 900, y: 866 }, { t: 7.0, x: 900, y: 866 }, { t: 8.0, x: 760, y: 1005 },
      { t: 8.8, x: 760, y: 1005 }, { t: 9.6, x: 800, y: 1082 }, { t: 10.4, x: 800, y: 1082 }, { t: 11.4, x: 1150, y: 1393 },
    ],
  },
  {
    // Cierre sobre la página entera
    id: "cierre", len: 9.0, img: "m02-plantillas.png", size: PANEL, bg: PAGINA,
    cam: [{ t: 0, x: 892, y: 560, s: 1.12 }, { t: 9.0, x: 892, y: 560, s: 1.0 }],
  },
  { id: "fin", len: 5.0 },
];

// Inicio de cada toma (cada una se funde CRUCE s sobre la anterior)
export const INICIO: Record<string, number> = (() => {
  const out: Record<string, number> = {};
  let at = 0;
  for (const t of TOMAS) {
    out[t.id] = at;
    at += t.len - CRUCE;
  }
  return out;
})();
export const TOTAL = INICIO.fin + TOMAS[TOMAS.length - 1].len;

// Subtítulos (inglés), en segundos desde el inicio de la toma
export const SUBS: { toma: string; de: number; a: number; texto: string }[] = [
  { toma: "login", de: 0.5, a: 6.4, texto: "A business logs in to its Atentina dashboard." },
  { toma: "whatsapp", de: 0.4, a: 11.8, texto: "The business connects its own WhatsApp Business Account with Meta's Embedded Signup." },
  { toma: "meta", de: 1.8, a: 10.4, texto: "Meta's window: the business authorizes Atentina and picks its WhatsApp Business Account and number." },
  { toma: "numeros", de: 0.6, a: 4.4, texto: "After signup the number appears connected:" },
  {
    toma: "numeros", de: 4.6, a: 13.6,
    texto: "we read its status, quality rating and messaging limit from the WhatsApp Business Management API and subscribe our app to its webhooks.",
  },
  { toma: "plantillas", de: 0.6, a: 9.4, texto: "The business lists its message templates and their approval status, live from Meta." },
  { toma: "plantilla", de: 0.6, a: 12.2, texto: "It creates new templates (Utility or Marketing) with variables and examples; Meta reviews each one." },
  {
    toma: "cierre", de: 0.6, a: 8.8,
    texto: "We use whatsapp_business_management only to onboard the business's own account, show its number status and manage its templates.",
  },
];
