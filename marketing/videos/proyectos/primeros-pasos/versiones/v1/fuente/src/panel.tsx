import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, EASE, F } from "../../../src/comun/theme";
import { useIn } from "../../../src/comun/ui";

// El panel de Atentina en el celular (vista de cliente, 390 px de ancho), recreado con los rótulos reales de web/
// (AppLayout, AgentsPage, NewAgentModal, AgentDetailPage, DefinitionForm, TestTab, NewCallForm, CallDetailPage).
// Todo lo de adentro del teléfono está en px de esa pantalla de 390; el marco lo escala.

export const W = 390;
export const FRAME = { left: 130, top: 470, width: 820, height: 1390 };
export const S = FRAME.width / W; // escala de la pantalla
export const VH = FRAME.height / S; // alto visible de la pantalla (px del panel)
export const HEADER = 60;
const ZOOM_Y = 1190; // a dónde va el foco del zoom en el cuadro (px del video)

export const P = {
  canvas: "#f6f8fb",
  line: "#e3e8ef",
  input: "#d3dae4",
  ink: C.ink,
  ink2: C.ink2,
  dim: "#64748b",
  blue: C.accent,
  blueLight: "#e8eefc",
  ok: "#1b8a4f",
  okSoft: "#e6f2eb",
  yellowSoft: "#fdf3d7",
  yellow: "#94650b",
};

// ---------- tiempo ----------

/** Texto que se va escribiendo: desde `desde` (s), a `cps` caracteres por segundo. */
export const useTipeo = (texto: string, desde: number, cps: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = Math.max(0, Math.min(texto.length, Math.floor((frame / fps - desde) * cps)));
  return { visto: texto.slice(0, n), escribiendo: n > 0 && n < texto.length, listo: n >= texto.length, fin: desde + texto.length / cps };
};

/** Zoom suave: entra en [a, a+0.55] y sale en [b, b+0.55] (0..1). */
export const useZoom = (a: number, b: number) => useIn(a, 0.55) * (1 - useIn(b, 0.55));

/** Desplazamiento de la página: de `y0` a `y1` entre `a` y `a + d`. */
export const useScroll = (pasos: [number, number, number][], inicial = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  let y = inicial;
  for (const [a, d, hasta] of pasos) {
    const k = interpolate(frame, [a * fps, (a + d) * fps], [0, 1], { ...CLAMP, easing: EASE });
    y = y + (hasta - y) * k;
  }
  return y;
};

// ---------- marco y zoom ----------

export type Zoom = { z: number; x: number; y: number; k: number };

/** El teléfono: marco, pantalla con el fondo del panel y el zoom hacia un punto (x, y de la pantalla). */
export const Telefono: React.FC<{ zoom?: Zoom; children: React.ReactNode; aparece?: number }> = ({ zoom, children, aparece = 1 }) => {
  // El zoom agranda el teléfono entero en el cuadro del video: el punto de foco (x, y de la pantalla) va hacia
  // el centro del cuadro, un poco más abajo del título.
  const z = zoom?.z ?? 0;
  const k = 1 + ((zoom?.k ?? 1) - 1) * z;
  const fx = FRAME.left + (zoom?.x ?? W / 2) * S;
  const fy = FRAME.top + (zoom?.y ?? VH / 2) * S;
  const cx = fx + (540 - fx) * z;
  const cy = fy + (ZOOM_Y - fy) * z;
  const tx = cx - k * fx;
  const ty = cy - k * fy;
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: 1080, height: 1920, transform: `translate(${tx}px, ${ty}px) scale(${k})`, transformOrigin: "0 0" }}>
      <div style={{
        position: "absolute", left: FRAME.left - 18, top: FRAME.top - 18, width: FRAME.width + 36, height: FRAME.height + 36,
        borderRadius: 78, background: C.ink, boxShadow: "0 40px 90px rgba(11,18,32,0.22)",
        opacity: aparece, transform: `translateY(${(1 - aparece) * 40}px)`,
      }}>
        <div style={{ position: "absolute", left: 18, top: 18, width: FRAME.width, height: FRAME.height, borderRadius: 62, overflow: "hidden", background: P.canvas }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: W, height: VH, transform: `scale(${S})`, transformOrigin: "0 0" }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};

/** Toque en la pantalla: un círculo que aparece, se aprieta y se desvanece. */
export const Toque: React.FC<{ x: number; y: number; t: number }> = ({ x, y, t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = frame / fps - t;
  if (s < -0.35 || s > 0.7) return null;
  const o = interpolate(s, [-0.35, -0.1, 0.35, 0.7], [0, 0.85, 0.6, 0], CLAMP);
  const r = interpolate(s, [-0.35, 0, 0.15, 0.7], [26, 18, 16, 30], CLAMP);
  const onda = interpolate(s, [0, 0.6], [16, 40], CLAMP);
  return (
    <>
      <div style={{ position: "absolute", left: x - onda, top: y - onda, width: onda * 2, height: onda * 2, borderRadius: "50%",
        border: `2px solid ${P.blue}`, opacity: s > 0 ? o * 0.6 : 0, zIndex: 50 }} />
      <div style={{ position: "absolute", left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: "50%",
        background: "rgba(36,86,230,0.28)", border: "2px solid rgba(255,255,255,0.9)", opacity: o, zIndex: 50 }} />
    </>
  );
};

// ---------- íconos (trazo como los de Tabler) ----------

type Ico = "menu" | "x" | "user" | "logout" | "plus" | "arrowLeft" | "pencil" | "dots" | "info" | "file" | "history" | "play"
  | "link" | "save" | "phoneCall" | "check" | "mic" | "chevrons" | "home" | "messages" | "phoneOut" | "robot" | "trash";
export const Icono: React.FC<{ n: Ico; s?: number; c?: string; w?: number }> = ({ n, s = 18, c = "currentColor", w = 2 }) => {
  const p = { fill: "none", stroke: c, strokeWidth: w, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  const d: Record<Ico, React.ReactNode> = {
    menu: <path {...p} d="M4 6h16M4 12h16M4 18h16" />,
    x: <path {...p} d="M6 6l12 12M18 6L6 18" />,
    user: <><circle {...p} cx={12} cy={12} r={9} /><circle {...p} cx={12} cy={10} r={3} /><path {...p} d="M6.2 18.8a6 6 0 0 1 11.6 0" /></>,
    logout: <><path {...p} d="M14 8V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h7a2 2 0 0 0 2-2v-2" /><path {...p} d="M9 12h12l-3-3M18 15l3-3" /></>,
    plus: <path {...p} d="M12 5v14M5 12h14" />,
    arrowLeft: <path {...p} d="M5 12h14M5 12l6 6M5 12l6-6" />,
    pencil: <path {...p} d="M4 20h4L18.5 9.5a2.8 2.8 0 0 0-4-4L4 16v4M13.5 6.5l4 4" />,
    dots: <><circle cx={5} cy={12} r={1.6} fill={c} /><circle cx={12} cy={12} r={1.6} fill={c} /><circle cx={19} cy={12} r={1.6} fill={c} /></>,
    info: <><circle {...p} cx={12} cy={12} r={9} /><path {...p} d="M12 8h.01M11 12h1v4h1" /></>,
    file: <><path {...p} d="M14 3v4a1 1 0 0 0 1 1h4" /><path {...p} d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" /><path {...p} d="M10 13l-1 2 1 2M14 13l1 2-1 2" /></>,
    history: <><path {...p} d="M12 8v4l2 2" /><path {...p} d="M3.05 11a9 9 0 1 1 .5 4M3 20v-5h5" /></>,
    play: <path {...p} d="M7 4v16l13-8Z" />,
    link: <path {...p} d="M9 15l6-6M11 6l.46-.54a5 5 0 0 1 7.07 7.07L18 13M13 18l-.4.53a5 5 0 0 1-7.11-7.04L6 11" />,
    save: <><path {...p} d="M6 4h10l4 4v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2" /><circle {...p} cx={12} cy={14} r={2} /><path {...p} d="M14 4v4H8V4" /></>,
    phoneCall: <><path {...p} d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" /><path {...p} d="M15 7a2 2 0 0 1 2 2M15 3a6 6 0 0 1 6 6" /></>,
    check: <><circle {...p} cx={12} cy={12} r={9} /><path {...p} d="M9 12l2 2 4-4" /></>,
    mic: <><rect {...p} x={9} y={2} width={6} height={11} rx={3} /><path {...p} d="M5 10a7 7 0 0 0 14 0M8 21h8M12 17v4" /></>,
    chevrons: <path {...p} d="M8 9l4-4 4 4M16 15l-4 4-4-4" />,
    home: <path {...p} d="M5 12H3l9-9 9 9h-2M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7M9 21v-6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v6" />,
    messages: <path {...p} d="M21 14l-3-3h-7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v10M14 15v2a1 1 0 0 1-1 1H6l-3 3V11a1 1 0 0 1 1-1h2" />,
    phoneOut: <><path {...p} d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" /><path {...p} d="M15 5h6M18 2l3 3-3 3" /></>,
    robot: <><rect {...p} x={6} y={4} width={12} height={10} rx={2} /><path {...p} d="M9 9h.01M15 9h.01M12 14v3M8 21v-4h8v4M4 9v2M20 9v2" /></>,
    trash: <path {...p} d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" />,
  };
  return <svg viewBox="0 0 24 24" width={s} height={s} style={{ display: "block", flexShrink: 0 }}>{d[n]}</svg>;
};

// ---------- piezas del panel ----------

const box = (style: React.CSSProperties): React.CSSProperties => ({ position: "absolute", boxSizing: "border-box", ...style });

/** Barra de arriba del panel en el celular: menú, logo, perfil y salir. */
export const Cabecera: React.FC<{ abierto?: boolean }> = ({ abierto }) => (
  <div style={box({ left: 0, top: 0, width: W, height: HEADER, background: "#fff", borderBottom: `1px solid ${P.line}`, zIndex: 20 })}>
    <div style={box({ left: 18, top: 18 })}><Icono n={abierto ? "x" : "menu"} s={24} c={P.ink} w={1.6} /></div>
    <Img src={staticFile("marca/atentina-logo.svg")} style={{ position: "absolute", left: 57, top: 17, height: 26 }} />
    {(["user", "logout"] as const).map((n, i) => (
      <div key={n} style={box({ left: 294 + i * 46, top: 13, width: 34, height: 34, borderRadius: 9, border: `1px solid ${P.input}`, background: "#fff",
        display: "flex", alignItems: "center", justifyContent: "center" })}>
        <Icono n={n} s={18} c={P.ink} w={1.8} />
      </div>
    ))}
  </div>
);

export const Texto: React.FC<{ x: number; y: number; w?: number; s?: number; c?: string; peso?: number; f?: string; lh?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({
  x, y, w, s = 14, c = P.ink, peso = 400, f = F.body, lh = 1.35, children, style,
}) => (
  <div style={box({ left: x, top: y, width: w, fontFamily: f, fontSize: s, color: c, fontWeight: peso, lineHeight: lh, ...style })}>{children}</div>
);

export const Titulo: React.FC<{ x?: number; y: number; children: React.ReactNode; s?: number }> = ({ x = 16, y, children, s = 26 }) => (
  <Texto x={x} y={y} s={s} peso={800} f={F.display} style={{ letterSpacing: "-0.015em", whiteSpace: "nowrap" }}>{children}</Texto>
);

export const Tarjeta: React.FC<{ y: number; h: number; x?: number; w?: number; children?: React.ReactNode; style?: React.CSSProperties }> = ({ y, h, x = 16, w = W - 32, children, style }) => (
  <div style={box({ left: x, top: y, width: w, height: h, background: "#fff", border: `1px solid ${P.line}`, borderRadius: 18, ...style })}>{children}</div>
);

export const Boton: React.FC<{ x: number; y: number; w?: number; h?: number; tipo?: "primario" | "borde" | "claro" | "apagado"; icono?: Ico; children: React.ReactNode; s?: number; apretado?: number }> = ({
  x, y, w, h = 36, tipo = "primario", icono, children, s = 14, apretado = 0,
}) => {
  const st = {
    primario: { bg: P.blue, fg: "#fff", bd: P.blue },
    borde: { bg: "#fff", fg: P.ink, bd: P.input },
    claro: { bg: P.blueLight, fg: P.blue, bd: P.blueLight },
    apagado: { bg: "#e9edf3", fg: "#9aa6b8", bd: "#e9edf3" },
  }[tipo];
  return (
    <div style={box({ left: x, top: y, width: w, height: h, padding: "0 16px", borderRadius: 9, background: st.bg, color: st.fg, border: `1px solid ${st.bd}`,
      display: "flex", alignItems: "center", justifyContent: "center", gap: 8, fontFamily: F.body, fontWeight: 600, fontSize: s, whiteSpace: "nowrap",
      transform: `scale(${1 - 0.05 * apretado})` })}>
      {icono ? <Icono n={icono} s={17} c={st.fg} /> : null}
      {children}
    </div>
  );
};

/** Campo con rótulo, descripción y caja (una línea o varias). `foco` resalta el borde. */
export const Campo: React.FC<{
  x?: number; y: number; w?: number; label?: string; desc?: string; valor?: string; placeholder?: string; alto?: number;
  foco?: boolean; cursor?: boolean; descLineas?: number; s?: number; apagado?: boolean;
}> = ({ x = 36, y, w = W - 72, label, desc, valor = "", placeholder, alto = 36, foco, cursor, descLineas = 1, s = 14, apagado }) => {
  const frame = useCurrentFrame();
  const top = (label ? 22 : 0) + (desc ? descLineas * 17 + 4 : 0);
  const blink = cursor && Math.floor(frame / 15) % 2 === 0;
  return (
    <>
      {label ? <Texto x={x} y={y} s={14} peso={600}>{label}</Texto> : null}
      {desc ? <Texto x={x} y={y + 21} w={w} s={12} c={P.dim} lh={1.4}>{desc}</Texto> : null}
      <div style={box({ left: x, top: y + top, width: w, height: alto, borderRadius: 9, background: apagado ? "#eef1f5" : "#fff",
        border: `1px solid ${foco ? P.blue : P.input}`, boxShadow: foco ? "0 0 0 2px rgba(36,86,230,0.15)" : undefined,
        padding: alto > 40 ? "8px 12px" : "0 12px", display: alto > 40 ? "block" : "flex", alignItems: "center",
        fontFamily: F.body, fontSize: s, lineHeight: 1.55, color: valor ? P.ink : "#a3adbb", whiteSpace: "pre-wrap", overflow: "hidden" })}>
        <span>{valor || placeholder}</span>
        {blink ? <span style={{ display: "inline-block", width: 1.5, height: s * 1.15, background: P.ink, verticalAlign: "text-bottom", marginLeft: 1 }} /> : null}
      </div>
    </>
  );
};

export const Interruptor: React.FC<{ x: number; y: number; on: number; label: string; desc?: string; w?: number }> = ({ x, y, on, label, desc, w = 250 }) => (
  <>
    <div style={box({ left: x, top: y, width: 38, height: 20, borderRadius: 10, background: on > 0.5 ? P.blue : "#e2e7ee" })}>
      <div style={box({ left: 3 + on * 18, top: 3, width: 14, height: 14, borderRadius: 7, background: "#fff", border: on > 0.5 ? undefined : `1px solid ${P.input}` })} />
    </div>
    <Texto x={x + 50} y={y} s={14}>{label}</Texto>
    {desc ? <Texto x={x + 50} y={y + 22} w={w} s={12} c={P.dim} lh={1.4}>{desc}</Texto> : null}
  </>
);

export const Insignia: React.FC<{ x: number; y: number; bg: string; fg: string; children: React.ReactNode }> = ({ x, y, bg, fg, children }) => (
  <div style={box({ left: x, top: y, padding: "2px 10px", borderRadius: 999, background: bg, color: fg, fontFamily: F.body, fontWeight: 700, fontSize: 12, whiteSpace: "nowrap" })}>{children}</div>
);

/** Aviso de arriba (notificación de Mantine): barra verde y texto. */
export const Aviso: React.FC<{ texto: string; o: number }> = ({ texto, o }) => (
  <div style={box({ left: 16, top: 16 + (1 - o) * -20, width: W - 32, height: 50, borderRadius: 12, background: "#fff", border: `1px solid ${P.line}`,
    boxShadow: "0 8px 24px rgba(11,18,32,0.12)", opacity: o, zIndex: 40, display: "flex", alignItems: "center", gap: 12, padding: "0 14px" })}>
    <div style={{ width: 4, height: 26, borderRadius: 2, background: P.ok }} />
    <span style={{ fontFamily: F.body, fontSize: 14, color: P.ink }}>{texto}</span>
  </div>
);

/** Cabecera del detalle del agente (AgentDetailPage) con las pestañas; `y` es el tope del contenido. */
export const DetalleAgente: React.FC<{ y: number; version: number; tab: "definicion" | "probar"; toque?: number }> = ({ y, version, tab }) => {
  const tabs: [string, Ico, string, number, number][] = [
    ["resumen", "info", "Resumen", 16, 0], ["definicion", "file", "Definición", 138, 0],
    ["versiones", "history", "Versiones", 16, 42], ["probar", "play", "Probar", 142, 42], ["link", "link", "Link para llamar", 16, 84],
  ];
  return (
    <>
      <div style={box({ left: 22, top: y + 14, display: "flex", alignItems: "center", gap: 10, color: P.blue, fontFamily: F.body, fontWeight: 600, fontSize: 14 })}>
        <Icono n="arrowLeft" s={16} c={P.blue} /> Agentes
      </div>
      <Titulo y={y + 42}>Atención al cliente <span style={{ fontFamily: F.body, fontWeight: 400, fontSize: 14, color: P.dim, marginLeft: 6 }}>v{version}</span></Titulo>
      <Texto x={16} y={y + 86} s={14} c={P.dim}>Voz sofia · actualizado 23/10/2026 10:15</Texto>
      <Texto x={16} y={y + 110} s={14} c={P.dim}>Atiende consultas de la web</Texto>
      <Boton x={16} y={y + 136} w={96} tipo="borde" icono="pencil">Editar</Boton>
      <Boton x={122} y={y + 136} w={40} tipo="borde"><Icono n="dots" s={18} c={P.ink} /></Boton>
      {tabs.map(([id, ic, t, x, dy]) => {
        const on = id === tab;
        return (
          <div key={id} style={box({ left: x, top: y + 188 + dy, height: 36, padding: "0 16px", borderRadius: 9, display: "flex", alignItems: "center", gap: 10,
            background: on ? P.blueLight : "transparent", color: on ? P.blue : P.ink, fontFamily: F.body, fontWeight: on ? 600 : 500, fontSize: 14 })}>
            <Icono n={ic} s={16} c={on ? P.blue : P.ink} w={1.8} /> {t}
          </div>
        );
      })}
    </>
  );
};
